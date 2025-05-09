import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
import urllib.request as libreq
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import re
from get_connections import main as get_paper_connections
from embed import fuzzy_search_related_papers, fuzzy_search_get_all_related_papers

app = Flask(__name__)
# Use CORS with explicit settings for compatibility
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'papers.db')
CSV_PATH = os.path.join(BASE_DIR, 'arxiv_ripper', 'arxiv_cs_recent.csv')

# Helper function to add paper to embeddings directly from API
def add_paper_to_embeddings_local(paper):
    """Direct implementation to add paper to embeddings database without importing from embed.py"""
    try:
        from embed import generate_embeddings, setup_embeddings_database, EMBEDDINGS_DB_PATH
        
        # Make sure database is set up
        setup_embeddings_database()
        
        if not paper.get('abstract'):
            print(f"Paper {paper['id']} has no abstract, skipping embedding generation")
            return False
        
        # Generate embedding
        abstracts = [paper['abstract']]
        embeddings = generate_embeddings(abstracts)
        
        if len(embeddings) == 0:
            print(f"Failed to generate embedding for paper {paper['id']}")
            return False
        
        # Store in database
        conn = sqlite3.connect(EMBEDDINGS_DB_PATH)
        cursor = conn.cursor()
        
        embedding_blob = embeddings[0].tobytes()
        
        cursor.execute('''
        INSERT OR REPLACE INTO paper_embeddings
        (id, title, abstract, embedding, authors, categories, year)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            paper['id'],
            paper['title'],
            paper['abstract'],
            embedding_blob,
            paper.get('authors', ''),
            paper.get('categories', ''),
            paper.get('year', 0)
        ))
        
        conn.commit()
        conn.close()
        
        print(f"Successfully added paper {paper['id']} to embeddings database")
        return True
    
    except Exception as e:
        print(f"Error adding paper to embeddings database: {str(e)}")
        return False

# Helper function to extract ArXiv ID
def extract_arxiv_id(url):
    """Extract the ArXiv ID from a URL or ID string."""
    if "arxiv.org" in url:
        # For full URLs like http://arxiv.org/abs/2210.02414
        parts = url.split("/")
        raw_id = parts[-1]
    else:
        # For already extracted IDs
        raw_id = url
    
    # Handle potential version number (e.g., 2210.02414v1)
    return raw_id.split("v")[0] if "v" in raw_id else raw_id

# Function to fetch paper details directly from ArXiv API
def fetch_arxiv_paper(paper_id):
    """Fetch paper details from ArXiv API."""
    print(f"Fetching paper {paper_id} from ArXiv API...")
    
    # Normalize ID (remove version if present)
    normalized_id = extract_arxiv_id(paper_id)
    
    try:
        # Construct ArXiv API query URL
        url = f"http://export.arxiv.org/api/query?id_list={normalized_id}"
        
        with libreq.urlopen(url) as response:
            xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        
        if not entries:
            print(f"No paper found with ID {paper_id}")
            return None
        
        entry = entries[0]
        
        # Extract data
        full_url = entry.find("{http://www.w3.org/2005/Atom}id").text
        title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip().replace("\n", " ")
        authors = ", ".join([author.find("{http://www.w3.org/2005/Atom}name").text 
                   for author in entry.findall("{http://www.w3.org/2005/Atom}author")])
        published = entry.find("{http://www.w3.org/2005/Atom}published").text
        abstract = entry.find("{http://www.w3.org/2005/Atom}summary").text.strip().replace("\n", " ") if entry.find("{http://www.w3.org/2005/Atom}summary") is not None else ""
        categories = ", ".join([cat.get('term') for cat in entry.findall("{http://www.w3.org/2005/Atom}category")])
        
        # Process publication date
        try:
            pub_date = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
            year = pub_date.year
            month = pub_date.month
            day = pub_date.day
        except:
            year, month, day = 0, 0, 0
            
        # Ensure the ID is correctly formatted
        arxiv_id = extract_arxiv_id(full_url)
        
        # Create paper object
        paper = {
            "id": arxiv_id,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "categories": categories,
            "year": year,
            "month": month,
            "day": day,
            "connected_papers": "[]"
        }
        
        print(f"Successfully fetched paper from ArXiv: {arxiv_id}: {title[:50]}...")
        return paper
        
    except Exception as e:
        print(f"Error fetching paper from ArXiv: {str(e)}")
        return None

# Function to add paper to database
def add_paper_to_db(paper):
    """Add paper to the papers database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Insert the paper into the database
        cursor.execute("""
            INSERT OR REPLACE INTO papers (
                id, title, authors, abstract, categories, 
                connected_papers, year, month, day
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            paper["id"],
            paper["title"],
            paper["authors"],
            paper["abstract"],
            paper["categories"],
            paper["connected_papers"],
            paper["year"],
            paper["month"],
            paper["day"]
        ))
        
        conn.commit()
        print(f"Successfully added paper {paper['id']} to database")
        return True
    except Exception as e:
        print(f"Error adding paper to database: {str(e)}")
        return False
    finally:
        conn.close()


def sort_core_papers(title, papers, current_id=None):
    """
    Sort and filter papers to avoid duplicates and the current paper.
    Returns up to 5 papers sorted by year (most recent first).
    """
    if not papers or len(papers) == 0:
        return []
        
    # Sort by year (most recent first)
    papers.sort(key=lambda x: x.get('year', 0), reverse=True)
    
    results = []
    seen_ids = set()
    
    # If current_id is provided, add it to seen_ids to avoid including it
    if current_id:
        seen_ids.add(current_id)
    
    for paper in papers:
        # Skip if no id or title (malformed entry)
        if not paper.get('id') or not paper.get('title'):
            continue
            
        # Skip the current paper (by title or id)
        if paper['id'] in seen_ids:
            continue
            
        if title and paper.get('title') == title:
            continue
            
        # Add to results and mark as seen
        seen_ids.add(paper['id'])
        results.append({
            "id": paper["id"],
            "title": paper["title"],
            "abstract": paper.get("abstract", ""),
            "categories": paper.get("categories", ""),
            "authors": paper.get("authors", ""),
            "similarity": paper.get("similarity", 0)
        })
        
        # Stop after 5 papers
        if len(results) >= 5:
            break

    return results

@app.route('/api/search', methods=['GET'])
def search_papers():
    query = request.args.get('q')
    print(f"DEBUG: /api/search received query: {query}")
    
    if not query:
        print("DEBUG: No query provided")
        return jsonify({"success": False, "error": "No query provided"}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print(f"DEBUG: Searching database for: {query}")
        cursor.execute("""
            SELECT id, title, authors, abstract, categories, year, month, day
            FROM papers 
            WHERE title LIKE ? OR authors LIKE ? OR id LIKE ?
            LIMIT 20
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        
        results = []
        for row in cursor.fetchall():
            print(f"DEBUG: Found paper: {row[0]}")
            connections = flask_get_connections(row[0], 1)
            connections_data = connections.get_json()
            
            # Get embedding-based related papers
            print(f"DEBUG: Getting embedding-based related papers for {row[0]}")
            current_paper_id = row[0]
            current_paper_title = row[1]
            
            # Safely get related papers with error handling
            try:
                hot_papers = fuzzy_search_get_all_related_papers(row[3] or "")
                hot_papers = sort_core_papers(current_paper_title, hot_papers, current_paper_id)
                print(f"DEBUG: Found {len(hot_papers)} hot papers for {current_paper_id}")
            except Exception as e:
                print(f"DEBUG: Error getting hot papers: {str(e)}")
                hot_papers = []

            # Add embedding-based connections to the connections data structure
            if connections_data and "first_degree" in connections_data:
                print(f"DEBUG: Adding embedding-based connections for {row[0]}")
                # Track how many we've added
                added_count = 0
                
                for i, hot_paper in enumerate(hot_papers):
                    # Skip if it's the same paper
                    if hot_paper['id'] == current_paper_id:
                        continue
                        
                    # Check if this hot paper is already in the connections
                    already_exists = False
                    if connections_data["first_degree"] and "connections" in connections_data["first_degree"]:
                        already_exists = any(
                            (isinstance(conn, dict) and conn.get('id') == hot_paper['id']) or
                            (isinstance(conn, str) and conn == hot_paper['id'])
                            for conn in connections_data["first_degree"]["connections"]
                        )
                    
                    # Add to connections if not already there
                    if not already_exists and connections_data["first_degree"] and "connections" in connections_data["first_degree"]:
                        print(f"DEBUG: Adding embedding connection: {hot_paper['id']}")
                        connections_data["first_degree"]["connections"].append({
                            "id": hot_paper['id'],
                            "title": hot_paper['title'],
                            "similarity": hot_paper['similarity']  # Use the actual similarity score
                        })
                        
                        # Increment counter and break if we've added 5
                        added_count += 1
                        if added_count >= 5:
                            print(f"DEBUG: Added top 5 embedding-based connections for {row[0]}")
                            break

            # Generate core papers with better error handling
            core_papers = []
            try:
                # First, get papers related to each hot paper
                processed_hot_papers = []
                # Make a copy of hot_papers to avoid modifying the original during iteration
                for paper in hot_papers[:10]:  # Limit to first 10 hot papers for efficiency
                    # Skip papers without abstracts
                    if not paper.get('abstract'):
                        continue
                        
                    try:
                        paper_temp = fuzzy_search_get_all_related_papers(paper['abstract'])
                        # Filter out duplicates and the current paper
                        paper_temp = sort_core_papers(paper['title'], paper_temp, current_paper_id)
                        if paper_temp and len(paper_temp) > 0:
                            processed_hot_papers.append(paper_temp[0])
                    except Exception as inner_e:
                        print(f"DEBUG: Error processing hot paper {paper.get('id')}: {str(inner_e)}")
                        continue
                
                # Filter out duplicates and ensure we don't include the original paper
                seen_ids = {current_paper_id}
                for paper in processed_hot_papers:
                    if paper['id'] not in seen_ids:
                        seen_ids.add(paper['id'])
                        core_papers.append(paper)
                        if len(core_papers) >= 5:
                            break
                
                # If we don't have 5 core papers yet, add more from hot papers
                if len(core_papers) < 5:
                    for paper in hot_papers:
                        if paper['id'] not in seen_ids:
                            seen_ids.add(paper['id'])
                            core_papers.append(paper)
                            if len(core_papers) >= 5:
                                break
                
                print(f"DEBUG: Created {len(core_papers)} core papers for {current_paper_id}")
            except Exception as core_e:
                print(f"DEBUG: Error generating core papers: {str(core_e)}")
                # Ensure we always have something for core_papers
                core_papers = hot_papers[:5] if hot_papers else []

            results.append({
                "id": row[0],
                "title": row[1].strip(),
                "authors": row[2],
                "abstract": row[3].strip(),
                "categories": row[4],
                "year": row[5],
                "month": row[6],
                "day": row[7],
                "hot_papers": hot_papers,
                "core_papers": core_papers,
                "connections": connections_data
            })
        
        print(f"DEBUG: Returning {len(results)} results for query: {query}")
        return jsonify({
            "success": True,
            "results": results
        })
        
    except Exception as e:
        print(f"DEBUG: Error in /api/search: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    finally:
        conn.close()

@app.route('/api/topic-search', methods=['GET'])
def search_by_topic():
    query = request.args.get('q')
    print(f"DEBUG: /api/topic-search received query: {query}")
    
    if not query:
        print("DEBUG: No topic provided")
        return jsonify({"success": False, "error": "No topic provided"}), 400
    
    try:
        # Use the existing embedding-based search function to find papers related to the topic
        print(f"DEBUG: Searching embeddings for: {query}")
        related_papers = fuzzy_search_related_papers(query, top_n=20)
        print(f"DEBUG: Found {len(related_papers)} related papers")
        
        # Format the results - LIGHTWEIGHT VERSION (no connections fetch)
        results = []
        for paper in related_papers:
            result_item = {
                "id": paper['id'],
                "title": paper['title'].strip(),
                "authors": paper['authors'],
                "year": paper['year'],
                "similarity": paper['similarity']
                # No abstract, no connections - keep it lightweight for dropdown only
            }
            results.append(result_item)
        
        print(f"DEBUG: Returning {len(results)} lightweight results for dropdown")
        return jsonify({
            "success": True,
            "results": results
        })
        
    except Exception as e:
        print(f"DEBUG: Error in /api/topic-search: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/paper/<paper_id>', methods=['GET'])
def get_paper(paper_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, authors, abstract, categories, year, connected_papers 
            FROM papers WHERE id = ?
        """, (paper_id,))
        
        paper = cursor.fetchone()
        if not paper:
            print(f"Paper {paper_id} not found in database")
            return jsonify({"success": False, "error": f"Paper with ID {paper_id} not found in database"}), 404
            
        # Get connected papers details
        connected = []
        if paper[6]:
            try:
                connected_ids = json.loads(paper[6])
                placeholders = ','.join(['?']*len(connected_ids))
                cursor.execute(f"""
                    SELECT id, title FROM papers 
                    WHERE id IN ({placeholders})
                """, connected_ids)
                connected = [{"id": row[0], "title": row[1]} for row in cursor.fetchall()]
            except json.JSONDecodeError:
                pass
                
        return jsonify({
            "success": True,
            "id": paper[0],
            "title": paper[1],
            "authors": paper[2],
            "abstract": paper[3],
            "categories": paper[4],
            "year": paper[5],
            "connected_papers": connected
        })
    except Exception as e:
        print(f"Error in /api/paper: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/connections/<paper_info>/<degree_checked>', methods=['GET'])
def flask_get_connections(paper_info, degree_checked):
    print(f"DEBUG: /api/connections received request for {paper_info}, degree {degree_checked}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # in case user queries by paper title
        search_query = f"%{paper_info}%"
        cursor.execute("""
            SELECT *
            FROM papers 
            WHERE title LIKE ? OR id LIKE ?
            LIMIT 1
        """, (search_query, search_query))
        
        results = cursor.fetchall()
        paper_id = None
        
        if results and len(results) > 0:
            paper_id = results[0][0]
            print(f"DEBUG: Found paper by search: {paper_id}")
        else:
            # If no results found, the paper_info might be an exact paper_id
            paper_id = paper_info
            print(f"DEBUG: Using direct paper ID: {paper_id}")
        
        # Validate paper_id
        if not paper_id:
            return jsonify({"success": False, "error": "Paper not found"}), 404
            
        connections = get_paper_connections(paper_id)
        
        if not connections or "first_degree" not in connections:
            print(f"DEBUG: No connections found for {paper_id}")
            return jsonify({
                "first_degree": {
                    "source_id": paper_id,
                    "source_title": "Unknown paper",
                    "connections": []
                }
            })
            
        print(f"DEBUG: Returning connections for {paper_id}")
        return jsonify(connections)
    except Exception as e:
        print(f"DEBUG: Error in /api/connections: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/update', methods=['POST'])
def update_database():
    try:
        from arxiv_ripper.arxiv_ripper import main as update_arxiv
        from arxiv_ripper.upload_csv import upload_csv_to_db
        
        update_arxiv()
        upload_csv_to_db(CSV_PATH, DB_PATH)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/category-search', methods=['GET'])
def search_by_category():
    category = request.args.get('category')
    print(f"DEBUG: /api/category-search received category: {category}")
    
    if not category:
        print("DEBUG: No category provided")
        return jsonify({"success": False, "error": "No category provided"}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Normalize the category format (handle both CS.LG and cs.lg formats)
        normalized_category = category.upper()
        if not normalized_category.startswith("CS."):
            normalized_category = "CS." + normalized_category
        
        print(f"DEBUG: Searching database for category: {normalized_category}")
        
        # Query the database for papers with exact category match
        # Categories are stored as comma-separated strings like "CS.CL, CS.AI"
        cursor.execute("""
            SELECT id, title, authors, year, month, day, categories
            FROM papers 
            WHERE categories LIKE ? OR categories LIKE ? OR categories LIKE ? OR categories = ?
            ORDER BY year DESC, month DESC, day DESC
            LIMIT 20
        """, (
            f"{normalized_category},%",  # Category at the start
            f"%, {normalized_category},%",  # Category in the middle
            f"%, {normalized_category}",  # Category at the end
            normalized_category,  # Category as the only value
        ))
        
        results = []
        rows = cursor.fetchall()
        
        for row in rows:
            # Additional check to ensure we have exact category match
            categories = row["categories"].split(", ") if row["categories"] else []
            if normalized_category not in [cat.strip().upper() for cat in categories]:
                continue
                
            paper = {
                "id": row["id"],
                "title": row["title"].strip(),
                "authors": row["authors"],
                "year": row["year"],
                "categories": row["categories"]
            }
            results.append(paper)
        
        print(f"DEBUG: Found {len(results)} papers for category {normalized_category}")
        return jsonify({
            "success": True,
            "category": normalized_category,
            "results": results
        })
        
    except Exception as e:
        print(f"DEBUG: Error in /api/category-search: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=8080)
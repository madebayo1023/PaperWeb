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


def sort_core_papers(title, papers):
    papers.sort(key=lambda x: x['year'], reverse=True)
    results = []
    for i, paper in enumerate(papers):
        if paper['title'] != title:
            results.append({
                paper["id"],
                paper["title"],
                paper["abstract"],
                paper["categories"],
                paper["authors"],
                paper["similarity"]
            })
        if len(papers) == 5:
            break

    return papers[:5]

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
            connections = connections.get_json()
            hot_papers = fuzzy_search_get_all_related_papers(row[3])
            hot_papers = sort_core_papers(row[1], hot_papers)

            core_papers = []
            for paper in hot_papers:
                paper_temp = fuzzy_search_get_all_related_papers(paper['abstract'])
                paper_temp = sort_core_papers(paper['title'], paper_temp)           # unsure if this is correct
                core_papers.append(paper_temp[0])                                   # just take the first one
                if len(core_papers) == 5:
                    break

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
                "connections": connections
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
            print(f"Paper {paper_id} not found in database, fetching from ArXiv...")
            
            # Fetch paper from ArXiv API
            arxiv_paper = fetch_arxiv_paper(paper_id)
            
            if not arxiv_paper:
                return jsonify({"success": False, "error": f"Paper with ID {paper_id} not found in database or ArXiv"}), 404
            
            # Add paper to database
            add_paper_to_db(arxiv_paper)
            
            # Add paper to embeddings database
            try:
                print(f"Adding paper {paper_id} to embeddings database...")
                add_paper_to_embeddings_local(arxiv_paper)
                print(f"Successfully added paper {paper_id} to embeddings")
            except Exception as e:
                print(f"Error adding paper to embeddings: {str(e)}")
            
            # Return the fetched paper
            return jsonify({
                "success": True,
                "id": arxiv_paper["id"],
                "title": arxiv_paper["title"],
                "authors": arxiv_paper["authors"],
                "abstract": arxiv_paper["abstract"],
                "categories": arxiv_paper["categories"],
                "year": arxiv_paper["year"],
                "connected_papers": []
            })
            
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

if __name__ == '__main__':
    app.run(debug=True, port=8080)
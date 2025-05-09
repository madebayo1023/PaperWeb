import sqlite3
import re
import requests
from typing import Set
from datetime import datetime
import sys
import PyPDF2
import json
import fitz as pymupdf

# Constants
ARXIV_PDF_URL = "https://arxiv.org/pdf/"
HEADERS = {'User-Agent': 'Mozilla/5.0'}
ERROR_LOG_FILE = 'errors.txt'
db_path ='papers.db'

# Array of all possible arXiv reference patterns
ARXIV_PATTERNS = [
    # Standard arXiv formats
    r'cs/\d{7}',                           # cs/1234567
    r'\d{4}\.\d{4,5}',                     # 1234.5678
    r'arXiv:\d{4}\.\d{4,5}',               # arXiv:1234.5678
    r'\[arXiv:\d{4}\.\d{4,5}\]',           # [arXiv:1234.5678]
    
    # Computer science specific formats
    r'cs\.[A-Za-z]{2}/\d{7}',              # cs.CL/1234567
    r'cs\s[A-Za-z]{2}/\d{7}',              # cs CL/1234567
    
    # Extended preprint formats
    r'cs\.\s?ArXiv\s+preprint\s+cs\.[A-Za-z]{2}/\d{7}',  # cs. ArXiv preprint cs.CL/1234567
    r'cs\.\s?ArXiv\s+preprint\s+cs\s[A-Za-z]{2}/\d{7}',  # cs. ArXiv preprint cs CL/1234567
    
    # Variants with arXiv prefix
    r'arXiv:cs/\d{7}',                     # arXiv:cs/1234567
    r'\[arXiv:cs/\d{7}\]',                 # [arXiv:cs/1234567]
    
    # Additional explicit patterns
    r'cs\.\s?[A-Za-z]{2}/\d{7}',           # cs.CL/1234567 (alternate)
    r'cs\s?\.?\s?[A-Za-z]{2}/\d{7}',       # cs CL/1234567 or cs. CL/1234567
]

def log_error(paper_id: str, error_type: str, message: str):
    """Log errors to the error file with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(ERROR_LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {error_type} for paper {paper_id}: {message}\n")

def get_pdf_text(arxiv_id: str) -> str:
    """Get text from ArXiv PDF with improved error handling and logging."""
    url = f"{ARXIV_PDF_URL}{arxiv_id}"
    
    try:
        head_response = requests.head(url, timeout=10)
        
        if head_response.status_code != 200:
            log_error(arxiv_id, "HTTP Error", f"Status code: {head_response.status_code}")
            return ""
            
        response = requests.get(url, timeout=30)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Save the PDF temporarily
            with open('temp.pdf', 'wb') as f:
                f.write(response.content)

            try:
                # Extract text using PyMuPDF
                doc = pymupdf.open('temp.pdf')
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                return text
            except Exception as e:
                log_error(arxiv_id, "PDF Text Extraction Error", str(e))
                return ""
        else:
            log_error(arxiv_id, "HTTP Error", f"Status code: {response.status_code}")
            return ""
            
    except requests.exceptions.RequestException as e:
        log_error(arxiv_id, "HTTP Request Error", str(e))
        return ""
    except PyPDF2.PdfReadError as e:
        log_error(arxiv_id, "PDF Read Error", str(e))
        return ""
    except Exception as e:
        log_error(arxiv_id, "PDF Processing Error", str(e))
        return ""

def extract_normalized_arxiv_ids(text: str) -> Set[str]:
    found_ids = set()
    
    for pattern in ARXIV_PATTERNS:
        try:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract the core ID part
                matched_text = match.group(0)
                
                # Normalize different formats to standard form
                if 'cs.' in matched_text.lower() or 'cs/' in matched_text.lower():
                    # Handle cs/ or cs.XX/ formats
                    if '/' in matched_text:
                        id_part = matched_text.split('/')[-1]
                    else:
                        id_part = matched_text.split('.')[-1]
                    normalized_id = f"cs/{id_part}"
                else:
                    # Handle traditional arXiv IDs
                    id_part = matched_text.replace('arXiv:', '').replace('[', '').replace(']', '')
                    normalized_id = id_part.split('v')[0]  # Remove version
                
                found_ids.add(normalized_id)
        except Exception as e:
            log_error("PATTERN", f"Pattern {pattern} failed", str(e))
            continue
    
    return list(found_ids)

def filter_existing_references(references, db_path: str = 'papers.db'):
    existing_references = set()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for ref in references:
            # Check both the exact ID and versioned IDs (e.g., 1234.5678 and 1234.5678v1)
            cursor.execute("""
                SELECT 1 FROM papers 
                WHERE id = ? OR id LIKE ? || '%'
            """, (ref, f"{ref}v"))
            
            if cursor.fetchone():
                existing_references.add(ref)
                
    except sqlite3.Error as e:
        pass
    finally:
        if conn:
            conn.close()
    
    return list(existing_references)

def process_paper(paper_id: str):
    pdf_text = get_pdf_text(paper_id)
    if not pdf_text:
        return []
        
    references = extract_normalized_arxiv_ids(pdf_text)
    
    # Remove self-references
    paper_base_id = paper_id.split('v')[0]
    references = [ref for ref in references if ref != paper_base_id]
    
    return references

def update_paper_connections(paper_id: str, references, db_path: str = 'papers.db') -> int:
    if not references:
        return 0
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get current connections
        cursor.execute("SELECT connected_papers FROM papers WHERE id = ?", (paper_id,))
        result = cursor.fetchone()
        
        current_connections = set()
        if result and result[0]:
            try:
                current_connections = set(json.loads(result[0]))
            except json.JSONDecodeError:
                current_connections = set()
        
        # Calculate new connections to add
        new_connections = set(references) - set(current_connections)
        if not new_connections:
            return 0
            
        # Update the database
        updated_connections = list(current_connections.union(new_connections))
        cursor.execute("""
            UPDATE papers 
            SET connected_papers = ?
            WHERE id = ?
        """, (json.dumps(updated_connections), paper_id))
        
        conn.commit()
        return len(new_connections)
        
    except sqlite3.Error:
        if conn:
            conn.rollback()
        return 0
    finally:
        if conn:
            conn.close()

def get_paper_connections(paper_id: str, db_path: str = 'papers.db'):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT connected_papers FROM papers 
            WHERE id = ?
        """, (paper_id,))
        
        result = cursor.fetchone()
        if result and result[0]:
            try:
                return list(json.loads(result[0]))
            except json.JSONDecodeError:
                return []
        return []
        
    except sqlite3.Error:
        return []
    finally:
        if conn:
            conn.close()

def process_connections(first_degree_refs):
    second_degree_refs = dict()
    for ref_paper_id in first_degree_refs:
        try:
            # Skip if we've already processed this paper
            check_if_processed = get_paper_connections(ref_paper_id)
            if check_if_processed:
                second_degree_refs[ref_paper_id] = list(check_if_processed)
                continue
                
            # Get references for this reference paper
            ref_text = get_pdf_text(ref_paper_id)
            if not ref_text:
                continue
                
            refs_of_ref = extract_normalized_arxiv_ids(ref_text)
            refs_of_ref = {r for r in refs_of_ref if r != ref_paper_id.split('v')[0]}
            
            # Filter to only papers that exist in our database
            existing_refs_of_ref = filter_existing_references(refs_of_ref)
            
            # Update this reference paper's connections
            if existing_refs_of_ref:
                update_paper_connections(ref_paper_id, existing_refs_of_ref)
                second_degree_refs[ref_paper_id] = list(existing_refs_of_ref)
                
        except Exception as e:
            log_error(ref_paper_id, "Second-degree processing error", str(e))
            continue

    return second_degree_refs

def main(paper_id):
    with open(ERROR_LOG_FILE, 'w') as f:
        f.write(f"Reference extraction log started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    # Get first degree connections with full details
    references = get_paper_connections(paper_id)
    
    if not references:
        references = process_paper(paper_id)
        references = filter_existing_references(references)
    
    # Get second degree connections with full details
    second_degree_refs = process_connections(references)
    
    # Get third degree connections with full details
    sec_degree_papers = [paper for paperset in second_degree_refs.values() for paper in paperset]
    
    third_degree_refs = process_connections(sec_degree_papers)
    
    # Format the first degree connections to match expected structure
    first_degree_formatted = {
        "source_id": paper_id,
        "source_title": get_paper_title(paper_id),
        "connections": references
    }
    
    result = {
        'first_degree': first_degree_formatted,
        'second_degree': second_degree_refs,
        'third_degree': third_degree_refs
    }
    
    print(f"DEBUG: Connection structure format - first_degree: {type(result['first_degree'])}, second_degree: {type(result['second_degree'])}, third_degree: {type(result['third_degree'])}")
    print(f"DEBUG: Second degree keys sample: {list(result['second_degree'].keys())[:3] if result['second_degree'] else []}")
    
    return result

def get_paper_title(paper_id):
    """Helper function to get just the paper title"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM papers WHERE id = ?", (paper_id,))
        row = cursor.fetchone()
        return row[0] if row else f"Paper {paper_id}"
    except Exception as e:
        return f"Paper {paper_id}"

def get_paper_details(paper_id):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, authors, abstract, categories, year, month, day
            FROM papers 
            WHERE id = ?
        """, (paper_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "title": row[1],
                "authors": row[2],
                "abstract": row[3].strip() if row[3] else "",
                "categories": row[4],
                "year": row[5],
                "month": row[6],
                "day": row[7]
            }
        else:
            return None
    except Exception as e:
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <paper_id>")
        sys.exit(1)
    paper_id = sys.argv[1]
    main(paper_id)

import sqlite3
from typing import Optional, Set, Dict, List
import json

# 603789 entries
# paper website: https://arxiv.org/abs/ID
# paper pdf: https://arxiv.org/pdf/ID

def setup_database():
    conn = sqlite3.connect('papers.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS papers (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        authors TEXT,
        abstract TEXT,
        categories TEXT,
        doi INTEGER,
        connected_papers TEXT,
        year INTEGER,
        month INTEGER,
        day INTEGER
    )
    ''')
    
    conn.commit()
    conn.close()

def process_json_lines(file_path: str, db_path: str = 'papers.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        entries = 0
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                paper = json.loads(line)
                
                # Filter for CS categories
                categories = paper.get('categories', '')
                if not categories.startswith('cs.'):
                    continue
                
                # Extract date components
                update_date = paper.get('update_date', '')
                year = None
                month = None
                day = None
                if update_date:
                    date_parts = update_date.split('-')
                    if len(date_parts) >= 1:
                        year = int(date_parts[0]) if date_parts[0] else None
                    if len(date_parts) >= 2:
                        month = int(date_parts[1]) if date_parts[1] else None
                    if len(date_parts) >= 3:
                        day = int(date_parts[2]) if date_parts[2] else None
                
                # Insert into database
                cursor.execute('''
                INSERT OR REPLACE INTO papers (
                    id, title, authors, abstract, categories, doi, year, month, day
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    paper['id'],
                    paper.get('title', ''),
                    paper.get('authors', ''),
                    paper.get('abstract', ''),
                    categories,
                    paper.get('doi'),
                    year,
                    month,
                    day
                ))
                entries += 1
                
            except json.JSONDecodeError as e:
                print(f"Skipping invalid JSON line: {e}")
                continue
            except Exception as e:
                print(f"Error processing paper {paper.get('id', 'unknown')}: {e}")
                continue
    
    conn.commit()
    conn.close()
    print("Data for", entries, "entries import complete.")

setup_database()
# data from: https://www.kaggle.com/datasets/Cornell-University/arxiv/data
process_json_lines('arxiv-metadata-oai-snapshot.json')

# import re

# arxiv_pattern = r'''
#     (?:arXiv:)?                        # Optional arXiv: prefix
#     (?:
#         (?:cs[.\s]?[A-Za-z]{2}/)?     # Optional cs.XX/ or cs XX/ prefix
#         (cs\/\d{7})                    # cs/ + exactly 7 digits (group 1)
#         |
#         (\d{4}\.\d{4,5})               # ####.#### or ####.##### (group 2)
#     )
#     (?:v\d+)?                          # Optional version suffix
# '''

# # Compiled regex with verbose mode and case insensitive
# arxiv_regex = re.compile(arxiv_pattern, re.VERBOSE | re.IGNORECASE)

# def extract_normalized_arxiv_ids(text: str) -> Set[str]:
#     """Extract and normalize arXiv IDs from text."""
#     matches = arxiv_regex.finditer(text)
#     ids = set()
    
#     for match in matches:
#         # Group 1 captures cs/####### format
#         if match.group(1):
#             ids.add(match.group(1).lower()  # Normalize to lowercase
            
#         # Group 2 captures ####.####/####.##### format
#         elif match.group(2):
#             ids.add(match.group(2))
            
#     return ids

# make sure only adds papers that exist in database and that it correctly gets CS papers and adds them to the connections
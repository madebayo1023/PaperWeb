import sqlite3
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import os
from transformers import AutoTokenizer, AutoModel
import torch
from tqdm import tqdm

# Constants
PAPERS_DB_PATH = 'papers.db'
EMBEDDINGS_DB_PATH = 'embeddings.db'
BATCH_SIZE = 100
MODEL_NAME = "avsolatorio/GIST-Embedding-v0"

tokenizer = None
model = None

def load_model():
    global tokenizer, model
    if tokenizer is None or model is None:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
        model = AutoModel.from_pretrained(MODEL_NAME, trust_remote_code=True)
        
        if torch.backends.mps.is_available():
            model = model.to("mps")
        elif torch.cuda.is_available():
            model = model.to("cuda")

def setup_embeddings_database():
    conn = sqlite3.connect(EMBEDDINGS_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS paper_embeddings (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        abstract TEXT,
        embedding BLOB,
        authors TEXT,
        categories TEXT,
        year INTEGER
    )
    ''')
    
    conn.commit()
    conn.close()

def get_papers_from_db(batch_size: int = BATCH_SIZE, offset: int = 0) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(PAPERS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, title, abstract, authors, categories, year
    FROM papers
    WHERE abstract IS NOT NULL AND abstract != ''
    LIMIT ? OFFSET ?
    ''', (batch_size, offset))
    
    papers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return papers

def count_papers_with_abstracts() -> int:
    conn = sqlite3.connect(PAPERS_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT COUNT(*) FROM papers
    WHERE abstract IS NOT NULL AND abstract != ''
    ''')
    
    count = cursor.fetchone()[0]
    conn.close()
    return count

def generate_embeddings(texts: List[str]) -> np.ndarray:
    """Generate embeddings for a list of texts using GIST-Embedding model."""
    load_model()
    
    max_hf_batch_size = 16
    all_embeddings = []
    
    for i in range(0, len(texts), max_hf_batch_size):
        batch_texts = texts[i:i+max_hf_batch_size]
        
        inputs = tokenizer(batch_texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
        
        if torch.backends.mps.is_available():
            inputs = {k: v.to("mps") for k, v in inputs.items()}
        elif torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model(**inputs)
            batch_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()  # Using CLS token
        
        all_embeddings.append(batch_embeddings)
    
    return np.vstack(all_embeddings)

def store_embeddings(papers: List[Dict[str, Any]], embeddings: np.ndarray):
    conn = sqlite3.connect(EMBEDDINGS_DB_PATH)
    cursor = conn.cursor()
    
    for i, paper in enumerate(papers):
        embedding_blob = embeddings[i].tobytes()
        
        cursor.execute('''
        INSERT OR REPLACE INTO paper_embeddings
        (id, title, abstract, embedding, authors, categories, year)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            paper['id'],
            paper['title'],
            paper['abstract'],
            embedding_blob,
            paper['authors'],
            paper['categories'],
            paper['year']
        ))
    
    conn.commit()
    conn.close()

def process_all_papers():
    setup_embeddings_database()
    
    total_papers = count_papers_with_abstracts()
    
    processed = 0
    while processed < total_papers:
        papers = get_papers_from_db(BATCH_SIZE, processed)
        if not papers:
            break
            
        # Generate embeddings for abstracts
        abstracts = [paper['abstract'] for paper in papers]
        embeddings = generate_embeddings(abstracts)
        
        # Store in the database
        store_embeddings(papers, embeddings)
        
        processed += len(papers)

def get_embedding_for_paper(paper_id: str) -> Optional[np.ndarray]:
    conn = sqlite3.connect(EMBEDDINGS_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT embedding FROM paper_embeddings
    WHERE id = ?
    ''', (paper_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return np.frombuffer(result[0], dtype=np.float32)
    return None

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def find_related_papers(paper_id: str, top_n: int = 10) -> List[Dict[str, Any]]:
    target_embedding = get_embedding_for_paper(paper_id)
    if target_embedding is None:
        return []
    
    conn = sqlite3.connect(EMBEDDINGS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, title, abstract, embedding, authors, categories, year
    FROM paper_embeddings
    WHERE id != ?
    ''', (paper_id,))
    
    related_papers = []
    rows = cursor.fetchall()
    
    for row in rows:
        paper_data = dict(row)
        embedding = np.frombuffer(paper_data.pop('embedding'), dtype=np.float32)
        similarity = cosine_similarity(target_embedding, embedding)
        
        related_papers.append({
            **paper_data,
            'similarity': float(similarity)
        })
    
    conn.close()
    
    related_papers.sort(key=lambda x: x['similarity'], reverse=True)
    return related_papers[:top_n]

def fuzzy_search_related_papers(query_text: str, top_n: int = 10) -> List[Dict[str, Any]]:
    query_embedding = generate_embeddings([query_text])[0]
    
    conn = sqlite3.connect(EMBEDDINGS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, title, abstract, embedding, authors, categories, year
    FROM paper_embeddings
    ''')
    
    related_papers = []
    rows = cursor.fetchall()
    
    for row in rows:
        paper_data = dict(row)
        embedding = np.frombuffer(paper_data.pop('embedding'), dtype=np.float32)
        similarity = cosine_similarity(query_embedding, embedding)
        
        related_papers.append({
            **paper_data,
            'similarity': float(similarity)
        })
    
    conn.close()
    
    related_papers.sort(key=lambda x: x['similarity'], reverse=True)
    return related_papers[:top_n]

def fuzzy_search_get_all_related_papers(query_text: str) -> List[Dict[str, Any]]:
    query_embedding = generate_embeddings([query_text])[0]
    
    conn = sqlite3.connect(EMBEDDINGS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, title, abstract, embedding, authors, categories, year
    FROM paper_embeddings
    ''')
    
    all_papers = []
    rows = cursor.fetchall()
    
    for row in rows:
        paper_data = dict(row)
        embedding = np.frombuffer(paper_data.pop('embedding'), dtype=np.float32)
        similarity = cosine_similarity(query_embedding, embedding)
        
        all_papers.append({
            **paper_data,
            'similarity': float(similarity)
        })
    
    conn.close()
    
    all_papers.sort(key=lambda x: x['similarity'], reverse=True)
    return all_papers

def add_paper_to_embeddings(paper: Dict[str, Any]) -> bool:
    """
    Add a single paper to the embeddings database
    
    Args:
        paper: Dictionary containing paper data with keys:
              id, title, abstract, authors, categories, year
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Make sure the database is set up
        setup_embeddings_database()
        
        # Make sure the paper has an abstract
        if not paper.get('abstract'):
            print(f"Paper {paper['id']} has no abstract, skipping embedding generation")
            return False
        
        # Generate embedding for the paper
        abstracts = [paper['abstract']]
        embeddings = generate_embeddings(abstracts)
        
        if len(embeddings) == 0:
            print(f"Failed to generate embedding for paper {paper['id']}")
            return False
        
        # Store in the database
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

if __name__ == "__main__":
    process_all_papers()
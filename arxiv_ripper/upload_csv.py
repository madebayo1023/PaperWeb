import sqlite3
import csv
from pathlib import Path

def upload_csv_to_db(csv_file_path, db_file='papers.db', batch_size=1000):
    """
    Upload CSV data to SQLite database with batching for efficiency.
    
    Args:
        csv_file_path (str): Path to the CSV file
        db_file (str): Path to the SQLite database file
        batch_size (int): Number of records to insert in each batch
    """    
    # Connect to the SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Check if the CSV file exists
    if not Path(csv_file_path).is_file():
        print(f"Error: CSV file not found at {csv_file_path}")
        return
    
    try:
        # Read the CSV file
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            csvreader = csv.DictReader(csvfile)
            
            # Prepare the SQL insert statement
            insert_sql = """
            INSERT OR REPLACE INTO papers (
                id, title, authors, abstract, categories, 
                doi, connected_papers, year, month, day
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            batch = []
            total_records = 0
            
            # Process each row in the CSV
            for row in csvreader:
                # Prepare the data tuple for insertion
                data = (
                    row['id'],
                    row['title'],
                    row.get('authors'),
                    row.get('abstract'),
                    row.get('categories'),
                    None,  # DOI is NULL since not in CSV
                    row.get('connected_papers'),
                    int(row['year']) if row.get('year') else None,
                    int(row['month']) if row.get('month') else None,
                    int(row['day']) if row.get('day') else None
                )
                
                batch.append(data)
                
                # Execute when batch size is reached
                if len(batch) >= batch_size:
                    cursor.executemany(insert_sql, batch)
                    conn.commit()
                    total_records += len(batch)
                    print(f"Inserted {total_records} records so far...")
                    batch = []
            
            # Insert any remaining records in the final batch
            if batch:
                cursor.executemany(insert_sql, batch)
                conn.commit()
                total_records += len(batch)
            
            print(f"Successfully uploaded {total_records} records from {csv_file_path} to {db_file}")
            
    
    except Exception as e:
        conn.rollback()
        print(f"Error occurred: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    csv_path = "arxiv_ripper/arxiv_cs_recent.csv"
    upload_csv_to_db(csv_path, db_file="papers.db", batch_size=500)
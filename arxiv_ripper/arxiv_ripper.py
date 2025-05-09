import urllib.request as libreq
import xml.etree.ElementTree as ET
import csv
import time
import sys
from datetime import datetime, timedelta

def format_arxiv_date(dt):
    """Format datetime object in arXiv API expected format"""
    return dt.strftime("%Y%m%d%H%M%S")

def extract_arxiv_id(full_url):
    """
    Extract clean arXiv ID from full URL, handling both formats:
    - Modern: http://arxiv.org/abs/2504.13414v1 -> 2504.13414
    - Legacy: http://arxiv.org/abs/cs/0205001v1 -> cs/0205001
    """
    parts = full_url.split('/abs/')
    if len(parts) < 2:
        return full_url  # fallback
    return parts[1].split('v')[0]  # remove version

def get_date_ranges(start_date, end_date, chunk_days=7):
    """Generate date ranges in chunks of chunk_days days"""
    current_date = start_date
    while current_date < end_date:
        next_date = current_date + timedelta(days=chunk_days)
        if next_date > end_date:
            next_date = end_date
        yield (current_date, next_date)
        current_date = next_date + timedelta(seconds=1)  # avoid overlap

def main():
    # Default to the last_updated.txt file if no date is provided
    with open('arxiv_ripper/last_updated.txt', 'r') as f:
        last_updated = f.read()
        try:
            last_updated_date = datetime.strptime(last_updated, "%Y%m%d")
            last_updated_date = last_updated_date.replace(hour=0, minute=0, second=0)
        except ValueError:
            print("Issue with last_updated.txt format. Please ensure you are using YYYYMMDD.")
            return 1
    
    if len(sys.argv) > 1:
        try:
            input_date = datetime.strptime(sys.argv[1], "%Y%m%d")
            input_date = input_date.replace(hour=0, minute=0, second=0)
        except ValueError:
            print("Invalid date format. Please use YYYYMMDD")
            return 1
    else:
        days_since_last_update = (datetime.now() - last_updated_date).days
        print(f"Usage: python3 arxiv_ripper.py last_updated(YYYYMMDD) \nUsing default: last {days_since_last_update} days")
        input_date = last_updated_date

    end_date = datetime(2025, 5, 1)
    
    with open('arxiv_ripper/arxiv_cs_recent.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            'id', 'title', 'authors', 'abstract', 
            'categories', 'connected_papers', 'year', 'month', 'day'
        ])

        paper_count = 0
        papers_per_request = 100
        chunk_days = 7  # Process 1 week at a time

        # print(f"\n\nProcessing date range: {input_date.date()} to {end_date.date()}\n\n")
        
        for date_range in get_date_ranges(input_date, end_date, chunk_days):
            start_dt, end_dt = date_range
            start_date_str = format_arxiv_date(start_dt)
            end_date_str = format_arxiv_date(end_dt)
            
            print(f"\n\nProcessing date range: {start_dt.date()} to {end_dt.date()}\n\n")
            
            query = f"cat:cs.*+AND+submittedDate:[{start_date_str}+TO+{end_date_str}]"
            
            # Start with 0 and increment until no more papers are found
            start = 0
            while True:
                url = f"http://export.arxiv.org/api/query?search_query={query}&start={start}&max_results={papers_per_request}&sortBy=submittedDate&sortOrder=ascending"
                
                try:
                    print(f"Requesting URL: {url}")
                    with libreq.urlopen(url) as response:
                        xml_data = response.read()
                    root = ET.fromstring(xml_data)

                    entries = root.findall("{http://www.w3.org/2005/Atom}entry")
                    if not entries:
                        print(f"\n\nNo more entries found in this date range.\n\n")
                        break
                    
                    for entry in entries:
                        # Extract raw data
                        full_url = entry.find("{http://www.w3.org/2005/Atom}id").text
                        title = entry.find("{http://www.w3.org/2005/Atom}title").text
                        authors = ", ".join([author.find("{http://www.w3.org/2005/Atom}name").text 
                                   for author in entry.findall("{http://www.w3.org/2005/Atom}author")])
                        published = entry.find("{http://www.w3.org/2005/Atom}published").text
                        abstract = entry.find("{http://www.w3.org/2005/Atom}summary").text.strip() if entry.find("{http://www.w3.org/2005/Atom}summary") is not None else ""
                        categories = ", ".join([cat.get('term') for cat in entry.findall("{http://www.w3.org/2005/Atom}category")])
                        
                        # Process data
                        arxiv_id = extract_arxiv_id(full_url)
                        connected_papers = ""
                        
                        try:
                            pub_date = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
                            year = pub_date.year
                            month = pub_date.month
                            day = pub_date.day
                        except:
                            year, month, day = 0, 0, 0
                        
                        writer.writerow([
                            arxiv_id, title, authors, abstract,
                            categories, connected_papers, year, month, day
                        ])
                        
                        paper_count += 1
                        print(f"Paper {paper_count} - {arxiv_id}: {title[:50]}...")

                    start += papers_per_request
                    time.sleep(4)  # Arxiv rate limit

                except Exception as e:
                    print(f"An error occurred: {e}")
                    break

    with open('arxiv_ripper/last_updated.txt', 'w') as f:
        f.write(datetime.now().strftime("%Y%m%d"))

    print(f"\nTotal papers found: {paper_count}")
    print("Data successfully written to arxiv_cs_recent.csv")
    # ascii_art = pyfiglet.figlet_format("Completed!")
    # print("\033" + ascii_art + "\033")
    return 0

if __name__ == "__main__":
    main()
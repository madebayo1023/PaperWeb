#!/usr/bin/env python3
import argparse
import sys
from embed import fuzzy_search_related_papers
from typing import List, Dict, Any

def display_paper(paper: Dict[str, Any], show_abstract: bool = False):
    print(f"\n{'=' * 80}")
    print(f"ID: {paper['id']}")
    print(f"Title: {paper['title']}")
    print(f"Authors: {paper['authors']}")
    print(f"Year: {paper.get('year', 'N/A')}")
    print(f"Categories: {paper.get('categories', 'N/A')}")
    print(f"Similarity score: {paper['similarity']:.4f}")
    
    if show_abstract and paper.get('abstract'):
        print("\nAbstract:")
        print(paper['abstract'])
    
    print(f"{'=' * 80}")

def main():
    parser = argparse.ArgumentParser(description="Search for papers by text query using embeddings")
    parser.add_argument("query", help="Text query to search for")
    parser.add_argument("-n", "--num", type=int, default=5, 
                       help="Number of papers to display (default: 5)")
    parser.add_argument("-a", "--abstract", action="store_true",
                       help="Show abstracts of found papers")
    args = parser.parse_args()

    print(f"Searching for papers related to: '{args.query}'...")
    print("This will generate an embedding for your query and find similar papers...")
    papers = fuzzy_search_related_papers(args.query, top_n=args.num)
    
    if not papers:
        print("No matching papers found.")
        sys.exit(1)
    
    print(f"\nFound {len(papers)} papers:")
    for i, paper in enumerate(papers, 1):
        print(f"\n[{i}/{len(papers)}]")
        display_paper(paper, show_abstract=args.abstract)
    
    print("\nDone!")

if __name__ == "__main__":
    main() 
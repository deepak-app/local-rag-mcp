#!/usr/bin/env python3
import os
import sys
import argparse
import time
from pathlib import Path
from txtai.embeddings import Embeddings

# ANSI color escape codes for a premium CLI look
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'

def format_score(score):
    """Format similarity score as a colored percentage."""
    percentage = score * 100
    if score >= 0.8:
        color = Colors.GREEN
    elif score >= 0.6:
        color = Colors.YELLOW
    else:
        color = Colors.CYAN
    return f"{color}{percentage:.2f}%{Colors.END}"

def print_results(results, query):
    """Format and print search results nicely in the terminal."""
    if not results:
        print(f"\n{Colors.YELLOW}[!] No matching passages found.{Colors.END}\n")
        return

    print(f"\n{Colors.BOLD}{Colors.HEADER}Search Results for: '{query}'{Colors.END}")
    print(f"{Colors.DIM}{'=' * 60}{Colors.END}")

    for idx, match in enumerate(results, 1):
        # When content=True, match is a dict containing 'id', 'text', 'score', and custom metadata
        text = match.get("text", "").strip()
        score = match.get("score", 0.0)
        file_path = match.get("file_path", "Unknown file")
        chunk_id = match.get("chunk_id", 0)

        print(f"\n{Colors.BOLD}{idx}. [Match Score: {format_score(score)}]{Colors.END}")
        print(f"{Colors.BLUE}Source:{Colors.END} {Colors.CYAN}{file_path}{Colors.END} (Chunk #{chunk_id})")
        print(f"{Colors.DIM}------------------------------------------------------------{Colors.END}")
        
        # Indent and print the chunk text
        indented_text = "\n".join(f"  {line}" for line in text.splitlines())
        print(f"{indented_text}")
        print(f"{Colors.DIM}{'=' * 60}{Colors.END}")
    print()

def interactive_mode(embeddings, limit, threshold):
    """Run an interactive CLI search loop."""
    print(f"\n{Colors.BOLD}{Colors.GREEN}=== Semantic Search Interactive Shell ==={Colors.END}")
    print("Type your search query and press Enter.")
    print("Type 'exit', 'quit', or press Ctrl+C to stop.\n")
    
    while True:
        try:
            query = input(f"{Colors.BOLD}{Colors.BLUE}Search Query > {Colors.END}").strip()
            if not query:
                continue
                
            if query.lower() in ('exit', 'quit'):
                print("Goodbye!")
                break
                
            escaped_query = query.replace("'", "''")
            sql_query = f"SELECT id, text, file_path, chunk_id, score FROM txtai WHERE similar('{escaped_query}') LIMIT {limit}"
            results = embeddings.search(sql_query)
            
            # Apply threshold if specified
            if threshold > 0.0:
                results = [r for r in results if r.get("score", 0.0) >= threshold]
                
            print_results(results, query)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"{Colors.RED}[!] Error running query: {e}{Colors.END}\n")

def main():
    parser = argparse.ArgumentParser(description="Semantic Search CLI using txtai")
    parser.add_argument("-q", "--query", help="Search query (triggers single-search mode)")
    parser.add_argument("--db-path", default="db/txtai_index", help="Path to the saved txtai index (default: db/txtai_index)")
    parser.add_argument("-k", "--limit", type=int, default=5, help="Maximum number of search results (default: 5)")
    parser.add_argument("-t", "--threshold", type=float, default=0.0, help="Similarity score threshold (0.0 to 1.0, default: 0.0)")
    
    args = parser.parse_args()
    
    # Check if index exists
    db_dir = Path(args.db_path)
    # The txtai index saves a 'config' and a 'documents' or 'embeddings' file inside db_path directory
    # or the db_path can be a single file depending on configuration.
    # In either case, let's make sure the path exists.
    if not db_dir.exists():
        print(f"{Colors.RED}[!] Error: Index directory '{args.db_path}' not found.{Colors.END}")
        print(f"Please run the indexer first: python3 indexer.py --doc-dir <doc_dir>")
        sys.exit(1)
        
    print(f"[*] Loading semantic index from: {args.db_path}...")
    start_time = time.time()
    
    try:
        embeddings = Embeddings()
        embeddings.load(args.db_path)
        print(f"[*] Index loaded in {time.time() - start_time:.2f} seconds.")
    except Exception as e:
        print(f"{Colors.RED}[!] Error loading index: {e}{Colors.END}")
        print("Please check that the index was built successfully.")
        sys.exit(1)
        
    if args.query:
        # Single query mode
        escaped_query = args.query.replace("'", "''")
        sql_query = f"SELECT id, text, file_path, chunk_id, score FROM txtai WHERE similar('{escaped_query}') LIMIT {args.limit}"
        results = embeddings.search(sql_query)
        if args.threshold > 0.0:
            results = [r for r in results if r.get("score", 0.0) >= args.threshold]
        print_results(results, args.query)
    else:
        # Interactive shell mode
        interactive_mode(embeddings, args.limit, args.threshold)

if __name__ == "__main__":
    main()

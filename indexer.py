#!/usr/bin/env python3
import os
import sys
import argparse
import time
import nltk
import subprocess
import tempfile
from pathlib import Path
from txtai.embeddings import Embeddings
from docling.document_converter import DocumentConverter

_docling_converter = None

def get_docling_converter():
    global _docling_converter
    if _docling_converter is None:
        _docling_converter = DocumentConverter()
    return _docling_converter

def extract_text_from_file(file_path):
    """
    Extracts text/markdown content from a file using docling or native reading.
    Supports: .txt, .md, .markdown, .rst, .pdf, .docx, .doc
    """
    suffix = file_path.suffix.lower()
    
    if suffix in {'.txt', '.md', '.markdown', '.rst'}:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
            
    elif suffix in {'.docx', '.pdf'}:
        print(f"[*] Parsing {suffix} file with Docling: {file_path.name}")
        converter = get_docling_converter()
        result = converter.convert(str(file_path))
        return result.document.export_to_markdown()
        
    elif suffix == '.doc':
        print(f"[*] Parsing legacy .doc file with LibreOffice & Docling: {file_path.name}")
        with tempfile.TemporaryDirectory() as temp_dir:
            cmd = [
                "libreoffice", "--headless",
                "--convert-to", "docx",
                "--outdir", temp_dir,
                str(file_path)
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            except Exception as e:
                raise RuntimeError(f"Failed to convert .doc to .docx using LibreOffice: {e}")
                
            converted_files = list(Path(temp_dir).glob("*.docx"))
            if not converted_files:
                raise FileNotFoundError("LibreOffice conversion succeeded but did not produce a .docx file.")
                
            converter = get_docling_converter()
            result = converter.convert(str(converted_files[0]))
            return result.document.export_to_markdown()
            
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

def download_nltk_resources():
    """Ensure NLTK punkt_tab is downloaded for sentence tokenization."""
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        print("[*] Downloading NLTK tokenizer resources ('punkt_tab')...")
        nltk.download('punkt_tab', quiet=True)

def chunk_text(text, max_chars=500, overlap_sentences=1):
    """
    Chunk text into segments with a maximum character length and a specified sentence overlap.
    """
    # Split the document into sentences using NLTK
    sentences = nltk.sent_tokenize(text)
    chunks = []
    
    current_sentences = []
    current_length = 0
    
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
            
        sent_len = len(sent)
        
        # If adding this sentence would exceed the limit, and we have existing sentences in our chunk
        if current_length + sent_len > max_chars and current_sentences:
            chunk_content = " ".join(current_sentences)
            chunks.append(chunk_content)
            
            # Slide window back by overlap_sentences count
            if overlap_sentences > 0 and len(current_sentences) > overlap_sentences:
                current_sentences = current_sentences[-overlap_sentences:]
                current_length = sum(len(s) + 1 for s in current_sentences) - 1
            else:
                current_sentences = []
                current_length = 0
        
        current_sentences.append(sent)
        # If we just started a chunk, length is sent_len. Otherwise, it is sent_len + 1 (for space)
        current_length += sent_len + (1 if current_length > 0 else 0)
        
    # Add any remaining sentences in the final chunk
    if current_sentences:
        chunk_content = " ".join(current_sentences)
        chunks.append(chunk_content)
        
    return chunks

def scan_documents(doc_dir):
    """
    Recursively scan the doc_dir for compatible documents.
    """
    supported_extensions = {'.txt', '.md', '.markdown', '.rst', '.pdf', '.docx', '.doc'}
    doc_path = Path(doc_dir)
    if not doc_path.exists():
        print(f"[!] Warning: Document directory '{doc_dir}' does not exist. Creating it.")
        doc_path.mkdir(parents=True, exist_ok=True)
        return []
        
    documents = []
    for file_path in doc_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            documents.append(file_path)
            
    return documents

def build_index(doc_dir, db_path, model_name, max_chars, overlap_sentences):
    """
    Reads documents, chunks them, generates embeddings, and indexes them.
    """
    print(f"[*] Scanning for documents in: {doc_dir}")
    doc_files = scan_documents(doc_dir)
    
    if not doc_files:
        print("[!] No supported documents found. Please place compatible files (.txt, .md, .markdown, .rst, .pdf, .docx, .doc) in the doc directory.")
        return False
        
    print(f"[*] Found {len(doc_files)} files. Extracting and chunking contents...")
    
    rows = []
    chunk_count = 0
    
    for file_path in doc_files:
        # Get relative path for cleaner metadata
        try:
            rel_path = file_path.relative_to(doc_dir)
        except ValueError:
            rel_path = file_path
            
        try:
            content = extract_text_from_file(file_path)
            file_chunks = chunk_text(content, max_chars=max_chars, overlap_sentences=overlap_sentences)
            
            for idx, chunk in enumerate(file_chunks):
                if not chunk.strip():
                    continue
                # Unique ID: file_name_chunk_idx
                uid = f"{rel_path}_{idx}"
                # data is a dict representing text and metadata
                data = {
                    "text": chunk,
                    "file_path": str(rel_path),
                    "chunk_id": idx
                }
                rows.append((uid, data, None))
                chunk_count += 1
                
        except Exception as e:
            print(f"[!] Error processing file {file_path}: {e}")
            
    if not rows:
        print("[!] No text content chunked successfully.")
        return False
        
    print(f"[*] Created {chunk_count} total text chunks from {len(doc_files)} documents.")
    print(f"[*] Initializing txtai embeddings with model: {model_name}...")
    
    start_time = time.time()
    
    # Initialize txtai Embeddings
    # content=True enables SQLite database to store metadata and text
    embeddings = Embeddings({
        "path": model_name,
        "content": True,
        "backend": "faiss",
        "metric": "cosine"
    })
    
    print("[*] Generating embeddings and indexing documents (this might take a moment)...")
    embeddings.index(rows)
    
    # Ensure the parent directory of db_path exists
    db_parent = Path(db_path).parent
    db_parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[*] Saving index to: {db_path}")
    embeddings.save(db_path)
    
    duration = time.time() - start_time
    print(f"[+] Indexing completed successfully in {duration:.2f} seconds!")
    print(f"[+] Index saved to {db_path}.")
    return True

def main():
    parser = argparse.ArgumentParser(description="Semantic Document Indexer using txtai")
    parser.add_argument("--doc-dir", default="doc", help="Directory containing documents to index (default: doc)")
    parser.add_argument("--db-path", default="db/txtai_index", help="Output path for the saved index (default: db/txtai_index)")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2", help="Pre-trained sentence transformer model (default: sentence-transformers/all-MiniLM-L6-v2)")
    parser.add_argument("--max-chars", type=int, default=500, help="Max length in characters for each chunk (default: 500)")
    parser.add_argument("--overlap", type=int, default=1, help="Sentence overlap count between chunks (default: 1)")
    
    args = parser.parse_args()
    
    download_nltk_resources()
    
    success = build_index(
        doc_dir=args.doc_dir,
        db_path=args.db_path,
        model_name=args.model,
        max_chars=args.max_chars,
        overlap_sentences=args.overlap
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()

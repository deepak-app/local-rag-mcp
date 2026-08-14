# Semantic Document Indexer & Local Notes Search MCP Server

A high-performance semantic document indexing and retrieval system powered by **txtai** (backed by **FAISS** vector database) and **IBM Docling**. The project also includes an interactive search CLI and a **Model Context Protocol (MCP)** server, enabling LLM agents (like Claude Desktop) to query your private documents semantically.

---

## 🌟 Key Features

*   **Multi-Format Document Parsing**: Natively extracts structured text and layout elements from `.txt`, `.md`, `.markdown`, `.rst`, `.pdf`, `.docx`, and legacy binary `.doc` files (using headless LibreOffice on the fly).
*   **Semantic Overlapping Chunking**: Tokenizes text with sentence-level boundaries (`nltk`) into overlapping segments to prevent information loss.
*   **FAISS Vector Index**: Leverages similarity search using cosine distance via the `sentence-transformers/all-MiniLM-L6-v2` embeddings model.
*   **Persistent SQLite Metadata**: Keeps a mapping of document locations, chunk indexes, and raw text in a companion database.
*   **Interactive CLI & Single-Search**: Search from standard terminal prompts or query using a continuous search shell.
*   **Model Context Protocol (MCP)**: Exposes a stdio-based MCP tool `search_local_notes` that allows AI agents to read and search local records.

---

## 📂 Project Structure

```text
├── db/                    # Directory where saved vector indexes are stored
│   └── txtai_index/       # Active FAISS & SQLite databases
├── doc/                   # Source documents directory (add your notes/PDFs here)
├── indexer.py             # Scanning and indexing script
├── search.py              # CLI and interactive search utility
├── mcp_server.py          # Stdio-based MCP server using FastMCP
├── mcp_wrapper.sh         # Executable shell wrapper for the MCP server
└── README.md              # Project documentation
```

---

## 🚀 Getting Started

### 1. Requirements
Ensure you have the following installed on your system:
*   Python 3.10+
*   **LibreOffice** (optional, required only for extracting legacy binary `.doc` formats on Linux)

### 2. Scanning & Indexing Documents
Place your documents (notes, receipts, research PDFs, Word files) in the `doc/` directory, then execute the indexer:
```bash
.venv/bin/python3 indexer.py --doc-dir doc --db-path db/txtai_index
```
*Options:*
*   `--max-chars`: Upper character limit per text chunk (default: `500`).
*   `--overlap`: Number of sentences to overlap between chunks (default: `1`).
*   `--model`: Embedding model to load (default: `sentence-transformers/all-MiniLM-L6-v2`).

### 3. Searching the Index
You can query the index via CLI:

#### Single Search Command:
```bash
.venv/bin/python3 search.py -q "instructions to cook spaghetti"
```

#### Interactive Search Shell:
Run without arguments to start the interactive loop:
```bash
.venv/bin/python3 search.py
```
Type your query and hit **Enter**. Type `exit` or `quit` to exit.

*Options:*
*   `-k`, `--limit`: Maximum results to return (default: `5`).
*   `-t`, `--threshold`: Score similarity threshold from 0.0 to 1.0 (default: `0.0`).

---

## 🤖 Model Context Protocol (MCP) Integration

The server provides a standard Model Context Protocol tool that feeds context to AI clients.

### 1. Verification
Ensure the wrapper script runs successfully in stdio mode:
```bash
./mcp_wrapper.sh
```
*(The command should stay active, listening for JSON-RPC messages on standard input).*

### 2. Setup with Claude Desktop
To integrate this tool with **Claude Desktop**, you can configure it either automatically or manually:

#### Option A: Automatic Configuration (Quickest)
Run the following command in your terminal. This will automatically create the directory and write the configuration file pointing to your current folder path:
```bash
mkdir -p ~/.config/Claude && echo "{\"mcpServers\":{\"local-notes-search\":{\"command\":\"$(pwd)/mcp_wrapper.sh\"}}}" > ~/.config/Claude/claude_desktop_config.json
```
*(Note: This creates a new configuration file. If you already have existing MCP servers configured, use Option B instead to avoid overwriting them).*

#### Option B: Manual Configuration
Open your desktop configuration file (located at `~/.config/Claude/claude_desktop_config.json` on Linux) and add the following server entry to the `mcpServers` block:

```json
{
  "mcpServers": {
    "local-notes-search": {
      "command": "/home/appaladeepak/Public/the_search/mcp_wrapper.sh"
    }
  }
}
```
*(Be sure to replace the path with your actual absolute path if you clone the repository elsewhere).*

Restart Claude Desktop, and the **Local Notes Search** tool (`search_local_notes`) will be available. Claude will automatically query this tool when you ask it questions about your indexed documents.

---

## 🛠️ How it Works

1.  **Extraction**: The system recursively scans the directory. Plain text files are read natively. PDF/Word documents are parsed by `Docling` to extract layout-aware markdown representations. Binary `.doc` files are first headlessly converted to `.docx` via `libreoffice`.
2.  **Segmentation**: NLTK's `punkt_tab` segmenter splits the extracted markdown into sentences. Chunks are aggregated up to the `--max-chars` threshold with overlap sentences.
3.  **Indexing**: Embeddings are generated and inserted into a FAISS index. The index uses cosine similarity for vector comparison. Raw text and source information are stored in an SQLite relational store under `db/txtai_index/documents`.
4.  **SQL Querying**: The search scripts query the index using SQL style:
    ```sql
    SELECT id, text, file_path, chunk_id, score 
    FROM txtai 
    WHERE similar(:query) 
    LIMIT :limit
    ```

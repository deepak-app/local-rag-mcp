import os
import sys
from fastmcp import FastMCP
from txtai.embeddings import Embeddings

# Initialize the FastMCP server
mcp = FastMCP("Local Notes Search")

# Resolve the absolute path to your txtai index
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE_DIR, "db", "txtai_index")

# Initialize and load your existing txtai index (loaded on server startup)
embeddings = Embeddings()
embeddings.load(INDEX_PATH)

@mcp.tool()
def search_local_notes(query: str, limit: int = 3) -> str:
    """
    Search semantically through the user's private documentation, notes, 
    and log files to retrieve contextual answers.
    
    Args:
        query: The natural language question or concept to search for.
        limit: The maximum number of relevant paragraphs/chunks to return.
    """
    try:
        # Run similarity search (txtai returns list of dicts/tuples containing content)
        results = embeddings.search(query, limit)
        
        if not results:
            return "No matching or semantically relevant notes found."
            
        # Format the output chunks beautifully for the AI agent to read
        formatted_results = []
        for i, result in enumerate(results, 1):
            # txtai search returns a list of dictionaries if content storage is enabled
            text = result.get("text", "No content available")
            source = result.get("id", "Unknown Source")
            score = result.get("score", 0.0)
            
            formatted_results.append(
                f"[{i}] Source File: {source} (Match Confidence: {score*100:.2f}%)\n"
                f"Content Passage:\n{text}\n"
                f"{'='*60}"
            )
            
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        return f"Error executing semantic search on server: {str(e)}"

if __name__ == "__main__":
    # Run the server using the default stdio transport protocol
    mcp.run()
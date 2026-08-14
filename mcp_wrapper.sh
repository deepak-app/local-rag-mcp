#!/bin/bash
# Wrapper script to run the Local Notes Search MCP server with the correct virtual environment.

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run python from the virtual environment
exec "${SCRIPT_DIR}/.venv/bin/python3" "${SCRIPT_DIR}/mcp_server.py" "$@"

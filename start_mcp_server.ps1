# Activate venv
.\venv\Scripts\activate

# Start the MCP server
uvicorn mcp_package.server:app --port 8000 --reload

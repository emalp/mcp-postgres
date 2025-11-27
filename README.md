## Database Debugger MCP Server

This project provides a minimal [Model Context Protocol](https://github.com/modelcontextprotocol) (MCP) server that exposes a single `run_sql` tool for running **read-only** SQL queries against a PostgreSQL database. It is intended to be registered inside an MCP-compatible client so you can inspect a database without risking write access.

### Requirements

- Python 3.10+
- `psycopg` (or any other PostgreSQL driver supported by psycopg 3)
- `mcp` (Model Context Protocol Python SDK)

Install the dependencies:

```bash
pip install psycopg[binary] mcp
```

### Configuration

Credentials are read **only** from environment variables:

- Prefer `DATABASE_URL` or `POSTGRES_URL` for a single connection string.
- Otherwise set the discrete `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` (and optional `PGSSLMODE`). All of these must be present if a URL is not provided.

### Running the server

```bash
export DATABASE_URL="postgres://readonly:secret@localhost:5432/your_db"
# or export each PG* variable instead
python debugger.py  # defaults to HTTP transport
```

Networking defaults:
- `MCP_HOST` (default `127.0.0.1`) controls which interface FastMCP binds to.
- `MCP_PORT` (default `8000`) controls the listening port.
- `MCP_TRANSPORT` (default `streamable-http`) selects the FastMCP transport if you don’t pass `--transport`.

The server starts FastMCP’s Streamable HTTP transport on `http://MCP_HOST:MCP_PORT/mcp`, which is what Cursor expects when configured with an HTTP MCP endpoint.

### Choosing the transport

For local development you can keep everything on stdio (no sockets involved):

```bash
python debugger.py --transport stdio
# or export MCP_TRANSPORT=stdio and run without the flag
```

When running over HTTP (the default), the server logs the exact URL (`http://MCP_HOST:MCP_PORT/mcp`) so MCP clients like Cursor can attach via `"transport": "http"`.

### Running via Docker

You can build and run the server as a container (useful for Cursor MCP integrations):

```bash
docker build -t database-debugger-mcp .
docker run --rm \
  -e MCP_HOST=0.0.0.0 \
  -e DATABASE_URL="postgres://readonly:secret@host:5432/your_db" \
  -p 8000:8000 \
  database-debugger-mcp
```

Cursor can then either:

1. Launch the container for you by pointing the MCP config to a small wrapper script (e.g., `docker run --rm ... database-debugger-mcp`), or
2. Connect to the exposed HTTP endpoint with `"transport": "http", "url": "http://127.0.0.1:8000/mcp"`.

### Available tools

- `run_sql(query: str) -> str`: Runs a single statement (e.g., `SELECT`, `SHOW`, `EXPLAIN`) and returns the rows as pretty-printed JSON.

### Read-only guarantees

1. The server rejects queries containing multiple statements.
2. Each PostgreSQL session is forced into `default_transaction_read_only = on` and `SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY`.
3. Any attempt to run mutating statements will raise an error and will not be executed.

### Troubleshooting

- Ensure the database user itself also has read-only privileges for defense-in-depth.
- Pass `--log-level DEBUG` for verbose logging.
- Use `--sslmode require` (or similar) if your deployment mandates TLS.


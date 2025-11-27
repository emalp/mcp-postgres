#!/usr/bin/env python3
"""
database_debugger_mcp.debugger
================================

Minimal Model Context Protocol (MCP) server that exposes database inspection
tools for PostgreSQL. Credentials are sourced exclusively from environment
variables (either `DATABASE_URL` / `POSTGRES_URL` or the discrete `PG*` vars),
and every session is forced into read-only mode.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import List, Optional

try:
    import psycopg  # noqa: F401  # pragma: no cover - ensure dependency present
except ImportError as exc:
    raise SystemExit(
        "psycopg is required to run this server. Install it with "
        "`pip install psycopg[binary]`."
    ) from exc

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - mcp should be installed
    raise SystemExit(
        "modelcontextprotocol is required. Install it with `pip install mcp`."
    ) from exc

from db_client import DatabaseCredentials, PostgresClient
from tools import register_database_tools

LOGGER = logging.getLogger(__name__)
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))
DEFAULT_TRANSPORT = os.getenv("MCP_TRANSPORT", "streamable-http")
server = FastMCP(
    name="database-debugger",
    host=MCP_HOST,
    port=MCP_PORT,
    streamable_http_path="/mcp",
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the PostgreSQL debugger MCP server (read-only). "
        "Credentials must be provided via env vars."
    )
    parser.add_argument(
        "--connect-timeout",
        type=int,
        default=int(os.getenv("PGCONNECT_TIMEOUT", "10")),
        help="Connection timeout in seconds (default: PGCONNECT_TIMEOUT or 10).",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level (DEBUG, INFO, WARNING, ERROR).",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default=DEFAULT_TRANSPORT,
        help="Transport to expose (stdio or streamable-http). "
        "Defaults to streamable-http or MCP_TRANSPORT env.",
    )
    return parser


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    configure_logging(args.log_level)

    try:
        credentials = DatabaseCredentials.from_env()
    except ValueError as exc:
        parser.error(str(exc))

    db_client = PostgresClient(credentials, connect_timeout=args.connect_timeout)
    register_database_tools(server, db_client)

    LOGGER.info(
        "Starting MCP server with PostgreSQL target %s:%s/%s (user=%s, sslmode=%s, read-only)",
        credentials.host,
        credentials.port,
        credentials.database,
        credentials.user or "<empty>",
        credentials.sslmode or "default",
    )
    LOGGER.info("Using MCP transport: %s", args.transport)
    if args.transport == "streamable-http":
        LOGGER.info("Streamable HTTP endpoint available at http://%s:%s/mcp", MCP_HOST, MCP_PORT)
    else:
        LOGGER.info("Running in stdio mode; awaiting client connection on stdin/stdout.")

    server.run(transport=args.transport)


if __name__ == "__main__":
    main(sys.argv[1:])


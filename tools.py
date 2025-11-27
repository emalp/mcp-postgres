"""
Tool registrations for the database debugger MCP server.
"""

from __future__ import annotations

import json

import psycopg
from mcp.server.fastmcp.server import FastMCP

from db_client import PostgresClient

def register_database_tools(server: FastMCP, client: PostgresClient) -> None:
    """
    Attach all database-related tools to the provided MCP server instance.
    """

    @server.tool(
        name="run_sql",
        description=(
            "Run a single read-only SQL statement (SELECT/SHOW/EXPLAIN/etc.) "
            "against the configured PostgreSQL database."
        ),
    )
    def run_sql_tool(query: str) -> str:
        """
        Execute a read-only SQL statement and return the resulting rows as JSON.
        """

        try:
            result = client.run_read_query(query)
        except psycopg.Error as exc:
            raise RuntimeError(f"PostgreSQL rejected the query: {exc.pgerror or exc.args[0]}") from exc

        return json.dumps(result, default=str, indent=2)

__all__ = ["register_database_tools"]


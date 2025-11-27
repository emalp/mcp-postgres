#!/usr/bin/env python3
"""
Shared PostgreSQL client utilities for the database debugger MCP server.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

import psycopg
from psycopg.rows import dict_row


@dataclass(frozen=True)
class DatabaseCredentials:
    """Connection details for a PostgreSQL instance."""

    host: str
    port: int
    database: str
    user: str
    password: str
    sslmode: Optional[str] = None

    @classmethod
    def from_url(cls, url: str) -> "DatabaseCredentials":
        parsed = urlparse(url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise ValueError(f"Unsupported URL scheme '{parsed.scheme}'.")
        database = parsed.path.lstrip("/")
        if not database:
            raise ValueError("Database name missing in URL.")

        query_params = parse_qs(parsed.query)
        sslmode = query_params.get("sslmode", [None])[0]

        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database=database,
            user=(parsed.username or ""),
            password=(parsed.password or ""),
            sslmode=sslmode,
        )

    @classmethod
    def from_env(cls) -> "DatabaseCredentials":
        url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
        if url:
            return cls.from_url(url)

        host = os.getenv("PGHOST")
        port = os.getenv("PGPORT")
        database = os.getenv("PGDATABASE")
        user = os.getenv("PGUSER")
        password = os.getenv("PGPASSWORD")
        sslmode = os.getenv("PGSSLMODE")

        required_fields = {
            "PGHOST": host,
            "PGPORT": port,
            "PGDATABASE": database,
            "PGUSER": user,
            "PGPASSWORD": password,
        }
        missing = [name for name, value in required_fields.items() if not value]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(
                f"Missing required PostgreSQL env vars: {joined}. "
                "Set DATABASE_URL/POSTGRES_URL or the discrete PG* variables."
            )

        return cls(
            host=host,
            port=int(port),  # type: ignore[arg-type]
            database=database,  # type: ignore[arg-type]
            user=user,  # type: ignore[arg-type]
            password=password,  # type: ignore[arg-type]
            sslmode=sslmode,
        )

    def connect_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "dbname": self.database,
            "user": self.user,
            "password": self.password,
        }
        if self.sslmode:
            kwargs["sslmode"] = self.sslmode
        return kwargs


class PostgresClient:
    """Lightweight helper for executing read-only queries."""

    def __init__(self, credentials: DatabaseCredentials, connect_timeout: int = 10) -> None:
        self._credentials = credentials
        self._connect_timeout = connect_timeout

    def _connect(self) -> psycopg.Connection:
        kwargs = self._credentials.connect_kwargs()
        kwargs["connect_timeout"] = self._connect_timeout
        conn = psycopg.connect(**kwargs)
        conn.execute("SET default_transaction_read_only = on;")
        conn.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")
        return conn

    def run_read_query(self, query: str) -> Dict[str, Any]:
        cleaned = query.strip()
        if not cleaned:
            raise ValueError("Query is empty.")

        cleaned = self._strip_trailing_semicolon(cleaned)
        if ";" in cleaned:
            raise ValueError("Only single read-only statements are allowed per call.")

        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(cleaned)
                results = cursor.fetchall()
                columns = [desc.name if hasattr(desc, "name") else desc[0] for desc in cursor.description]

        serialised_rows = [self._json_ready(dict(row)) for row in results]
        return {
            "columns": columns,
            "rows": serialised_rows,
            "row_count": len(serialised_rows),
        }

    @staticmethod
    def _strip_trailing_semicolon(statement: str) -> str:
        stripped = statement.rstrip()
        while stripped.endswith(";"):
            stripped = stripped[:-1].rstrip()
        return stripped

    @staticmethod
    def _json_ready(payload: Dict[str, Any]) -> Dict[str, Any]:
        def convert(value: Any) -> Any:
            if isinstance(value, (list, tuple)):
                return [convert(item) for item in value]
            if isinstance(value, dict):
                return {key: convert(val) for key, val in value.items()}
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")

            if value is None or isinstance(value, (int, float, str, bool)):
                return value

            return str(value)

        return {key: convert(val) for key, val in payload.items()}


__all__ = ["DatabaseCredentials", "PostgresClient"]


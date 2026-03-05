"""
DuckDB Connection Manager.

DuckDB is an embedded columnar database (like SQLite, but optimized for analytics).
Key constraint: DuckDB allows only ONE writer at a time within a process, but
multiple concurrent readers are fine (it uses MVCC - Multi-Version Concurrency Control).

This class wraps a single DuckDB connection and enforces the single-writer rule
using an asyncio.Lock. Without the lock, two concurrent FastAPI requests trying
to write (e.g., two batch event ingestions at the same time) would crash.

Trade-off: The asyncio.Lock serializes writes, meaning writes queue up. This is
fine for a local-only tool. At scale, you'd write to a buffer (like Kafka/Parquet files)
and bulk-load into DuckDB periodically.
"""

import asyncio
import duckdb
from pathlib import Path


class DuckDBManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # Create the data/ directory if it doesn't exist yet
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        # Open a persistent connection to the DuckDB file.
        # This single connection is shared across the entire FastAPI process.
        self._conn: duckdb.DuckDBPyConnection = duckdb.connect(db_path)
        # asyncio.Lock ensures only one coroutine writes at a time.
        # This is NOT a thread lock - it's cooperative async locking, which is
        # correct for FastAPI's async handlers running on a single event loop.
        self._write_lock = asyncio.Lock()

    def execute_write_sync(self, sql: str, params: list[tuple] | tuple | None = None):
        """
        Synchronous write - called directly during startup (schema init)
        and from within the async execute_write wrapper.

        Supports three calling patterns:
        - No params:     execute("CREATE TABLE ...")
        - Single tuple:  execute("DELETE ... WHERE id = ?", ("abc",))
        - List of tuples: executemany("INSERT ... VALUES (?, ?)", [(1, "a"), (2, "b")])
          executemany is DuckDB's batch insert - much faster than individual inserts
          because it sends all rows in a single operation.
        """
        if params is None:
            self._conn.execute(sql)
        elif isinstance(params, list):
            self._conn.executemany(sql, params)
        else:
            self._conn.execute(sql, params)

    async def execute_write(self, sql: str, params: list[tuple] | tuple | None = None):
        """
        Async write wrapper. Acquires the lock so only one write happens at a time.
        All route handlers that modify data (insert events, create orgs, save viz)
        go through this method.
        """
        async with self._write_lock:
            self.execute_write_sync(sql, params)

    def execute_read(self, sql: str, params: tuple | None = None) -> list[dict]:
        """
        Read operations use a cursor (lightweight read-only view).
        Multiple reads can happen concurrently thanks to DuckDB's MVCC -
        a reader sees a consistent snapshot even if a write is happening.

        Returns results as a list of dicts for easy JSON serialization:
        [{"event_name": "signup", "count": 42}, ...]
        """
        cursor = self._conn.cursor()
        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            # DDL statements (CREATE TABLE) return no description
            if cursor.description is None:
                return []
            # Build column names from cursor metadata, then zip with each row
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def close(self):
        self._conn.close()

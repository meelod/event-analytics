import asyncio
import duckdb
from pathlib import Path


class DuckDBManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: duckdb.DuckDBPyConnection = duckdb.connect(db_path)
        self._write_lock = asyncio.Lock()

    def execute_write_sync(self, sql: str, params: list[tuple] | tuple | None = None):
        """Synchronous write - use within async wrapper."""
        if params is None:
            self._conn.execute(sql)
        elif isinstance(params, list):
            self._conn.executemany(sql, params)
        else:
            self._conn.execute(sql, params)

    async def execute_write(self, sql: str, params: list[tuple] | tuple | None = None):
        """Serialize all writes through a single lock."""
        async with self._write_lock:
            self.execute_write_sync(sql, params)

    def execute_read(self, sql: str, params: tuple | None = None) -> list[dict]:
        """Create a cursor for read operations."""
        cursor = self._conn.cursor()
        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            if cursor.description is None:
                return []
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def close(self):
        self._conn.close()

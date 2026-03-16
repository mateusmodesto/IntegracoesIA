"""
Base DatabaseManager - Metodos compartilhados de conexao e query SQL Server.
Todos os modulos herdam desta classe e adicionam metodos especificos do dominio.
"""

import pyodbc
from typing import Dict, Any, List, Optional, Sequence, Union
from contextlib import contextmanager


class BaseDatabaseManager:

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection_string = self._build_connection_string()

    def _build_connection_string(self) -> str:
        return (
            f"DRIVER=ODBC Driver 17 for SQL Server;"
            f"SERVER={self.config['host']},{self.config.get('port', 1433)};"
            f"DATABASE={self.config['database']};"
            f"UID={self.config['user']};"
            f"PWD={self.config['password']};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
            "Trusted_Connection=no;"
        )

    @contextmanager
    def get_connection(self):
        connection = None
        try:
            connection = pyodbc.connect(self.connection_string)
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if connection:
                connection.close()

    def execute_query(self, query: str, params: Optional[Union[Sequence[Any], Dict[str, Any]]] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params is not None:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.rowcount
            except Exception as e:
                conn.rollback()
                raise e

    def execute_insert_returning_id(self, query: str, params=None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                inserted_id = cursor.fetchone()[0]
                conn.commit()
                return inserted_id
            except Exception as e:
                conn.rollback()
                raise e

    def fetch_one(self, query: str, params=None) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params is not None:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            columns = [column[0] for column in cursor.description] if cursor.description else []
            row = cursor.fetchone()

            if row:
                return dict(zip(columns, row))
            return None

    def fetch_all(self, query: str, params=None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params is not None:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            columns = [column[0] for column in cursor.description] if cursor.description else []
            rows = cursor.fetchall()

            return [dict(zip(columns, row)) for row in rows]

"""Database integration client for common database operations."""

import sqlite3
import pandas as pd
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path


class DatabaseClient:
    """Generic database client with support for SQLite and extensible for other DBs."""
    
    def __init__(self, db_type: str = "sqlite", **connection_params):
        """Initialize database client."""
        self.db_type = db_type.lower()
        self.connection_params = connection_params
        self.connection = None
        
        if self.db_type == "sqlite":
            self.db_path = connection_params.get("database", ":memory:")
            
    def connect(self) -> None:
        """Establish database connection."""
        if self.db_type == "sqlite":
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
        else:
            raise NotImplementedError(f"Database type {self.db_type} not yet implemented")
            
    def disconnect(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results."""
        if not self.connection:
            raise Exception("Database connection not established. Call connect() first.")
            
        cursor = self.connection.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        # Convert rows to dictionaries
        columns = [description[0] for description in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
            
        return results
        
    def execute_update(self, query: str, params: Optional[Tuple] = None) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows."""
        if not self.connection:
            raise Exception("Database connection not established. Call connect() first.")
            
        cursor = self.connection.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        self.connection.commit()
        return cursor.rowcount
        
    def execute_batch(self, query: str, param_list: List[Tuple]) -> int:
        """Execute batch query with multiple parameter sets."""
        if not self.connection:
            raise Exception("Database connection not established. Call connect() first.")
            
        cursor = self.connection.cursor()
        cursor.executemany(query, param_list)
        self.connection.commit()
        return cursor.rowcount
        
    def create_table(self, table_name: str, columns: Dict[str, str]) -> None:
        """Create a table with specified columns and types."""
        column_definitions = []
        for col_name, col_type in columns.items():
            column_definitions.append(f"{col_name} {col_type}")
            
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_definitions)})"
        self.execute_update(query)
        
    def drop_table(self, table_name: str) -> None:
        """Drop a table."""
        query = f"DROP TABLE IF EXISTS {table_name}"
        self.execute_update(query)
        
    def insert_data(self, table_name: str, data: Dict[str, Any]) -> int:
        """Insert single row of data."""
        columns = list(data.keys())
        placeholders = ['?' for _ in columns]
        values = list(data.values())
        
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        return self.execute_update(query, tuple(values))
        
    def insert_dataframe(self, table_name: str, df: pd.DataFrame, if_exists: str = 'append') -> None:
        """Insert DataFrame into table."""
        if not self.connection:
            raise Exception("Database connection not established. Call connect() first.")
            
        df.to_sql(table_name, self.connection, if_exists=if_exists, index=False)
        
    def query_to_dataframe(self, query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
        """Execute query and return results as DataFrame."""
        if not self.connection:
            raise Exception("Database connection not established. Call connect() first.")
            
        return pd.read_sql_query(query, self.connection, params=params)
        
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get information about table structure."""
        if self.db_type == "sqlite":
            query = f"PRAGMA table_info({table_name})"
            return self.execute_query(query)
        else:
            raise NotImplementedError(f"Table info not implemented for {self.db_type}")
            
    def list_tables(self) -> List[str]:
        """Get list of all tables in database."""
        if self.db_type == "sqlite":
            query = "SELECT name FROM sqlite_master WHERE type='table'"
            results = self.execute_query(query)
            return [row['name'] for row in results]
        else:
            raise NotImplementedError(f"List tables not implemented for {self.db_type}")
            
    def backup_database(self, backup_path: str) -> None:
        """Backup database to file."""
        if self.db_type == "sqlite":
            if not self.connection:
                raise Exception("Database connection not established. Call connect() first.")
                
            backup_conn = sqlite3.connect(backup_path)
            self.connection.backup(backup_conn)
            backup_conn.close()
        else:
            raise NotImplementedError(f"Backup not implemented for {self.db_type}")
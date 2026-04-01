"""
Database connection and query execution module
"""
import pyodbc
import pandas as pd
import logging
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from config import Config

class DatabaseManager:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self._pg_engine = None

    def get_connection(self, database='SPISA'):
        """Get database connection"""
        try:
            connection_string = self.config.CONNECTION_STRING.format(
                server=self.config.DB_SERVER,
                database=database,
                user=self.config.DB_USER,
                password=self.config.DB_PASSWORD
            )
            return pyodbc.connect(connection_string)
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise

    def execute_query(self, query, database='SPISA', params=None):
        """Execute query and return pandas DataFrame"""
        try:
            engine = self.get_sqlalchemy_engine(database)
            df = pd.read_sql(query, engine, params=params)
            return df
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            raise

    def get_sqlalchemy_engine(self, database='SPISA'):
        """Get SQLAlchemy engine - routes SPISA to PostgreSQL when configured"""
        try:
            # Route SPISA queries to PostgreSQL if configured
            if database == 'SPISA' and self.config.SPISA_PG_URL:
                if not self._pg_engine:
                    self._pg_engine = create_engine(self.config.SPISA_PG_URL)
                return self._pg_engine

            # Default: Azure SQL Server (used for xERP and SPISA fallback)
            connection_url = URL.create(
                "mssql+pyodbc",
                username=self.config.DB_USER,
                password=self.config.DB_PASSWORD,
                host=self.config.DB_SERVER,
                database=database,
                query={
                    "driver": "ODBC Driver 17 for SQL Server",
                    "Encrypt": "yes",
                    "TrustServerCertificate": "yes",
                    "Connection Timeout": "30"
                }
            )
            return create_engine(connection_url)
        except Exception as e:
            self.logger.error(f"SQLAlchemy engine creation failed: {e}")
            raise

    def execute_scalar(self, query, database='SPISA', params=None):
        """Execute query and return single value"""
        try:
            # Use PostgreSQL for SPISA if configured
            if database == 'SPISA' and self.config.SPISA_PG_URL:
                engine = self.get_sqlalchemy_engine(database)
                with engine.connect() as conn:
                    result = conn.execute(query, params or {})
                    row = result.fetchone()
                    return row[0] if row else None

            with self.get_connection(database) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or [])
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Scalar query execution failed: {e}")
            raise

    def test_connection(self):
        """Test database connectivity"""
        try:
            engine = self.get_sqlalchemy_engine('SPISA')
            with engine.connect() as conn:
                conn.execute("SELECT 1")
                return True
        except:
            return False

    def get_table_info(self, table_name, database='SPISA'):
        """Get table structure information"""
        if database == 'SPISA' and self.config.SPISA_PG_URL:
            query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = %(table)s
            ORDER BY ordinal_position
            """
            return self.execute_query(query, database, {'table': table_name})

        query = """
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
        """
        return self.execute_query(query, database, [table_name])

"""
Database connection and query execution module
"""
import pandas as pd
import logging
import time
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from config import Config
from database.readonly import url_pg

XERP_TIMEOUT_S = 5       # calidad and the MCP brief ask; a dead server must not hang them
XERP_CACHE_S = 60


class XerpNoConfigurado(RuntimeError):
    """DB_USER / DB_PASSWORD are not set: there is no Azure SQL Server to talk to."""


class DatabaseManager:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self._pg_engine = None
        self._xerp = (0.0, None)   # (when, status) of the last xerp_estado() probe

    def _require_azure(self, database):
        if not self.config.XERP_CONFIGURED:
            raise XerpNoConfigurado(f"Azure SQL ({database}) no configurado: faltan DB_USER/DB_PASSWORD")

    def xerp_estado(self):
        """"ok" | "no responde" | "no configurado" for the Azure SQL Server (xERP), probed with a short timeout and
        remembered for a minute."""
        if not self.config.XERP_CONFIGURED:
            return "no configurado"
        cuando, estado = self._xerp
        if estado and time.monotonic() - cuando < XERP_CACHE_S:
            return estado
        try:
            import pyodbc
            cadena = self.config.CONNECTION_STRING.format(
                server=self.config.DB_SERVER, database=self.config.XERP_DB,
                user=self.config.DB_USER, password=self.config.DB_PASSWORD
            ).replace('Connection Timeout=30;', f'Connection Timeout={XERP_TIMEOUT_S};')
            # timeout= in connect() only bounds the login; conn.timeout bounds each query (pyodbc: 0 = none)
            with pyodbc.connect(cadena, timeout=XERP_TIMEOUT_S) as conn:
                conn.timeout = XERP_TIMEOUT_S
                conn.cursor().execute("SELECT 1").fetchone()
            estado = "ok"
        except Exception as e:
            self.logger.warning(f"xERP no responde: {type(e).__name__}")
            estado = "no responde"
        self._xerp = (time.monotonic(), estado)
        return estado

    def get_connection(self, database='SPISA'):
        """Get database connection"""
        self._require_azure(database)
        try:
            import pyodbc
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
                    self._pg_engine = create_engine(url_pg(self.config.SPISA_PG_URL))
                return self._pg_engine

            # Default: Azure SQL Server (used for xERP and SPISA fallback)
            self._require_azure(database)
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

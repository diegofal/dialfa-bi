"""
Configuration settings for Dialfa Analytics Dashboard
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database Configuration
    DB_SERVER = 'dialfa.database.windows.net'
    DB_USER = 'fp'
    DB_PASSWORD = 'Ab1234,,,'
    SPISA_DB = 'SPISA'
    XERP_DB = 'xERP'
    
    # Connection string template - working configuration
    CONNECTION_STRING = (
        'DRIVER={{ODBC Driver 17 for SQL Server}};'
        'SERVER={server};'
        'DATABASE={database};'
        'UID={user};'
        'PWD={password};'
        'Encrypt=yes;'
        'TrustServerCertificate=yes;'
        'Connection Timeout=30;'
    )
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dialfa-analytics-2025'
    DEBUG = True
    
    # Analytics Configuration
    CACHE_TIMEOUT = 300  # 5 minutes
    MAX_RECORDS = 10000
    EXPORT_PATH = 'exports/'
    
    # Chart Configuration
    CHART_COLORS = {
        'primary': '#033663',
        'success': '#28a745',
        'warning': '#ffc107',
        'danger': '#dc3545',
        'info': '#17a2b8'
    }
    
    # Business Rules
    HIGH_RISK_THRESHOLD = 0.5  # 50% overdue
    MEDIUM_RISK_THRESHOLD = 0.2  # 20% overdue
    SLOW_MOVING_DAYS = 180  # Days without sales
    DEAD_STOCK_DAYS = 365  # Days without sales
    
    # Currency and Tax Configuration
    DEFAULT_CURRENCY = 'ARS'  # Argentine Pesos
    TAX_RATE = 0.21  # 21% IVA (Value Added Tax)
    CURRENCY_SYMBOL = 'ARS'  # Show currency code explicitly
    
    # Internationalization Configuration
    LANGUAGES = {
        'en': 'English',
        'es': 'Español'
    }
    BABEL_DEFAULT_LOCALE = 'es'
    BABEL_DEFAULT_TIMEZONE = 'UTC'

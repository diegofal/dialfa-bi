"""
Cache Configuration for Dialfa Analytics
Supports SimpleCache (memory) and Redis backends
"""
import os
from flask_caching import Cache

# Cache configuration - easily switch between backends
CACHE_CONFIG = {
    # Development: SimpleCache (in-memory)
    'simple': {
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutes default
    },
    
    # Production: Redis (when ready)
    'redis': {
        'CACHE_TYPE': 'RedisCache',
        'CACHE_REDIS_HOST': os.getenv('REDIS_HOST', 'localhost'),
        'CACHE_REDIS_PORT': int(os.getenv('REDIS_PORT', 6379)),
        'CACHE_REDIS_DB': int(os.getenv('REDIS_DB', 0)),
        'CACHE_REDIS_PASSWORD': os.getenv('REDIS_PASSWORD', None),
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_KEY_PREFIX': 'dialfa_'
    },
    
    # Filesystem cache (alternative to Redis)
    'filesystem': {
        'CACHE_TYPE': 'FileSystemCache',
        'CACHE_DIR': 'cache',
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_THRESHOLD': 500
    }
}

# Select cache backend from environment or default to simple
CACHE_BACKEND = os.getenv('CACHE_BACKEND', 'simple')
cache_config = CACHE_CONFIG.get(CACHE_BACKEND, CACHE_CONFIG['simple'])

# Cache timeout configurations by data type (in seconds)
CACHE_TIMEOUTS = {
    # Heavy queries - longer cache
    'credit_risk': 600,          # 10 minutes - changes slowly
    'executive_summary': 300,     # 5 minutes - moderate changes
    'monthly_trends': 1800,       # 30 minutes - historical data
    'customer_segmentation': 900, # 15 minutes - changes slowly
    'stock_alerts': 600,          # 10 minutes
    'aging_analysis': 900,        # 15 minutes
    'category_analysis': 1200,    # 20 minutes
    'abc_analysis': 1800,         # 30 minutes
    'inventory_kpis': 600,        # 10 minutes
    
    # Medium queries
    'dashboard_overview': 300,    # 5 minutes
    'dashboard_charts': 300,      # 5 minutes
    'top_customers': 600,         # 10 minutes
    'cash_flow': 900,             # 15 minutes
    
    # Lighter queries or more dynamic
    'dashboard_alerts': 120,      # 2 minutes - should be relatively fresh
    'billing_monthly': 600,       # 10 minutes
    'collected_monthly': 600,     # 10 minutes
    
    # Real-time - short cache just to prevent spam
    'billing_today': 60,          # 1 minute - changes frequently
    'health_check': 30,           # 30 seconds
}

def get_cache_timeout(cache_key):
    """Get cache timeout for a specific key"""
    return CACHE_TIMEOUTS.get(cache_key, 300)  # Default 5 minutes


def make_cache_key(*args, **kwargs):
    """
    Generate cache key including user role for role-specific caching
    Useful if admin sees different data than regular users
    """
    from flask_login import current_user
    
    # Include user role in cache key if authenticated
    role = 'guest'
    if current_user.is_authenticated:
        role = current_user.role
    
    # Create key from function name and arguments
    path = kwargs.get('request_path', 'default')
    key = f"{role}:{path}"
    
    return key


# Initialize cache instance (to be configured in app factory)
cache = Cache()


def init_cache(app):
    """Initialize cache with Flask app"""
    app.config.update(cache_config)
    cache.init_app(app)
    
    app.logger.info(f"Cache initialized with backend: {CACHE_BACKEND}")
    app.logger.info(f"Cache config: {cache_config['CACHE_TYPE']}")
    
    return cache


"""
Cache Configuration for Dialfa Analytics
Supports SimpleCache (memory) and Redis backends
"""
import os
from flask_caching import Cache

# Auto-detect Redis from Railway REDIS_URL or REDIS_PRIVATE_URL
REDIS_URL = os.getenv('REDIS_URL') or os.getenv('REDIS_PRIVATE_URL')

# Cache configuration - easily switch between backends
CACHE_CONFIG = {
    # Development: SimpleCache (in-memory)
    'simple': {
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutes default
    },
    
    # Production: Redis (Railway provides REDIS_URL automatically)
    'redis': {
        'CACHE_TYPE': 'RedisCache',
        'CACHE_REDIS_URL': REDIS_URL,  # Railway format: redis://host:port
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_KEY_PREFIX': 'dialfa_',
        'CACHE_OPTIONS': {
            'socket_connect_timeout': 5,
            'socket_timeout': 5,
            'retry_on_timeout': True
        }
    },
    
    # Filesystem cache (alternative to Redis)
    'filesystem': {
        'CACHE_TYPE': 'FileSystemCache',
        'CACHE_DIR': 'cache',
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_THRESHOLD': 500
    }
}

# Auto-select cache backend:
# - If REDIS_URL exists (Railway), use Redis
# - Otherwise use CACHE_BACKEND env var or default to simple
if REDIS_URL:
    CACHE_BACKEND = 'redis'
    # Use logging instead of print to avoid Windows encoding issues
    import logging
    logging.info(f"[CACHE] Redis URL detected, using Redis cache: {REDIS_URL[:20]}...")
else:
    CACHE_BACKEND = os.getenv('CACHE_BACKEND', 'simple')
    import logging
    logging.info(f"[CACHE] No Redis URL found, using {CACHE_BACKEND} cache")

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
    'stock_value_evolution': 3600, # 60 minutes - stock snapshots daily
    'out_of_stock_analysis': 300,  # 5 minutes - changes frequently, critical for operations
    'reorder_analysis': 600,       # 10 minutes - reorder calculations
    'supplier_performance': 1800,  # 30 minutes - supplier metrics
    
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


# ==========================================
# REORDER POINT CONFIGURATION
# ==========================================
REORDER_CONFIG = {
    # Lead time: Production (90 days) + Shipping (45 days) = 135 days total
    'lead_time_days': 135,
    
    # Service levels by ABC classification (Z-score for safety stock)
    'service_levels': {
        'A': 1.65,  # 95% service level - Critical/high rotation products
        'B': 1.28,  # 90% service level - Medium rotation products  
        'C': 0.84,  # 80% service level - Low rotation products
    },
    
    # Coverage multipliers (how many lead times to cover)
    'coverage_multipliers': {
        'A': 2.0,   # 2x lead time coverage for A products (270 days stock)
        'B': 1.5,   # 1.5x lead time coverage for B products (202 days stock)
        'C': 1.2,   # 1.2x lead time coverage for C products (162 days stock)
    },
    
    # ABC Classification thresholds (cumulative revenue %)
    'abc_thresholds': {
        'A': 80,  # Top products contributing 80% of revenue
        'B': 95,  # Next products contributing to 95% of revenue
        'C': 100, # Remaining products
    },
    
    # Demand calculation window
    'demand_window_days': 90,  # Use last 90 days to calculate average demand
    
    # Priority thresholds (days of coverage remaining)
    'priority_thresholds': {
        'critical': 30,   # Less than 30 days coverage
        'urgent': 60,     # Less than 60 days coverage  
        'high': 90,       # Less than 90 days coverage
        'medium': 135,    # Less than lead time (135 days)
    },
    
    # Minimum order quantity
    'min_order_quantity': 1,
}

def get_reorder_config(key=None):
    """Get reorder configuration value"""
    if key:
        return REORDER_CONFIG.get(key)
    return REORDER_CONFIG


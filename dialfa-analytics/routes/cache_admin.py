"""
Cache Administration Routes
Endpoints for cache management (admin only)
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from auth.decorators import admin_required
from cache_config import cache
import logging

cache_admin_bp = Blueprint('cache_admin', __name__)
logger = logging.getLogger(__name__)


@cache_admin_bp.route('/api/admin/cache/clear', methods=['POST'])
@login_required
@admin_required
def clear_all_cache():
    """Clear all cache (admin only)"""
    try:
        cache.clear()
        logger.info("All cache cleared by admin")
        return jsonify({
            'status': 'success',
            'message': 'All cache cleared successfully'
        })
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@cache_admin_bp.route('/api/admin/cache/clear/<cache_type>', methods=['POST'])
@login_required
@admin_required
def clear_specific_cache(cache_type):
    """
    Clear specific cache by type (admin only)
    
    Types: financial, inventory, sales, dashboard
    """
    try:
        cache_prefixes = {
            'financial': ['financial_'],
            'inventory': ['inventory_'],
            'sales': ['sales_'],
            'dashboard': ['dashboard_']
        }
        
        if cache_type not in cache_prefixes:
            return jsonify({
                'status': 'error',
                'message': f'Invalid cache type. Valid types: {list(cache_prefixes.keys())}'
            }), 400
        
        # Clear cache by prefix (note: SimpleCache doesn't support selective clearing)
        # This is a limitation - with Redis we could use key patterns
        cache.clear()  # For now, clear all
        
        logger.info(f"Cache cleared for type: {cache_type}")
        return jsonify({
            'status': 'success',
            'message': f'Cache for {cache_type} cleared successfully',
            'note': 'Using SimpleCache - all cache cleared. Upgrade to Redis for selective clearing.'
        })
    except Exception as e:
        logger.error(f"Error clearing {cache_type} cache: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@cache_admin_bp.route('/api/admin/cache/stats', methods=['GET'])
@login_required
@admin_required
def cache_stats():
    """
    Get cache statistics (admin only)
    
    Note: SimpleCache has limited stats. Redis provides better monitoring.
    """
    try:
        # Get cache config
        config = cache.config
        
        stats = {
            'backend': config.get('CACHE_TYPE', 'Unknown'),
            'default_timeout': config.get('CACHE_DEFAULT_TIMEOUT', 0),
            'note': 'For detailed stats, upgrade to Redis backend'
        }
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@cache_admin_bp.route('/api/admin/cache/test', methods=['GET'])
@login_required
@admin_required
def test_cache():
    """
    Test cache functionality (admin only)
    """
    try:
        import time
        
        # Test cache set/get
        test_key = 'cache_test_key'
        test_value = {'timestamp': time.time(), 'message': 'Cache is working'}
        
        cache.set(test_key, test_value, timeout=60)
        retrieved_value = cache.get(test_key)
        
        if retrieved_value:
            return jsonify({
                'status': 'success',
                'message': 'Cache is working correctly',
                'test_data': retrieved_value
            })
        else:
            return jsonify({
                'status': 'warning',
                'message': 'Cache set but retrieval failed'
            }), 500
    except Exception as e:
        logger.error(f"Error testing cache: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


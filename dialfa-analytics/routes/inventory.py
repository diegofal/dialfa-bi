"""
Inventory Routes
Inventory analysis API endpoints
"""
from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required
import logging

inventory_bp = Blueprint('inventory', __name__)
logger = logging.getLogger(__name__)

# Protect all routes in this blueprint
@inventory_bp.before_request
@login_required
def require_login():
    """Require login for all inventory routes"""
    pass

@inventory_bp.route('/')
def inventory_dashboard():
    """Inventory dashboard page"""
    return render_template('inventory/dashboard.html')

@inventory_bp.route('/api/summary')
def inventory_summary():
    """Get inventory summary"""
    try:
        summary = current_app.inventory_analytics.get_summary()
        return jsonify({
            'data': summary,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Inventory summary error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@inventory_bp.route('/api/top-stock-value')
def top_stock_value():
    """Get products with highest stock value"""
    try:
        limit = request.args.get('limit', 10, type=int)
        top_stock = current_app.inventory_analytics.get_top_stock_value(limit)
        return jsonify({
            'data': top_stock,
            'total_records': len(top_stock),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Top stock value error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@inventory_bp.route('/api/slow-moving')
def slow_moving_analysis():
    """Get slow-moving stock analysis"""
    try:
        slow_moving = current_app.inventory_analytics.get_slow_moving_analysis()
        return jsonify({
            'data': slow_moving,
            'total_records': len(slow_moving),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Slow moving analysis error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@inventory_bp.route('/api/category-analysis')
def category_analysis():
    """Get inventory analysis by category"""
    try:
        categories = current_app.inventory_analytics.get_category_analysis()
        return jsonify({
            'data': categories,
            'total_records': len(categories),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Category analysis error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@inventory_bp.route('/api/reorder-recommendations')
def reorder_recommendations():
    """Get reorder recommendations"""
    try:
        recommendations = current_app.inventory_analytics.get_reorder_recommendations()
        return jsonify({
            'data': recommendations,
            'total_records': len(recommendations),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Reorder recommendations error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@inventory_bp.route('/api/abc-analysis')
def abc_analysis():
    """Get ABC analysis"""
    try:
        abc_data = current_app.inventory_analytics.get_abc_analysis()
        return jsonify({
            'data': abc_data,
            'total_records': len(abc_data),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"ABC analysis error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@inventory_bp.route('/api/stock-alerts')
def stock_alerts():
    """Get stock level alerts"""
    try:
        alerts = current_app.inventory_analytics.get_stock_alerts()
        return jsonify({
            'data': alerts,
            'total_records': len(alerts),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Stock alerts error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@inventory_bp.route('/api/kpis')
def inventory_kpis():
    """Get inventory KPIs"""
    try:
        kpis = current_app.inventory_analytics.get_inventory_kpis()
        return jsonify({
            'data': kpis,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Inventory KPIs error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@inventory_bp.route('/api/stock-variation-over-time')
def stock_variation_over_time():
    """Get detailed stock variation analysis over time"""
    try:
        variation_data = current_app.inventory_analytics.get_stock_variation_over_time()
        return jsonify({
            'data': variation_data,
            'total_records': len(variation_data),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Stock variation over time error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@inventory_bp.route('/api/stock-velocity-summary')
def stock_velocity_summary():
    """Get comprehensive stock velocity and turnover analysis"""
    try:
        velocity_data = current_app.inventory_analytics.get_stock_velocity_summary()
        return jsonify({
            'data': velocity_data,
            'total_records': len(velocity_data),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Stock velocity summary error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@inventory_bp.route('/api/stock-variation-kpis')
def stock_variation_kpis():
    """Get key performance indicators from stock variation analysis"""
    try:
        kpis = current_app.inventory_analytics.get_stock_variation_kpis()
        return jsonify({
            'data': kpis,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Stock variation KPIs error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@inventory_bp.route('/api/stock-value-evolution')
def stock_value_evolution():
    """Get historical stock value evolution"""
    try:
        months = request.args.get('months', 12, type=int)
        evolution_data = current_app.inventory_analytics.get_stock_value_evolution(months)
        return jsonify({
            'data': evolution_data,
            'total_records': len(evolution_data),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Stock value evolution error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

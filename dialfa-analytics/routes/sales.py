"""
Sales Routes
Sales analysis API endpoints
"""
from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required
import logging

sales_bp = Blueprint('sales', __name__)
logger = logging.getLogger(__name__)

# Protect all routes in this blueprint
@sales_bp.before_request
@login_required
def require_login():
    """Require login for all sales routes"""
    pass

@sales_bp.route('/')
def sales_dashboard():
    """Sales dashboard page"""
    return render_template('sales/dashboard.html')

@sales_bp.route('/api/summary')
def sales_summary():
    """Get sales summary"""
    try:
        summary = current_app.sales_analytics.get_summary()
        return jsonify({
            'data': summary,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Sales summary error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@sales_bp.route('/api/monthly-trends')
def monthly_trends():
    """Get monthly sales trends"""
    try:
        trends = current_app.sales_analytics.get_monthly_trends()
        return jsonify({
            'data': trends,
            'total_records': len(trends),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Monthly trends error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@sales_bp.route('/api/performance-by-period')
def performance_by_period():
    """Get sales performance by period"""
    try:
        period = request.args.get('period', 'month')  # month, quarter, year
        performance = current_app.sales_analytics.get_sales_performance_by_period(period)
        return jsonify({
            'data': performance,
            'total_records': len(performance),
            'period': period,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Performance by period error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@sales_bp.route('/api/customer-segmentation')
def customer_segmentation():
    """Get customer segmentation analysis"""
    try:
        segmentation = current_app.sales_analytics.get_customer_segmentation()
        return jsonify({
            'data': segmentation,
            'total_records': len(segmentation),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Customer segmentation error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@sales_bp.route('/api/product-performance')
def product_performance():
    """Get product sales performance"""
    try:
        performance = current_app.sales_analytics.get_product_performance()
        return jsonify({
            'data': performance,
            'total_records': len(performance),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Product performance error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@sales_bp.route('/api/seasonal-analysis')
def seasonal_analysis():
    """Get seasonal sales analysis"""
    try:
        seasonal = current_app.sales_analytics.get_seasonal_analysis()
        return jsonify({
            'data': seasonal,
            'total_records': len(seasonal),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Seasonal analysis error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@sales_bp.route('/api/xerp-top-customers')
def xerp_top_customers():
    """Get top customers from xERP system"""
    try:
        limit = request.args.get('limit', 10, type=int)
        customers = current_app.sales_analytics.get_xerp_top_customers(limit)
        return jsonify({
            'data': customers,
            'total_records': len(customers),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"xERP top customers error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@sales_bp.route('/api/forecast')
def sales_forecast():
    """Get sales forecast"""
    try:
        months_ahead = request.args.get('months', 6, type=int)
        forecast = current_app.sales_analytics.get_sales_forecast(months_ahead)
        return jsonify({
            'data': forecast,
            'total_records': len(forecast),
            'months_ahead': months_ahead,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Sales forecast error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@sales_bp.route('/api/kpis')
def sales_kpis():
    """Get sales KPIs"""
    try:
        kpis = current_app.sales_analytics.get_sales_kpis()
        return jsonify({
            'data': kpis,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Sales KPIs error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

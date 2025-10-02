"""
Purchase Order Routes
Reorder analysis and supplier management endpoints
"""
from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required
import logging

purchase_bp = Blueprint('purchase', __name__)
logger = logging.getLogger(__name__)

# Protect all routes in this blueprint
@purchase_bp.before_request
@login_required
def require_login():
    """Require login for all purchase routes"""
    pass

@purchase_bp.route('/')
def purchase_dashboard():
    """Purchase orders dashboard page"""
    return render_template('purchase/dashboard.html')

@purchase_bp.route('/api/reorder-analysis')
def reorder_analysis():
    """Get detailed reorder analysis"""
    try:
        analysis_data = current_app.purchase_analytics.get_reorder_analysis()
        summary = current_app.purchase_analytics.get_reorder_summary()
        
        return jsonify({
            'data': analysis_data,
            'summary': summary,
            'total_records': len(analysis_data),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Reorder analysis error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@purchase_bp.route('/api/reorder-summary')
def reorder_summary():
    """Get reorder summary KPIs"""
    try:
        summary = current_app.purchase_analytics.get_reorder_summary()
        return jsonify({
            'data': summary,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Reorder summary error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@purchase_bp.route('/api/supplier-performance')
def supplier_performance():
    """Get supplier performance metrics"""
    try:
        suppliers = current_app.purchase_analytics.get_supplier_performance()
        return jsonify({
            'data': suppliers,
            'total_records': len(suppliers),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Supplier performance error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500


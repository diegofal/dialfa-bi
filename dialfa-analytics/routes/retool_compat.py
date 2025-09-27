"""
Retool Compatibility Routes
API endpoints that exactly match the original Retool dashboard queries
"""
from flask import Blueprint, jsonify, request, current_app
import logging

retool_bp = Blueprint('retool', __name__, url_prefix='/api/retool')
logger = logging.getLogger(__name__)

# SPISA Routes - Exact Retool Compatibility
@retool_bp.route('/spisa/balances')
def spisa_balances():
    """SPISA_Balances - Exact match to Retool query"""
    try:
        data = current_app.financial_analytics.get_spisa_balances()
        return jsonify({
            'data': data,
            'status': 'success',
            'query_name': 'SPISA_Balances'
        })
    except Exception as e:
        logger.error(f"SPISA balances error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@retool_bp.route('/spisa/future-payments')
def spisa_future_payments():
    """SPISA_FuturePayments - Exact match to Retool query"""
    try:
        data = current_app.financial_analytics.get_spisa_future_payments()
        return jsonify({
            'data': [data],  # Retool expects array format
            'status': 'success',
            'query_name': 'SPISA_FuturePayments'
        })
    except Exception as e:
        logger.error(f"SPISA future payments error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@retool_bp.route('/spisa/due-balance')
def spisa_due_balance():
    """SPISA_DueBalance - Exact match to Retool query"""
    try:
        data = current_app.financial_analytics.get_spisa_due_balance()
        return jsonify({
            'data': [data],  # Retool expects array format
            'status': 'success',
            'query_name': 'SPISA_DueBalance'
        })
    except Exception as e:
        logger.error(f"SPISA due balance error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@retool_bp.route('/spisa/billed-monthly')
def spisa_billed_monthly():
    """SPISA_BilledMonthly - Exact match to Retool query"""
    try:
        data = current_app.financial_analytics.get_spisa_billed_monthly()
        return jsonify({
            'data': [data],  # Retool expects array format
            'status': 'success',
            'query_name': 'SPISA_BilledMonthly'
        })
    except Exception as e:
        logger.error(f"SPISA billed monthly error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@retool_bp.route('/spisa/billed-today')
def spisa_billed_today():
    """SPISA_BilledToday - Exact match to Retool query"""
    try:
        data = current_app.financial_analytics.get_spisa_billed_today()
        return jsonify({
            'data': [data],  # Retool expects array format
            'status': 'success',
            'query_name': 'SPISA_BilledToday'
        })
    except Exception as e:
        logger.error(f"SPISA billed today error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

# xERP Routes - Exact Retool Compatibility
@retool_bp.route('/xerp/billed-monthly')
def xerp_billed_monthly():
    """xERP_BilledMonthly - Exact match to Retool query"""
    try:
        data = current_app.sales_analytics.get_xerp_billed_monthly()
        return jsonify({
            'data': [data],  # Retool expects array format
            'status': 'success',
            'query_name': 'xERP_BilledMonthly'
        })
    except Exception as e:
        logger.error(f"xERP billed monthly error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@retool_bp.route('/xerp/billed-today')
def xerp_billed_today():
    """xERP_BilledToday - Exact match to Retool query"""
    try:
        data = current_app.sales_analytics.get_xerp_billed_today()
        return jsonify({
            'data': [data],  # Retool expects array format
            'status': 'success',
            'query_name': 'xERP_BilledToday'
        })
    except Exception as e:
        logger.error(f"xERP billed today error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@retool_bp.route('/xerp/bills')
def xerp_bills():
    """xERP_Bills - Exact match to Retool query"""
    try:
        view_filter = request.args.get('view', 'month')  # 'month' or 'day'
        data = current_app.sales_analytics.get_xerp_bills(view_filter)
        return jsonify({
            'data': data,
            'status': 'success',
            'query_name': 'xERP_Bills',
            'view_filter': view_filter
        })
    except Exception as e:
        logger.error(f"xERP bills error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@retool_bp.route('/xerp/bills-history')
def xerp_bills_history():
    """xERP_BillsHistory - Monthly sales trend (already implemented)"""
    try:
        data = current_app.sales_analytics.get_monthly_trends()
        return jsonify({
            'data': data,
            'status': 'success',
            'query_name': 'xERP_BillsHistory'
        })
    except Exception as e:
        logger.error(f"xERP bills history error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

# Summary endpoint for all Retool queries
@retool_bp.route('/summary')
def retool_summary():
    """Summary of all Retool-compatible queries"""
    try:
        summary = {
            'spisa_queries': [
                'SPISA_Balances',
                'SPISA_FuturePayments', 
                'SPISA_DueBalance',
                'SPISA_BilledMonthly',
                'SPISA_BilledToday'
            ],
            'xerp_queries': [
                'xERP_BilledMonthly',
                'xERP_BilledToday',
                'xERP_Bills',
                'xERP_BillsHistory'
            ],
            'total_queries': 9,
            'compatibility': '100% - All Retool queries implemented'
        }
        return jsonify({
            'data': summary,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Retool summary error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500


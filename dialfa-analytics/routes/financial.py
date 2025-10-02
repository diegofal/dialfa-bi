"""
Financial Routes
Financial analysis API endpoints
"""
from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required
import logging

financial_bp = Blueprint('financial', __name__)
logger = logging.getLogger(__name__)

# Protect all routes in this blueprint
@financial_bp.before_request
@login_required
def require_login():
    """Require login for all financial routes"""
    pass

@financial_bp.route('/')
def financial_dashboard():
    """Financial dashboard page"""
    return render_template('financial/dashboard.html')

@financial_bp.route('/api/executive-summary')
def executive_summary():
    """Get executive financial summary"""
    try:
        summary = current_app.financial_analytics.get_executive_summary()
        return jsonify({
            'data': summary,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Executive summary error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@financial_bp.route('/api/credit-risk')
def credit_risk():
    """Get credit risk analysis"""
    try:
        risk_analysis = current_app.financial_analytics.get_credit_risk_analysis()
        return jsonify({
            'data': risk_analysis,
            'total_records': len(risk_analysis),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Credit risk error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@financial_bp.route('/api/cash-flow-history')
def cash_flow_history():
    """Get historical cash flow data"""
    try:
        months = request.args.get('months', 12, type=int)
        cash_flow_data = current_app.financial_analytics.get_cash_flow_history(months)
        return jsonify({
            'data': cash_flow_data,
            'total_records': len(cash_flow_data),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Cash flow history error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@financial_bp.route('/api/cash-flow-forecast')
def cash_flow_forecast():
    """Get cash flow forecast with predictions"""
    try:
        forecast_months = request.args.get('months', 6, type=int)
        forecast_data = current_app.financial_analytics.get_cash_flow_forecast(forecast_months)
        return jsonify({
            'data': forecast_data,
            'total_records': len(forecast_data),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Cash flow forecast error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@financial_bp.route('/api/billing-monthly')
def billing_monthly():
    """Get monthly billing from xERP"""
    try:
        data = current_app.sales_analytics.get_xerp_billed_monthly()
        return jsonify({
            'data': data,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Monthly billing error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@financial_bp.route('/api/billing-today')
def billing_today():
    """Get today's billing from xERP"""
    try:
        data = current_app.sales_analytics.get_xerp_billed_today()
        return jsonify({
            'data': data,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Today billing error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@financial_bp.route('/api/collected-monthly')
def collected_monthly():
    """Get monthly collections from SPISA"""
    try:
        data = current_app.financial_analytics.get_spisa_collected_monthly()
        return jsonify({
            'data': data,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Monthly collections error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@financial_bp.route('/api/top-customers')
def top_customers():
    """Get top customers by balance"""
    try:
        limit = request.args.get('limit', 10, type=int)
        customers = current_app.financial_analytics.get_top_customers(limit)
        return jsonify({
            'data': customers,
            'total_records': len(customers),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Top customers error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@financial_bp.route('/api/customer-profitability')
def customer_profitability():
    """Get customer profitability analysis"""
    try:
        profitability = current_app.financial_analytics.get_customer_profitability()
        return jsonify({
            'data': profitability,
            'total_records': len(profitability),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Customer profitability error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@financial_bp.route('/api/aging-analysis')
def aging_analysis():
    """Get accounts receivable aging analysis"""
    try:
        aging = current_app.financial_analytics.get_aging_analysis()
        return jsonify({
            'data': aging,
            'total_records': len(aging),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Aging analysis error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@financial_bp.route('/api/payment-trends')
def payment_trends():
    """Get payment trends analysis"""
    try:
        trends = current_app.financial_analytics.get_payment_trends()
        return jsonify({
            'data': trends,
            'total_records': len(trends),
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Payment trends error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@financial_bp.route('/api/kpis')
def financial_kpis():
    """Get financial KPIs"""
    try:
        kpis = current_app.financial_analytics.get_financial_kpis()
        return jsonify({
            'data': kpis,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Financial KPIs error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@financial_bp.route('/api/expected-collections')
def expected_collections():
    """Get expected collections based on invoice aging"""
    try:
        collections = current_app.financial_analytics.get_expected_collections()
        return jsonify({
            'data': collections,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Expected collections error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@financial_bp.route('/api/collection-performance')
def collection_performance():
    """Get collection performance metrics (DSO, on-time %)"""
    try:
        performance = current_app.financial_analytics.get_collection_performance()
        return jsonify({
            'data': performance,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Collection performance error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

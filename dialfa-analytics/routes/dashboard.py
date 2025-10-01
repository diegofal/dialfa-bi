"""
Dashboard Routes
Main dashboard API endpoints
"""
from flask import Blueprint, render_template, jsonify, current_app
from flask_login import login_required
import logging

dashboard_bp = Blueprint('dashboard', __name__)
logger = logging.getLogger(__name__)

@dashboard_bp.route('/api/dashboard/overview')
@login_required
def dashboard_overview():
    """Get dashboard overview data"""
    try:
        # Get financial summary
        financial_summary = current_app.financial_analytics.get_executive_summary()
        
        # Get inventory summary
        inventory_summary = current_app.inventory_analytics.get_summary()
        
        # Get sales summary
        sales_summary = current_app.sales_analytics.get_summary()
        
        return jsonify({
            'financial': financial_summary,
            'inventory': inventory_summary,
            'sales': sales_summary,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Dashboard overview error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@dashboard_bp.route('/api/dashboard/charts')
@login_required
def dashboard_charts():
    """Get chart data for dashboard"""
    try:
        # Cash flow chart
        cash_flow = current_app.financial_analytics.get_cash_flow_forecast()
        
        # Top customers chart
        top_customers = current_app.financial_analytics.get_top_customers(5)
        
        # Monthly sales trend
        sales_trend = current_app.sales_analytics.get_monthly_trends()
        
        # Category analysis
        category_analysis = current_app.inventory_analytics.get_category_analysis()
        
        return jsonify({
            'cash_flow': cash_flow,
            'top_customers': top_customers,
            'sales_trend': sales_trend[:6],  # Last 6 months
            'category_analysis': category_analysis[:5],  # Top 5 categories
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Dashboard charts error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@dashboard_bp.route('/api/dashboard/kpis')
@login_required
def dashboard_kpis():
    """Get key performance indicators"""
    try:
        # Financial KPIs
        financial_kpis = current_app.financial_analytics.get_financial_kpis()
        
        # Inventory KPIs
        inventory_kpis = current_app.inventory_analytics.get_inventory_kpis()
        
        # Sales KPIs
        sales_kpis = current_app.sales_analytics.get_sales_kpis()
        
        return jsonify({
            'financial_kpis': financial_kpis,
            'inventory_kpis': inventory_kpis,
            'sales_kpis': sales_kpis,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Dashboard KPIs error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@dashboard_bp.route('/api/dashboard/alerts')
@login_required
def dashboard_alerts():
    """Get system alerts and notifications"""
    try:
        alerts = []
        
        # Credit risk alerts
        credit_risks = current_app.financial_analytics.get_credit_risk_analysis()
        high_risk_customers = [c for c in credit_risks if c.get('RiskLevel') == 'HIGH RISK']
        
        if high_risk_customers:
            alerts.append({
                'type': 'warning',
                'category': 'Financial',
                'message': f"{len(high_risk_customers)} customers with high credit risk",
                'count': len(high_risk_customers)
            })
        
        # Stock alerts
        stock_alerts = current_app.inventory_analytics.get_stock_alerts()
        out_of_stock = [s for s in stock_alerts if s.get('AlertType') == 'OUT_OF_STOCK']
        low_stock = [s for s in stock_alerts if s.get('AlertType') == 'LOW_STOCK']
        
        if out_of_stock:
            alerts.append({
                'type': 'danger',
                'category': 'Inventory',
                'message': f"{len(out_of_stock)} products out of stock",
                'count': len(out_of_stock)
            })
        
        if low_stock:
            alerts.append({
                'type': 'warning',
                'category': 'Inventory',
                'message': f"{len(low_stock)} products with low stock",
                'count': len(low_stock)
            })
        
        return jsonify({
            'alerts': alerts,
            'total_alerts': len(alerts),
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Dashboard alerts error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

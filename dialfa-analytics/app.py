"""
Dialfa Business Intelligence Dashboard
Main Flask Application
"""

from flask import Flask, render_template, jsonify, request, send_file, session
import os
from datetime import datetime
import logging
import traceback
from flask_babel import Babel, _, get_locale
from config import Config

# Import our custom modules
from database.connection import DatabaseManager
from analytics.financial import FinancialAnalytics
from analytics.inventory import InventoryAnalytics
from analytics.sales import SalesAnalytics

# Import routes
from routes.dashboard import dashboard_bp
from routes.financial import financial_bp
from routes.inventory import inventory_bp
from routes.sales import sales_bp
from routes.retool_compat import retool_bp

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = 'dialfa-analytics-2025'
    app.config['DEBUG'] = True
    app.config.from_object(Config)
    
    # Initialize Babel for internationalization
    babel = Babel()
    babel.init_app(app)
    
    def get_locale():
        # 1. Check if language is set in session
        if 'language' in session:
            return session['language']
        # 2. Check if language is in URL parameters
        if request.args.get('lang'):
            session['language'] = request.args.get('lang')
            return session['language']
        # 3. Use browser's preferred language
        return request.accept_languages.best_match(app.config['LANGUAGES'].keys()) or app.config['BABEL_DEFAULT_LOCALE']
    
    babel.locale_selector_func = get_locale
    
    # Make get_locale and translation functions available in templates
    @app.context_processor
    def inject_conf_vars():
        return {
            'get_locale': get_locale,
            'LANGUAGES': app.config['LANGUAGES']
        }
    
    # Make Babel functions available in Jinja2 templates
    app.jinja_env.globals.update(_=_, ngettext=lambda s, p, n: s if n == 1 else p)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize database manager
    try:
        db_manager = DatabaseManager()
        app.logger.info("Database manager initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize database manager: {e}")
        raise
    
    # Initialize analytics modules
    try:
        financial_analytics = FinancialAnalytics(db_manager)
        inventory_analytics = InventoryAnalytics(db_manager)
        sales_analytics = SalesAnalytics(db_manager)
        app.logger.info("Analytics modules initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize analytics modules: {e}")
        raise
    
    # Store in app context for access in routes
    app.db_manager = db_manager
    app.financial_analytics = financial_analytics
    app.inventory_analytics = inventory_analytics
    app.sales_analytics = sales_analytics
    
    # Register blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(financial_bp, url_prefix='/financial')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(retool_bp)
    
    @app.route('/')
    def index():
        """Main dashboard page"""
        try:
            return render_template('dashboard.html')
        except Exception as e:
            app.logger.error(f"Error rendering dashboard: {e}")
            return render_template('error.html', error=str(e)), 500
    
    @app.route('/api/health')
    def health_check():
        """Health check endpoint"""
        try:
            db_status = db_manager.test_connection()
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'database': 'connected' if db_status else 'disconnected',
                'version': '1.0.0'
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @app.route('/api/system-info')
    def system_info():
        """Get system information"""
        try:
            # Test both databases
            spisa_status = db_manager.test_connection()
            
            # Get basic table counts
            customer_count = db_manager.execute_scalar("SELECT COUNT(*) FROM Customers", 'SPISA')
            transaction_count = db_manager.execute_scalar("SELECT COUNT(*) FROM Transactions", 'SPISA')
            
            return jsonify({
                'databases': {
                    'SPISA': 'connected' if spisa_status else 'disconnected',
                    'xERP': 'available'
                },
                'data_summary': {
                    'customers': customer_count or 0,
                    'transactions': transaction_count or 0
                },
                'last_updated': datetime.now().isoformat()
            })
        except Exception as e:
            app.logger.error(f"System info error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/favicon.ico')
    def favicon():
        """Serve favicon"""
        return '', 204  # No content
    
    @app.route('/set_language/<language>')
    def set_language(language=None):
        """Set the language preference"""
        if language in app.config['LANGUAGES']:
            session['language'] = language
        return jsonify({'status': 'success', 'language': session.get('language', 'es')})
    
    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', 
                             error="Page not found", 
                             error_code=404), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        return render_template('error.html', 
                             error="Internal server error", 
                             error_code=500), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle uncaught exceptions"""
        app.logger.error(f"Unhandled exception: {e}")
        app.logger.error(traceback.format_exc())
        return render_template('error.html', 
                             error="An unexpected error occurred", 
                             error_code=500), 500
    
    # Add template filters
    @app.template_filter('currency')
    def currency_filter(amount):
        """Format currency in templates"""
        if amount is None:
            return "$0"
        if amount >= 1000000:
            return f"${amount/1000000:.1f}M"
        elif amount >= 1000:
            return f"${amount/1000:.1f}K"
        else:
            return f"${amount:,.2f}"
    
    @app.template_filter('percentage')
    def percentage_filter(value):
        """Format percentage in templates"""
        if value is None:
            return "0%"
        return f"{value:.1f}%"
    
    return app

if __name__ == '__main__':
    try:
        app = create_app()
        app.logger.info("Starting Dialfa Analytics Dashboard...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"Failed to start application: {e}")
        traceback.print_exc()

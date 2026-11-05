# Dialfa Business Intelligence Dashboard

A comprehensive Python-based business intelligence dashboard for analyzing financial, inventory, and sales data from SPISA and xERP databases.

## Features

### 📊 **Executive Dashboard**
- Real-time key performance indicators
- Interactive charts and visualizations
- System health monitoring
- Automated alerts and notifications

### 💰 **Financial Analytics**
- Credit risk analysis
- Cash flow forecasting
- Customer profitability analysis
- Accounts receivable aging
- Payment trend analysis

### 📦 **Inventory Management**
- Stock value analysis
- Slow-moving and dead stock identification
- ABC analysis
- Reorder recommendations
- Category-wise inventory breakdown

### 📈 **Sales Analytics**
- Monthly sales trends
- Customer segmentation
- Product performance analysis
- Seasonal analysis
- Sales forecasting

## Technology Stack

- **Backend**: Python Flask
- **Database**: SQL Server (SPISA & xERP)
- **Data Analysis**: pandas, numpy
- **Visualization**: Plotly.js
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Database Connectivity**: pyodbc

## Installation

### Prerequisites
- Python 3.8 or higher
- Access to SQL Server databases (SPISA & xERP)
- ODBC Driver 17 for SQL Server

### Quick Setup

1. **Clone or extract the project**
   ```bash
   cd dialfa-analytics
   ```

2. **Run the setup script**
   ```bash
   python setup.py
   ```

3. **Start the dashboard**
   ```bash
   python app.py
   ```
   On Diego's PC the database URL is not in `.env`: it lives in Windows Credential Manager
   (`pocs/dialfa-bi/SPISA_PG_URL`, see jarvisx `tools/secrets`), so start it with
   `pocs-secrets run dialfa-bi python app.py`. It listens on 127.0.0.1 only; `DIALFA_HOST=0.0.0.0` shares it
   on the network on purpose, and the debugger is on only with `FLASK_DEBUG=true`.
   Logging in needs `ADMIN_USERNAME` and `ADMIN_PASSWORD_HASH` (a hash from `python scripts/admin_hash.py`);
   without them there is no admin and every login is refused. See `AUTHENTICATION.md`.

4. **Open your browser**
   ```
   http://localhost:5000
   ```

### Manual Installation

1. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure database connection**
   - Everything comes from environment variables (see `config.py`); there are no default credentials:
     - `SPISA_PG_URL`: the SPISA Postgres
     - `DB_SERVER` (default `dialfa.database.windows.net`), `DB_USER`, `DB_PASSWORD`: Azure SQL (xERP);
       without user/password xERP is "no configurado" and the app still starts

3. **Test database connection**
   ```bash
   python -c "from database.connection import DatabaseManager; print('Connected!' if DatabaseManager().test_connection() else 'Failed!')"
   ```

## Project Structure

```
dialfa-analytics/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── setup.py             # Setup script
├── database/
│   ├── connection.py    # Database connection manager
│   └── queries.py       # SQL queries collection
├── analytics/
│   ├── financial.py     # Financial analysis module
│   ├── inventory.py     # Inventory analysis module
│   ├── sales.py         # Sales analysis module
│   └── utils.py         # Utility functions
├── routes/
│   ├── dashboard.py     # Main dashboard routes
│   ├── financial.py     # Financial routes
│   ├── inventory.py     # Inventory routes
│   └── sales.py         # Sales routes
├── templates/
│   ├── base.html        # Base template
│   ├── dashboard.html   # Main dashboard
│   └── error.html       # Error page
├── static/
│   ├── css/style.css    # Custom styles
│   └── js/dashboard.js  # JavaScript functionality
└── exports/             # Generated reports
```

## API Endpoints

### Dashboard
- `GET /api/dashboard/overview` - Executive summary
- `GET /api/dashboard/charts` - Chart data
- `GET /api/dashboard/kpis` - Key performance indicators
- `GET /api/dashboard/alerts` - System alerts

### Financial
- `GET /financial/api/executive-summary` - Financial summary
- `GET /financial/api/credit-risk` - Credit risk analysis
- `GET /financial/api/cash-flow` - Cash flow data
- `GET /financial/api/top-customers` - Top customers by balance
- `GET /financial/api/customer-profitability` - Customer profitability
- `GET /financial/api/aging-analysis` - AR aging analysis

### Inventory
- `GET /inventory/api/summary` - Inventory summary
- `GET /inventory/api/top-stock-value` - Highest value products
- `GET /inventory/api/slow-moving` - Slow-moving stock
- `GET /inventory/api/category-analysis` - Category breakdown
- `GET /inventory/api/reorder-recommendations` - Reorder suggestions
- `GET /inventory/api/abc-analysis` - ABC analysis

### Sales
- `GET /sales/api/summary` - Sales summary
- `GET /sales/api/monthly-trends` - Monthly trends
- `GET /sales/api/customer-segmentation` - Customer segments
- `GET /sales/api/product-performance` - Product performance
- `GET /sales/api/seasonal-analysis` - Seasonal patterns

## Key Business Insights

### Financial Metrics
- **$12.1M** total outstanding receivables
- **$1.5M** overdue amounts requiring attention
- **214** active customers with balances
- Automated credit risk scoring and alerts

### Inventory Optimization
- **1,798** products in inventory
- Dead stock identification (>365 days no sales)
- Slow-moving stock analysis (>180 days)
- ABC analysis for inventory prioritization

### Sales Performance
- Monthly and seasonal trend analysis
- Customer segmentation (Champions, Loyal, At Risk, etc.)
- Product performance tracking
- Sales forecasting capabilities

## Configuration

### Database Settings
```python
# config.py
DB_SERVER = 'dialfa.database.windows.net'
DB_USER = 'fp'
DB_PASSWORD = 'Ab1234,,,'
SPISA_DB = 'SPISA'
XERP_DB = 'xERP'
```

### Business Rules
```python
# config.py
HIGH_RISK_THRESHOLD = 0.5  # 50% overdue
MEDIUM_RISK_THRESHOLD = 0.2  # 20% overdue
SLOW_MOVING_DAYS = 180  # Days without sales
DEAD_STOCK_DAYS = 365  # Days without sales
```

## Usage Examples

### Running Specific Analyses

```python
from analytics.financial import FinancialAnalytics
from database.connection import DatabaseManager

# Initialize
db = DatabaseManager()
financial = FinancialAnalytics(db)

# Get credit risk analysis
risk_data = financial.get_credit_risk_analysis()

# Get cash flow forecast
cash_flow = financial.get_cash_flow_forecast(months=12)
```

### Custom Queries

```python
# Execute custom SQL
query = "SELECT COUNT(*) FROM Customers WHERE Type = 0"
result = db.execute_query(query, 'SPISA')
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check network connectivity
   - Verify credentials in `config.py`
   - Ensure ODBC Driver 17 is installed

2. **Import Errors**
   - Run `pip install -r requirements.txt`
   - Check Python version (3.8+ required)

3. **Charts Not Loading**
   - Check browser console for JavaScript errors
   - Verify API endpoints are responding
   - Clear browser cache

### Health Check
```bash
curl http://localhost:5000/api/health
```

## Development

### Adding New Analytics

1. Create analysis function in appropriate module
2. Add route in corresponding routes file
3. Update frontend to display results
4. Add tests for new functionality

### Database Schema Changes

1. Update queries in `database/queries.py`
2. Test with sample data
3. Update documentation

## Security Notes

- Database credentials are stored in `config.py`
- Use environment variables for production
- Implement proper authentication for production use
- Regular security updates recommended

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API endpoint documentation
3. Check database connectivity
4. Verify data availability

## License

Internal use only - Dialfa Business Intelligence Dashboard

---

**Generated**: September 26, 2025  
**Version**: 1.0.0  
**Python**: 3.8+  
**Databases**: SPISA, xERP

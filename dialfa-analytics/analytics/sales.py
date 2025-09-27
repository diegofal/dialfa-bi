"""
Sales Analytics Module
Provides comprehensive sales analysis capabilities
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from .utils import format_currency, calculate_growth_rate, clean_dataframe
from database.queries import SalesQueries

class SalesAnalytics:
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self.queries = SalesQueries()
    
    def get_summary(self):
        """Get sales summary metrics from xERP database"""
        try:
            df = self.db.execute_query(self.queries.XERP_SALES_SUMMARY, 'xERP')
            df = clean_dataframe(df)
            
            if not df.empty:
                row = df.iloc[0]
                return {
                        'total_transactions': int(row['TotalTransactions']),
                        'total_revenue': float(row['TotalRevenue']),
                        'unique_customers': int(row['UniqueCustomers']),
                        'avg_invoice_size': float(row['AvgInvoiceSize']),
                        'formatted': {
                            'total_revenue': format_currency(row['TotalRevenue'], 'ARS', 'xERP'),
                            'avg_invoice_size': format_currency(row['AvgInvoiceSize'], 'ARS', 'xERP')
                        }
                    }
            return {}
        except Exception as e:
            self.logger.error(f"Error getting sales summary: {e}")
            return {}
    
    def get_monthly_trends(self):
        """Get monthly sales trends from xERP database"""
        try:
            df = self.db.execute_query(self.queries.XERP_MONTHLY_SALES_TREND, 'xERP')
            df = clean_dataframe(df)
            
            if not df.empty:
                # Add formatted columns (xERP data = ARS)
                df['FormattedRevenue'] = df['MonthlyRevenue'].apply(lambda x: format_currency(x, 'ARS', 'xERP'))
                df['MonthYearLabel'] = df.apply(lambda x: f"{x['MonthName']} {x['Year']}", axis=1)
                
                # Calculate month-over-month growth manually since xERP query doesn't include it
                df = df.sort_values(['Year', 'Month'])
                df['MonthOverMonthGrowth'] = df['MonthlyRevenue'].pct_change() * 100
                df['MonthOverMonthGrowth'] = df['MonthOverMonthGrowth'].fillna(0)
                
                # Sort back to descending order for display
                df = df.sort_values(['Year', 'Month'], ascending=[False, False])
                
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error getting monthly trends: {e}")
            return []
    
    def get_xerp_top_customers(self, limit=10):
        """Get top customers from xERP system"""
        try:
            query = self.queries.XERP_TOP_CUSTOMERS.format(limit=limit)
            df = self.db.execute_query(query, 'xERP')
            df = clean_dataframe(df)
            
            # Add formatted columns
            df['FormattedRevenue'] = df['TotalRevenue'].apply(format_currency)
            df['AvgOrderValue'] = df['TotalRevenue'] / df['OrderCount']
            df['FormattedAvgOrder'] = df['AvgOrderValue'].apply(format_currency)
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error getting xERP top customers: {e}")
            return []
    
    def get_sales_performance_by_period(self, period='month'):
        """Get sales performance by different time periods"""
        try:
            if period == 'month':
                period_query = """
                SELECT 
                    YEAR(InvoiceDate) as Year,
                    MONTH(InvoiceDate) as Month,
                    DATENAME(MONTH, InvoiceDate) as PeriodName,
                    SUM(InvoiceAmount) as Revenue,
                    COUNT(*) as TransactionCount,
                    COUNT(DISTINCT CustomerId) as UniqueCustomers
                FROM Transactions
                WHERE Type = 1 
                AND InvoiceDate >= DATEADD(MONTH, -12, GETDATE())
                AND InvoiceDate > '2020-01-01'
                GROUP BY YEAR(InvoiceDate), MONTH(InvoiceDate), DATENAME(MONTH, InvoiceDate)
                ORDER BY Year DESC, Month DESC
                """
            elif period == 'quarter':
                period_query = """
                SELECT 
                    YEAR(InvoiceDate) as Year,
                    DATEPART(QUARTER, InvoiceDate) as Quarter,
                    'Q' + CAST(DATEPART(QUARTER, InvoiceDate) AS VARCHAR) as PeriodName,
                    SUM(InvoiceAmount) as Revenue,
                    COUNT(*) as TransactionCount,
                    COUNT(DISTINCT CustomerId) as UniqueCustomers
                FROM Transactions
                WHERE Type = 1 
                AND InvoiceDate >= DATEADD(YEAR, -2, GETDATE())
                AND InvoiceDate > '2020-01-01'
                GROUP BY YEAR(InvoiceDate), DATEPART(QUARTER, InvoiceDate)
                ORDER BY Year DESC, Quarter DESC
                """
            else:  # year
                period_query = """
                SELECT 
                    YEAR(InvoiceDate) as Year,
                    YEAR(InvoiceDate) as PeriodName,
                    SUM(InvoiceAmount) as Revenue,
                    COUNT(*) as TransactionCount,
                    COUNT(DISTINCT CustomerId) as UniqueCustomers
                FROM Transactions
                WHERE Type = 1 
                AND InvoiceDate >= DATEADD(YEAR, -5, GETDATE())
                AND InvoiceDate > '2020-01-01'
                GROUP BY YEAR(InvoiceDate)
                ORDER BY Year DESC
                """
            
            df = self.db.execute_query(period_query, 'SPISA')
            df = clean_dataframe(df)
            
            if not df.empty:
                # Calculate period-over-period growth
                df['RevenueGrowth'] = df['Revenue'].pct_change() * 100
                df['FormattedRevenue'] = df['Revenue'].apply(format_currency)
                df['AvgTransactionSize'] = df['Revenue'] / df['TransactionCount']
                df['FormattedAvgTransaction'] = df['AvgTransactionSize'].apply(format_currency)
                
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error getting sales performance by {period}: {e}")
            return []
    
    def get_customer_segmentation(self):
        """Segment customers based on sales behavior"""
        try:
            segmentation_query = """
            WITH CustomerSales AS (
                SELECT 
                    c.Name,
                    COUNT(t.Id) as TransactionCount,
                    SUM(t.InvoiceAmount) as TotalRevenue,
                    AVG(t.InvoiceAmount) as AvgInvoiceSize,
                    DATEDIFF(DAY, MIN(t.InvoiceDate), MAX(t.InvoiceDate)) as CustomerLifespanDays,
                    MAX(t.InvoiceDate) as LastPurchaseDate,
                    DATEDIFF(DAY, MAX(t.InvoiceDate), GETDATE()) as DaysSinceLastPurchase
                FROM Customers c
                INNER JOIN Transactions t ON c.Id = t.CustomerId
                WHERE t.Type = 1 
                AND t.InvoiceDate >= DATEADD(YEAR, -2, GETDATE())
                GROUP BY c.Id, c.Name
            )
            SELECT 
                *,
                CASE 
                    WHEN TotalRevenue > 500000 AND DaysSinceLastPurchase < 90 THEN 'Champions'
                    WHEN TotalRevenue > 200000 AND DaysSinceLastPurchase < 180 THEN 'Loyal Customers'
                    WHEN TotalRevenue > 100000 AND DaysSinceLastPurchase < 365 THEN 'Potential Loyalists'
                    WHEN DaysSinceLastPurchase < 90 THEN 'New Customers'
                    WHEN DaysSinceLastPurchase > 365 THEN 'At Risk'
                    ELSE 'Regular Customers'
                END as CustomerSegment,
                TotalRevenue / NULLIF(CustomerLifespanDays, 0) * 365 as AnnualizedRevenue
            FROM CustomerSales
            ORDER BY TotalRevenue DESC
            """
            
            df = self.db.execute_query(segmentation_query, 'SPISA')
            df = clean_dataframe(df)
            
            # Add formatted columns
            df['FormattedRevenue'] = df['TotalRevenue'].apply(format_currency)
            df['FormattedAvgInvoice'] = df['AvgInvoiceSize'].apply(format_currency)
            df['FormattedAnnualized'] = df['AnnualizedRevenue'].apply(format_currency)
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in customer segmentation: {e}")
            return []
    
    def get_product_performance(self):
        """Analyze product sales performance"""
        try:
            product_query = """
            SELECT 
                a.descripcion as ProductName,
                c.Descripcion as Category,
                SUM(npi.Cantidad) as TotalQuantitySold,
                SUM(npi.Cantidad * npi.PrecioUnitario) as TotalRevenue,
                COUNT(DISTINCT np.IdNotaPedido) as OrderCount,
                AVG(npi.PrecioUnitario) as AvgSellingPrice,
                MAX(np.FechaEmision) as LastSaleDate
            FROM NotaPedido_Items npi
            INNER JOIN NotaPedidos np ON npi.IdNotaPedido = np.IdNotaPedido
            INNER JOIN Articulos a ON npi.IdArticulo = a.IdArticulo
            INNER JOIN Categorias c ON a.IdCategoria = c.IdCategoria
            WHERE np.FechaEmision >= DATEADD(YEAR, -1, GETDATE())
            GROUP BY a.IdArticulo, a.descripcion, c.Descripcion
            ORDER BY TotalRevenue DESC
            """
            
            df = self.db.execute_query(product_query, 'SPISA')
            df = clean_dataframe(df)
            
            if not df.empty:
                # Add formatted columns
                df['FormattedRevenue'] = df['TotalRevenue'].apply(format_currency)
                df['FormattedAvgPrice'] = df['AvgSellingPrice'].apply(format_currency)
                df['AvgOrderSize'] = df['TotalQuantitySold'] / df['OrderCount']
                
                # Calculate revenue percentage
                total_revenue = df['TotalRevenue'].sum()
                df['RevenuePercentage'] = (df['TotalRevenue'] / total_revenue * 100) if total_revenue > 0 else 0
                
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in product performance analysis: {e}")
            return []
    
    def get_seasonal_analysis(self):
        """Analyze seasonal sales patterns"""
        try:
            seasonal_query = """
            SELECT 
                MONTH(InvoiceDate) as Month,
                DATENAME(MONTH, InvoiceDate) as MonthName,
                AVG(InvoiceAmount) as AvgMonthlyRevenue,
                COUNT(*) as AvgTransactionCount,
                STDEV(InvoiceAmount) as RevenueVolatility
            FROM Transactions
            WHERE Type = 1 
            AND InvoiceDate >= DATEADD(YEAR, -3, GETDATE())
            AND InvoiceDate > '2020-01-01'
            GROUP BY MONTH(InvoiceDate), DATENAME(MONTH, InvoiceDate)
            ORDER BY Month
            """
            
            df = self.db.execute_query(seasonal_query, 'SPISA')
            df = clean_dataframe(df)
            
            if not df.empty:
                # Calculate seasonality index
                overall_avg = df['AvgMonthlyRevenue'].mean()
                df['SeasonalityIndex'] = (df['AvgMonthlyRevenue'] / overall_avg) * 100
                df['FormattedRevenue'] = df['AvgMonthlyRevenue'].apply(format_currency)
                
                # Categorize seasons
                df['SeasonCategory'] = df['SeasonalityIndex'].apply(self._categorize_season)
                
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in seasonal analysis: {e}")
            return []
    
    def get_sales_kpis(self):
        """Calculate key sales KPIs"""
        try:
            # Current vs previous period comparison
            current_period_query = """
            SELECT 
                SUM(InvoiceAmount) as CurrentRevenue,
                COUNT(*) as CurrentTransactions,
                COUNT(DISTINCT CustomerId) as CurrentCustomers,
                AVG(InvoiceAmount) as CurrentAvgInvoice
            FROM Transactions
            WHERE Type = 1
            AND InvoiceDate >= DATEADD(MONTH, -1, GETDATE())
            AND InvoiceDate > '2020-01-01'
            """
            
            previous_period_query = """
            SELECT 
                SUM(InvoiceAmount) as PreviousRevenue,
                COUNT(*) as PreviousTransactions,
                COUNT(DISTINCT CustomerId) as PreviousCustomers,
                AVG(InvoiceAmount) as PreviousAvgInvoice
            FROM Transactions
            WHERE Type = 1
            AND InvoiceDate >= DATEADD(MONTH, -2, GETDATE())
            AND InvoiceDate < DATEADD(MONTH, -1, GETDATE())
            """
            
            current_df = self.db.execute_query(current_period_query, 'SPISA')
            previous_df = self.db.execute_query(previous_period_query, 'SPISA')
            
            if not current_df.empty and not previous_df.empty:
                current = current_df.iloc[0]
                previous = previous_df.iloc[0]
                
                return {
                    'current_revenue': float(current['CurrentRevenue']),
                    'current_transactions': int(current['CurrentTransactions']),
                    'current_customers': int(current['CurrentCustomers']),
                    'current_avg_invoice': float(current['CurrentAvgInvoice']),
                    'revenue_growth': calculate_growth_rate(current['CurrentRevenue'], previous['PreviousRevenue']),
                    'transaction_growth': calculate_growth_rate(current['CurrentTransactions'], previous['PreviousTransactions']),
                    'customer_growth': calculate_growth_rate(current['CurrentCustomers'], previous['PreviousCustomers']),
                    'formatted': {
                        'current_revenue': format_currency(current['CurrentRevenue']),
                        'current_avg_invoice': format_currency(current['CurrentAvgInvoice'])
                    }
                }
            
            return {}
        except Exception as e:
            self.logger.error(f"Error calculating sales KPIs: {e}")
            return {}
    
    def _categorize_season(self, seasonality_index):
        """Categorize seasonal performance"""
        if seasonality_index > 120:
            return 'Peak Season'
        elif seasonality_index > 110:
            return 'High Season'
        elif seasonality_index < 80:
            return 'Low Season'
        elif seasonality_index < 90:
            return 'Slow Season'
        else:
            return 'Normal Season'
    
    def get_sales_forecast(self, months_ahead=6):
        """Generate simple sales forecast based on trends"""
        try:
            # Get historical data for trend analysis
            historical_query = """
            SELECT 
                YEAR(InvoiceDate) as Year,
                MONTH(InvoiceDate) as Month,
                SUM(InvoiceAmount) as MonthlyRevenue
            FROM Transactions
            WHERE Type = 1 
            AND InvoiceDate >= DATEADD(MONTH, -12, GETDATE())
            AND InvoiceDate > '2020-01-01'
            GROUP BY YEAR(InvoiceDate), MONTH(InvoiceDate)
            ORDER BY Year, Month
            """
            
            df = self.db.execute_query(historical_query, 'SPISA')
            df = clean_dataframe(df)
            
            if len(df) >= 3:  # Need at least 3 months of data
                # Simple linear trend calculation
                df['Period'] = range(len(df))
                
                # Calculate trend using simple linear regression
                x = df['Period'].values
                y = df['MonthlyRevenue'].values
                
                # Simple trend calculation
                trend = np.polyfit(x, y, 1)[0]  # slope
                avg_revenue = y.mean()
                
                # Generate forecast
                forecast = []
                last_period = len(df) - 1
                
                for i in range(1, months_ahead + 1):
                    forecast_period = last_period + i
                    forecast_revenue = avg_revenue + (trend * forecast_period)
                    
                    # Add some seasonality based on historical patterns
                    month_index = (forecast_period % 12)
                    seasonal_factor = self._get_seasonal_factor(df, month_index)
                    forecast_revenue *= seasonal_factor
                    
                    forecast.append({
                        'period': forecast_period,
                        'forecast_revenue': max(0, forecast_revenue),  # Ensure non-negative
                        'formatted_forecast': format_currency(max(0, forecast_revenue))
                    })
                
                return forecast
            
            return []
        except Exception as e:
            self.logger.error(f"Error generating sales forecast: {e}")
            return []
    
    def _get_seasonal_factor(self, df, month_index):
        """Calculate seasonal factor for forecasting"""
        try:
            # Simple seasonal adjustment based on historical data
            if len(df) >= 12:
                monthly_avg = df.groupby(df.index % 12)['MonthlyRevenue'].mean()
                overall_avg = df['MonthlyRevenue'].mean()
                return monthly_avg.iloc[month_index] / overall_avg if overall_avg > 0 else 1.0
            return 1.0  # No seasonal adjustment if insufficient data
        except:
            return 1.0
    
    # Retool-compatible methods
    def get_xerp_billed_monthly(self):
        """Get xERP monthly billing exactly as in Retool"""
        try:
            df = self.db.execute_query(self.queries.XERP_BILLED_MONTHLY, 'xERP')
            df = clean_dataframe(df)
            if not df.empty:
                return {'BilledMonthly': float(df.iloc[0]['BilledMonthly'])}
            return {'BilledMonthly': 0}
        except Exception as e:
            self.logger.error(f"Error getting xERP monthly billing: {e}")
            return {'BilledMonthly': 0}
    
    def get_xerp_billed_today(self):
        """Get xERP today billing exactly as in Retool"""
        try:
            df = self.db.execute_query(self.queries.XERP_BILLED_TODAY, 'xERP')
            df = clean_dataframe(df)
            if not df.empty:
                return {'BilledToday': float(df.iloc[0]['BilledToday'])}
            return {'BilledToday': 0}
        except Exception as e:
            self.logger.error(f"Error getting xERP today billing: {e}")
            return {'BilledToday': 0}
    
    def get_xerp_bills(self, view_filter='month'):
        """Get xERP bills exactly as in Retool"""
        try:
            query = self.queries.XERP_BILLS.format(view_filter=view_filter)
            df = self.db.execute_query(query, 'xERP')
            df = clean_dataframe(df)
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error getting xERP bills: {e}")
            return []

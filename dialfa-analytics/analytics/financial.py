"""
Financial Analytics Module
Provides comprehensive financial analysis capabilities
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from .utils import format_currency, calculate_growth_rate, calculate_risk_score, clean_dataframe
from database.queries import FinancialQueries

class FinancialAnalytics:
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self.queries = FinancialQueries()
    
    def get_executive_summary(self):
        """Get key financial metrics for executive dashboard"""
        try:
            df = self.db.execute_query(self.queries.EXECUTIVE_SUMMARY, 'SPISA')
            
            if not df.empty:
                row = df.iloc[0]
                return {
                    'unique_customers': int(row['UniqueCustomers']),
                    'total_outstanding': float(row['TotalOutstanding']),
                    'total_overdue': float(row['TotalOverdue']),
                    'avg_balance': float(row['AvgBalance']),
                    'overdue_percentage': (float(row['TotalOverdue']) / float(row['TotalOutstanding'])) * 100 if row['TotalOutstanding'] > 0 else 0,
                    'formatted': {
                        'total_outstanding': format_currency(row['TotalOutstanding']),
                        'total_overdue': format_currency(row['TotalOverdue']),
                        'avg_balance': format_currency(row['AvgBalance'])
                    }
                }
            return {}
        except Exception as e:
            self.logger.error(f"Error getting executive summary: {e}")
            return {}
    
    def get_credit_risk_analysis(self):
        """Analyze customer credit risk"""
        try:
            df = self.db.execute_query(self.queries.CREDIT_RISK_ANALYSIS, 'SPISA')
            df = clean_dataframe(df)
            
            # Add risk scoring
            df['RiskScore'] = df.apply(calculate_risk_score, axis=1)
            
            # Add formatted currency columns
            df['FormattedBalance'] = df['CurrentBalance'].apply(format_currency)
            df['FormattedOverdue'] = df['OverdueAmount'].apply(format_currency)
            
            # Sort by risk score descending
            df = df.sort_values('RiskScore', ascending=False)
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in credit risk analysis: {e}")
            return []
    
    def get_cash_flow_forecast(self, months=12):
        """Generate cash flow forecast"""
        try:
            df = self.db.execute_query(self.queries.CASH_FLOW_FORECAST, 'SPISA')
            df = clean_dataframe(df)
            
            if not df.empty:
                # Calculate moving averages and trends
                df['MovingAvg3'] = df['ActualPayments'].rolling(window=3, min_periods=1).mean()
                df['MovingAvg6'] = df['ActualPayments'].rolling(window=6, min_periods=1).mean()
                df['MonthOverMonth'] = df['ActualPayments'].pct_change() * 100
                
                # Replace NaN values with None for JSON serialization
                df = df.fillna(0)
                
                # Add formatted values
                df['FormattedPayments'] = df['ActualPayments'].apply(format_currency)
                df['FormattedMovingAvg'] = df['MovingAvg3'].apply(format_currency)
                
                # Create month-year label
                df['MonthYear'] = df.apply(lambda x: f"{x['Year']}-{x['Month']:02d}", axis=1)
                
                return df.to_dict('records')
            return []
        except Exception as e:
            self.logger.error(f"Error in cash flow forecast: {e}")
            return []
    
    def get_top_customers(self, limit=10):
        """Get top customers by outstanding balance"""
        try:
            query = self.queries.TOP_CUSTOMERS.format(limit=limit)
            df = self.db.execute_query(query, 'SPISA')
            df = clean_dataframe(df)
            
            # Add formatted currency columns
            df['FormattedBalance'] = df['OutstandingBalance'].apply(format_currency)
            df['FormattedOverdue'] = df['OverdueAmount'].apply(format_currency)
            
            # Add risk level based on overdue percentage
            df['RiskLevel'] = df['OverduePercentage'].apply(self._categorize_risk)
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error getting top customers: {e}")
            return []
    
    def get_customer_profitability(self):
        """Analyze customer profitability and lifetime value"""
        try:
            df = self.db.execute_query(self.queries.CUSTOMER_PROFITABILITY, 'SPISA')
            df = clean_dataframe(df)
            
            # Add formatted currency columns
            df['FormattedRevenue'] = df['TotalRevenue'].apply(format_currency)
            df['FormattedPayments'] = df['TotalPayments'].apply(format_currency)
            df['FormattedBalance'] = df['CurrentBalance'].apply(format_currency)
            df['FormattedAnnualized'] = df['AnnualizedRevenue'].apply(format_currency)
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in customer profitability analysis: {e}")
            return []
    
    def get_aging_analysis(self):
        """Analyze accounts receivable aging"""
        try:
            # Custom aging query
            aging_query = """
            SELECT 
                c.Name,
                b.Amount as TotalBalance,
                CASE 
                    WHEN b.Due = 0 THEN b.Amount
                    ELSE 0
                END as Current,
                CASE 
                    WHEN b.Due > 0 AND b.Due <= b.Amount * 0.3 THEN b.Due
                    ELSE 0
                END as Days30,
                CASE 
                    WHEN b.Due > b.Amount * 0.3 AND b.Due <= b.Amount * 0.6 THEN b.Due
                    ELSE 0
                END as Days60,
                CASE 
                    WHEN b.Due > b.Amount * 0.6 THEN b.Due
                    ELSE 0
                END as Days90Plus
            FROM Customers c
            INNER JOIN Balances b ON c.Id = b.CustomerId
            WHERE b.Amount > 0
            ORDER BY b.Amount DESC
            """
            
            df = self.db.execute_query(aging_query, 'SPISA')
            df = clean_dataframe(df)
            
            # Add formatted columns
            for col in ['TotalBalance', 'Current', 'Days30', 'Days60', 'Days90Plus']:
                df[f'Formatted{col}'] = df[col].apply(format_currency)
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in aging analysis: {e}")
            return []
    
    def get_payment_trends(self):
        """Analyze payment trends and patterns"""
        try:
            payment_query = """
            SELECT 
                YEAR(PaymentDate) as Year,
                MONTH(PaymentDate) as Month,
                DATENAME(MONTH, PaymentDate) as MonthName,
                COUNT(*) as PaymentCount,
                SUM(PaymentAmount) as TotalPayments,
                AVG(PaymentAmount) as AvgPaymentSize
            FROM Transactions
            WHERE PaymentDate >= DATEADD(MONTH, -12, GETDATE())
            AND PaymentDate > '2020-01-01'
            AND PaymentAmount > 0
            GROUP BY YEAR(PaymentDate), MONTH(PaymentDate), DATENAME(MONTH, PaymentDate)
            ORDER BY Year DESC, Month DESC
            """
            
            df = self.db.execute_query(payment_query, 'SPISA')
            df = clean_dataframe(df)
            
            if not df.empty:
                # Calculate trends
                df['PaymentGrowth'] = df['TotalPayments'].pct_change() * 100
                df['FormattedPayments'] = df['TotalPayments'].apply(format_currency)
                df['FormattedAvgSize'] = df['AvgPaymentSize'].apply(format_currency)
                
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in payment trends analysis: {e}")
            return []
    
    def _categorize_risk(self, overdue_percentage):
        """Categorize risk level based on overdue percentage"""
        if pd.isna(overdue_percentage):
            return 'LOW RISK'
        elif overdue_percentage > 50:
            return 'HIGH RISK'
        elif overdue_percentage > 20:
            return 'MEDIUM RISK'
        else:
            return 'LOW RISK'
    
    def get_financial_kpis(self):
        """Calculate key financial KPIs"""
        try:
            # Get current month data
            current_month_query = """
            SELECT 
                SUM(CASE WHEN Type = 1 THEN InvoiceAmount ELSE 0 END) as CurrentMonthRevenue,
                SUM(CASE WHEN Type = 0 THEN PaymentAmount ELSE 0 END) as CurrentMonthPayments,
                COUNT(DISTINCT CustomerId) as ActiveCustomers
            FROM Transactions
            WHERE MONTH(InvoiceDate) = MONTH(GETDATE())
            AND YEAR(InvoiceDate) = YEAR(GETDATE())
            """
            
            current_df = self.db.execute_query(current_month_query, 'SPISA')
            
            # Get previous month for comparison
            previous_month_query = """
            SELECT 
                SUM(CASE WHEN Type = 1 THEN InvoiceAmount ELSE 0 END) as PreviousMonthRevenue,
                SUM(CASE WHEN Type = 0 THEN PaymentAmount ELSE 0 END) as PreviousMonthPayments
            FROM Transactions
            WHERE MONTH(InvoiceDate) = MONTH(DATEADD(MONTH, -1, GETDATE()))
            AND YEAR(InvoiceDate) = YEAR(DATEADD(MONTH, -1, GETDATE()))
            """
            
            previous_df = self.db.execute_query(previous_month_query, 'SPISA')
            
            if not current_df.empty and not previous_df.empty:
                current = current_df.iloc[0]
                previous = previous_df.iloc[0]
                
                revenue_growth = calculate_growth_rate(
                    current['CurrentMonthRevenue'], 
                    previous['PreviousMonthRevenue']
                )
                
                payment_growth = calculate_growth_rate(
                    current['CurrentMonthPayments'], 
                    previous['PreviousMonthPayments']
                )
                
                return {
                    'current_month_revenue': float(current['CurrentMonthRevenue']),
                    'current_month_payments': float(current['CurrentMonthPayments']),
                    'active_customers': int(current['ActiveCustomers']),
                    'revenue_growth': revenue_growth,
                    'payment_growth': payment_growth,
                    'formatted': {
                        'current_month_revenue': format_currency(current['CurrentMonthRevenue']),
                        'current_month_payments': format_currency(current['CurrentMonthPayments'])
                    }
                }
            
            return {}
        except Exception as e:
            self.logger.error(f"Error calculating financial KPIs: {e}")
            return {}

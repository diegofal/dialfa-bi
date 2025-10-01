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
from cache_config import cache, get_cache_timeout

class FinancialAnalytics:
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self.queries = FinancialQueries()
    
    @cache.cached(timeout=get_cache_timeout('executive_summary'), key_prefix='financial_exec_summary')
    def get_executive_summary(self):
        """Get key financial metrics for executive dashboard"""
        self.logger.info("Executing get_executive_summary (cache miss or expired)")
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
                        'total_outstanding': format_currency(row['TotalOutstanding'], 'ARS', 'SPISA'),
                        'total_overdue': format_currency(row['TotalOverdue'], 'ARS', 'SPISA'),
                        'avg_balance': format_currency(row['AvgBalance'], 'ARS', 'SPISA')
                    }
                }
            return {}
        except Exception as e:
            self.logger.error(f"Error getting executive summary: {e}")
            return {}
    
    @cache.cached(timeout=get_cache_timeout('credit_risk'), key_prefix='financial_credit_risk')
    def get_credit_risk_analysis(self):
        """Analyze customer credit risk"""
        self.logger.info("Executing get_credit_risk_analysis (cache miss or expired)")
        try:
            df = self.db.execute_query(self.queries.CREDIT_RISK_ANALYSIS, 'SPISA')
            df = clean_dataframe(df)
            
            # Add risk scoring
            df['RiskScore'] = df.apply(calculate_risk_score, axis=1)
            
            # Add formatted currency columns
            df['FormattedBalance'] = df['CurrentBalance'].apply(lambda x: format_currency(x, 'ARS', 'SPISA'))
            df['FormattedOverdue'] = df['OverdueAmount'].apply(lambda x: format_currency(x, 'ARS', 'SPISA'))
            
            # Sort by risk score descending
            df = df.sort_values('RiskScore', ascending=False)
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in credit risk analysis: {e}")
            return []
    
    @cache.cached(timeout=get_cache_timeout('cash_flow'), key_prefix='financial_cash_flow_%(months)s')
    def get_cash_flow_history(self, months=12):
        """Get historical cash flow data"""
        self.logger.info(f"Executing get_cash_flow_history for {months} months (cache miss or expired)")
        try:
            query = self.queries.CASH_FLOW_FORECAST.format(months=months)
            df = self.db.execute_query(query, 'SPISA')
            df = clean_dataframe(df)
            
            if not df.empty:
                # Sort by Year, Month for proper trend calculation
                df = df.sort_values(['Year', 'Month'])
                
                # Calculate moving averages and trends
                df['MovingAvg3'] = df['ActualPayments'].rolling(window=3, min_periods=1).mean()
                df['MovingAvg6'] = df['ActualPayments'].rolling(window=6, min_periods=1).mean()
                df['MonthOverMonth'] = df['ActualPayments'].pct_change() * 100
                
                # Replace NaN and inf values with 0 for JSON serialization
                df = df.fillna(0)
                df = df.replace([float('inf'), float('-inf')], 0)
                
                # Add formatted values
                df['FormattedPayments'] = df['ActualPayments'].apply(lambda x: format_currency(x, '$', 'SPISA'))
                df['FormattedMovingAvg'] = df['MovingAvg3'].apply(lambda x: format_currency(x, '$', 'SPISA'))
                
                # Create month-year label
                df['MonthYear'] = df.apply(lambda x: f"{x['Year']}-{x['Month']:02d}", axis=1)
                
                # Sort again for display (most recent first or chronological)
                df = df.sort_values(['Year', 'Month'])
                
                return df.to_dict('records')
            return []
        except Exception as e:
            self.logger.error(f"Error in cash flow history: {e}")
            return []
    
    def get_cash_flow_forecast(self, forecast_months=6):
        """Generate actual cash flow forecast using multiple algorithms"""
        try:
            # Get 24 months of historical data for better predictions
            historical_query = self.queries.CASH_FLOW_FORECAST.format(months=24)
            df_historical = self.db.execute_query(historical_query, 'SPISA')
            df_historical = clean_dataframe(df_historical)
            
            if df_historical.empty:
                return []
            
            # Sort and prepare historical data
            df_historical = df_historical.sort_values(['Year', 'Month'])
            df_historical['Date'] = pd.to_datetime(df_historical[['Year', 'Month']].assign(day=1))
            
            # Generate future dates
            last_date = df_historical['Date'].max()
            future_dates = []
            for i in range(1, forecast_months + 1):
                future_date = last_date + pd.DateOffset(months=i)
                future_dates.append({
                    'Date': future_date,
                    'Year': future_date.year,
                    'Month': future_date.month,
                    'MonthYear': f"{future_date.year}-{future_date.month:02d}"
                })
            
            df_future = pd.DataFrame(future_dates)
            
            # Apply multiple forecasting algorithms
            forecasts = self._apply_forecasting_algorithms(df_historical, df_future)
            
            # Combine historical and forecast data
            result = []
            
            # Add historical data (last 6 months for context)
            historical_context = df_historical.tail(6).copy()
            for _, row in historical_context.iterrows():
                result.append({
                    'Year': int(row['Year']),
                    'Month': int(row['Month']),
                    'MonthYear': f"{int(row['Year'])}-{int(row['Month']):02d}",
                    'ActualPayments': float(row['ActualPayments']),
                    'ForecastedPayments': None,
                    'IsHistorical': True,
                    'Algorithm': 'Historical',
                    'FormattedPayments': format_currency(row['ActualPayments'], '$', 'SPISA'),
                    'ConfidenceInterval': None
                })
            
            # Add forecast data
            for forecast in forecasts:
                result.append(forecast)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in cash flow forecast: {e}")
            return []
    
    def _apply_forecasting_algorithms(self, df_historical, df_future):
        """Apply multiple forecasting algorithms and combine results"""
        forecasts = []
        
        # Algorithm 1: Linear Trend
        trend_forecasts = self._linear_trend_forecast(df_historical, df_future)
        
        # Algorithm 2: Seasonal Decomposition + Trend
        seasonal_forecasts = self._seasonal_forecast(df_historical, df_future)
        
        # Algorithm 3: Exponential Smoothing
        exponential_forecasts = self._exponential_smoothing_forecast(df_historical, df_future)
        
        # Algorithm 4: Moving Average with Growth
        moving_avg_forecasts = self._moving_average_forecast(df_historical, df_future)
        
        # Combine algorithms with weights
        for i, row in df_future.iterrows():
            # Weighted ensemble of forecasts
            trend_value = trend_forecasts[i] if i < len(trend_forecasts) else 0
            seasonal_value = seasonal_forecasts[i] if i < len(seasonal_forecasts) else 0
            exponential_value = exponential_forecasts[i] if i < len(exponential_forecasts) else 0
            moving_avg_value = moving_avg_forecasts[i] if i < len(moving_avg_forecasts) else 0
            
            # Weighted average (adjust weights based on algorithm performance)
            ensemble_forecast = (
                trend_value * 0.25 +           # Linear trend
                seasonal_value * 0.35 +        # Seasonal (highest weight)
                exponential_value * 0.25 +     # Exponential smoothing
                moving_avg_value * 0.15        # Moving average
            )
            
            # Calculate confidence interval (±15% for simplicity)
            confidence_lower = ensemble_forecast * 0.85
            confidence_upper = ensemble_forecast * 1.15
            
            forecasts.append({
                'Year': int(row['Year']),
                'Month': int(row['Month']),
                'MonthYear': row['MonthYear'],
                'ActualPayments': None,
                'ForecastedPayments': float(ensemble_forecast),
                'IsHistorical': False,
                'Algorithm': 'Ensemble',
                'FormattedPayments': format_currency(ensemble_forecast, '$', 'SPISA'),
                'ConfidenceInterval': {
                    'lower': float(confidence_lower),
                    'upper': float(confidence_upper),
                    'formatted_lower': format_currency(confidence_lower, '$', 'SPISA'),
                    'formatted_upper': format_currency(confidence_upper, '$', 'SPISA')
                },
                'ComponentForecasts': {
                    'trend': float(trend_value),
                    'seasonal': float(seasonal_value),
                    'exponential': float(exponential_value),
                    'moving_average': float(moving_avg_value)
                }
            })
        
        return forecasts
    
    def _linear_trend_forecast(self, df_historical, df_future):
        """Simple linear trend forecasting"""
        if len(df_historical) < 2:
            return [df_historical['ActualPayments'].mean()] * len(df_future)
        
        # Create time index
        x = np.arange(len(df_historical))
        y = df_historical['ActualPayments'].values
        
        # Linear regression
        slope, intercept = np.polyfit(x, y, 1)
        
        # Project future values
        future_x = np.arange(len(df_historical), len(df_historical) + len(df_future))
        forecasts = slope * future_x + intercept
        
        # Ensure non-negative values
        forecasts = np.maximum(forecasts, 0)
        
        return forecasts.tolist()
    
    def _seasonal_forecast(self, df_historical, df_future):
        """Seasonal decomposition with trend forecasting"""
        if len(df_historical) < 12:
            # Not enough data for seasonal analysis, fall back to trend
            return self._linear_trend_forecast(df_historical, df_future)
        
        # Calculate seasonal factors (month-over-month patterns)
        df_historical['MonthNum'] = df_historical['Month']
        monthly_avg = df_historical.groupby('MonthNum')['ActualPayments'].mean()
        overall_avg = df_historical['ActualPayments'].mean()
        seasonal_factors = monthly_avg / overall_avg
        
        # Get trend
        trend_forecasts = self._linear_trend_forecast(df_historical, df_future)
        
        # Apply seasonal adjustment
        seasonal_forecasts = []
        for i, row in df_future.iterrows():
            month_num = row['Month']
            seasonal_factor = seasonal_factors.get(month_num, 1.0)
            seasonal_forecast = trend_forecasts[i] * seasonal_factor
            seasonal_forecasts.append(max(seasonal_forecast, 0))
        
        return seasonal_forecasts
    
    def _exponential_smoothing_forecast(self, df_historical, df_future):
        """Exponential smoothing forecasting"""
        if df_historical.empty:
            return [0] * len(df_future)
        
        alpha = 0.3  # Smoothing parameter
        values = df_historical['ActualPayments'].values
        
        # Initialize
        smoothed = [values[0]]
        
        # Calculate exponential smoothing
        for i in range(1, len(values)):
            smoothed_value = alpha * values[i] + (1 - alpha) * smoothed[i-1]
            smoothed.append(smoothed_value)
        
        # Forecast future values (use last smoothed value with slight trend)
        last_smoothed = smoothed[-1]
        recent_trend = (smoothed[-1] - smoothed[-3]) / 2 if len(smoothed) >= 3 else 0
        
        forecasts = []
        for i in range(len(df_future)):
            forecast = last_smoothed + (recent_trend * (i + 1))
            forecasts.append(max(forecast, 0))
        
        return forecasts
    
    def _moving_average_forecast(self, df_historical, df_future):
        """Moving average with growth rate forecasting"""
        if len(df_historical) < 3:
            avg_value = df_historical['ActualPayments'].mean()
            return [avg_value] * len(df_future)
        
        # Calculate 6-month moving average
        window = min(6, len(df_historical))
        moving_avg = df_historical['ActualPayments'].rolling(window=window).mean().iloc[-1]
        
        # Calculate average growth rate
        recent_values = df_historical['ActualPayments'].tail(6).values
        if len(recent_values) >= 2:
            growth_rates = []
            for i in range(1, len(recent_values)):
                if recent_values[i-1] > 0:
                    growth_rate = (recent_values[i] - recent_values[i-1]) / recent_values[i-1]
                    growth_rates.append(growth_rate)
            
            avg_growth_rate = np.mean(growth_rates) if growth_rates else 0
        else:
            avg_growth_rate = 0
        
        # Apply growth rate to moving average
        forecasts = []
        current_value = moving_avg
        for i in range(len(df_future)):
            current_value = current_value * (1 + avg_growth_rate)
            forecasts.append(max(current_value, 0))
        
        return forecasts
    
    @cache.cached(timeout=get_cache_timeout('top_customers'), key_prefix='financial_top_customers_%(limit)s')
    def get_top_customers(self, limit=10):
        """Get top customers by outstanding balance"""
        self.logger.info(f"Executing get_top_customers (top {limit}) (cache miss or expired)")
        try:
            query = self.queries.TOP_CUSTOMERS.format(limit=limit)
            df = self.db.execute_query(query, 'SPISA')
            df = clean_dataframe(df)
            
            # Add formatted currency columns
            df['FormattedBalance'] = df['OutstandingBalance'].apply(lambda x: format_currency(x, 'ARS', 'SPISA'))
            df['FormattedOverdue'] = df['OverdueAmount'].apply(lambda x: format_currency(x, 'ARS', 'SPISA'))
            
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
            df['FormattedRevenue'] = df['TotalRevenue'].apply(lambda x: format_currency(x, '$', 'SPISA'))
            df['FormattedPayments'] = df['TotalPayments'].apply(lambda x: format_currency(x, '$', 'SPISA'))
            df['FormattedBalance'] = df['CurrentBalance'].apply(lambda x: format_currency(x, '$', 'SPISA'))
            df['FormattedAnnualized'] = df['AnnualizedRevenue'].apply(lambda x: format_currency(x, '$', 'SPISA'))
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in customer profitability analysis: {e}")
            return []
    
    @cache.cached(timeout=get_cache_timeout('aging_analysis'), key_prefix='financial_aging')
    def get_aging_analysis(self):
        """Analyze accounts receivable aging"""
        self.logger.info("Executing get_aging_analysis (cache miss or expired)")
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
                df[f'Formatted{col}'] = df[col].apply(lambda x: format_currency(x, '$', 'SPISA'))
            
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
            AND PaymentDate <= GETDATE()
            AND PaymentDate != '0001-01-01 00:00:00'
            AND PaymentDate > '2020-01-01'
            AND PaymentAmount > 0
            GROUP BY YEAR(PaymentDate), MONTH(PaymentDate), DATENAME(MONTH, PaymentDate)
            ORDER BY Year DESC, Month DESC
            """
            
            df = self.db.execute_query(payment_query, 'SPISA')
            df = clean_dataframe(df)
            
            if not df.empty:
                # Sort properly for growth calculation
                df = df.sort_values(['Year', 'Month'])
                
                # Calculate trends
                df['PaymentGrowth'] = df['TotalPayments'].pct_change() * 100
                
                # Replace NaN and infinite values
                df['PaymentGrowth'] = df['PaymentGrowth'].fillna(0)
                df['PaymentGrowth'] = df['PaymentGrowth'].replace([np.inf, -np.inf], 0)
                
                # Format currency
                df['FormattedPayments'] = df['TotalPayments'].apply(lambda x: format_currency(x, '$', 'SPISA'))
                df['FormattedAvgSize'] = df['AvgPaymentSize'].apply(lambda x: format_currency(x, '$', 'SPISA'))
                
                # Sort back to descending for display
                df = df.sort_values(['Year', 'Month'], ascending=[False, False])
                
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
                           'current_month_revenue': format_currency(current['CurrentMonthRevenue'], '$', 'SPISA'),
                           'current_month_payments': format_currency(current['CurrentMonthPayments'], '$', 'SPISA')
                       }
                }
            
            return {}
        except Exception as e:
            self.logger.error(f"Error calculating financial KPIs: {e}")
            return {}
    
    # Retool-compatible methods
    def get_spisa_balances(self):
        """Get SPISA balances exactly as in Retool"""
        try:
            df = self.db.execute_query(self.queries.SPISA_BALANCES, 'SPISA')
            df = clean_dataframe(df)
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error getting SPISA balances: {e}")
            return []
    
    def get_spisa_future_payments(self):
        """Get SPISA future payments exactly as in Retool"""
        try:
            df = self.db.execute_query(self.queries.SPISA_FUTURE_PAYMENTS, 'SPISA')
            df = clean_dataframe(df)
            if not df.empty:
                return {'PaymentAmount': float(df.iloc[0]['PaymentAmount'])}
            return {'PaymentAmount': 0}
        except Exception as e:
            self.logger.error(f"Error getting SPISA future payments: {e}")
            return {'PaymentAmount': 0}
    
    def get_spisa_due_balance(self):
        """Get SPISA due balance exactly as in Retool"""
        try:
            df = self.db.execute_query(self.queries.SPISA_DUE_BALANCE, 'SPISA')
            df = clean_dataframe(df)
            if not df.empty:
                return {'Due': float(df.iloc[0]['Due'])}
            return {'Due': 0}
        except Exception as e:
            self.logger.error(f"Error getting SPISA due balance: {e}")
            return {'Due': 0}
    
    def get_spisa_billed_monthly(self):
        """Get SPISA monthly billing exactly as in Retool"""
        try:
            df = self.db.execute_query(self.queries.SPISA_BILLED_MONTHLY, 'SPISA')
            df = clean_dataframe(df)
            if not df.empty:
                return {'InvoiceAmount': float(df.iloc[0]['InvoiceAmount'])}
            return {'InvoiceAmount': 0}
        except Exception as e:
            self.logger.error(f"Error getting SPISA monthly billing: {e}")
            return {'InvoiceAmount': 0}
    
    def get_spisa_billed_today(self):
        """Get SPISA today billing exactly as in Retool"""
        try:
            df = self.db.execute_query(self.queries.SPISA_BILLED_TODAY, 'SPISA')
            df = clean_dataframe(df)
            if not df.empty:
                return {'InvoiceAmount': float(df.iloc[0]['InvoiceAmount'])}
            return {'InvoiceAmount': 0}
        except Exception as e:
            self.logger.error(f"Error getting SPISA today billing: {e}")
            return {'InvoiceAmount': 0}
    
    def get_spisa_collected_monthly(self):
        """Get SPISA monthly collections (payments received this month) with breakdown by type"""
        try:
            df = self.db.execute_query(self.queries.SPISA_COLLECTED_MONTHLY, 'SPISA')
            df = clean_dataframe(df)
            if not df.empty:
                row = df.iloc[0]
                return {
                    'TotalPayments': float(row['TotalPayments']),
                    'CashPayments': float(row['CashPayments']),
                    'ElectronicPayments': float(row['ElectronicPayments']),
                    'TransactionCount': int(row['TransactionCount']),
                    'CashCount': int(row['CashCount']),
                    'ElectronicCount': int(row['ElectronicCount']),
                    'CashPercentage': (float(row['CashPayments']) / float(row['TotalPayments']) * 100) if float(row['TotalPayments']) > 0 else 0,
                    'ElectronicPercentage': (float(row['ElectronicPayments']) / float(row['TotalPayments']) * 100) if float(row['TotalPayments']) > 0 else 0
                }
            return {
                'TotalPayments': 0,
                'CashPayments': 0,
                'ElectronicPayments': 0,
                'TransactionCount': 0,
                'CashCount': 0,
                'ElectronicCount': 0,
                'CashPercentage': 0,
                'ElectronicPercentage': 0
            }
        except Exception as e:
            self.logger.error(f"Error getting SPISA monthly collections: {e}")
            return {
                'TotalPayments': 0,
                'CashPayments': 0,
                'ElectronicPayments': 0,
                'TransactionCount': 0,
                'CashCount': 0,
                'ElectronicCount': 0,
                'CashPercentage': 0,
                'ElectronicPercentage': 0
            }
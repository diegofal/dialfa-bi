"""
Utility functions for analytics
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def format_currency(amount, currency_symbol='$'):
    """Format amount as currency"""
    if pd.isna(amount) or amount is None:
        return f"{currency_symbol}0"
    
    if amount >= 1000000:
        return f"{currency_symbol}{amount/1000000:.1f}M"
    elif amount >= 1000:
        return f"{currency_symbol}{amount/1000:.1f}K"
    else:
        return f"{currency_symbol}{amount:,.2f}"

def calculate_growth_rate(current, previous):
    """Calculate growth rate percentage"""
    if pd.isna(previous) or previous == 0:
        return 0
    return ((current - previous) / previous) * 100

def calculate_risk_score(row):
    """Calculate risk score based on multiple factors"""
    score = 0
    
    # Overdue percentage weight
    overdue_pct = row.get('OverduePercentage', 0)
    if overdue_pct > 50:
        score += 40
    elif overdue_pct > 20:
        score += 20
    elif overdue_pct > 10:
        score += 10
    
    # Balance size weight
    balance = row.get('CurrentBalance', 0)
    if balance > 1000000:
        score += 30
    elif balance > 500000:
        score += 20
    elif balance > 100000:
        score += 10
    
    return min(score, 100)  # Cap at 100

def categorize_stock_movement(days_since_sale):
    """Categorize stock based on movement"""
    if pd.isna(days_since_sale):
        return 'No Sales Data'
    elif days_since_sale > 365:
        return 'Dead Stock'
    elif days_since_sale > 180:
        return 'Slow Moving'
    elif days_since_sale > 90:
        return 'Moderate'
    else:
        return 'Fast Moving'

def calculate_carrying_cost(stock_value, monthly_rate=0.02):
    """Calculate monthly carrying cost"""
    return stock_value * monthly_rate

def safe_divide(numerator, denominator):
    """Safe division that handles zero denominator"""
    if denominator == 0 or pd.isna(denominator):
        return 0
    return numerator / denominator

def get_date_range_filter(months_back=12):
    """Get date filter for queries"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months_back * 30)
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

def clean_dataframe(df):
    """Clean and prepare dataframe for analysis"""
    # Replace NaN with appropriate defaults
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    df[numeric_columns] = df[numeric_columns].fillna(0)
    
    # Replace NaN in string columns with empty string
    string_columns = df.select_dtypes(include=['object']).columns
    df[string_columns] = df[string_columns].fillna('')
    
    return df

def create_summary_stats(df, value_column):
    """Create summary statistics for a numeric column"""
    if value_column not in df.columns:
        return {}
    
    return {
        'count': len(df),
        'sum': df[value_column].sum(),
        'mean': df[value_column].mean(),
        'median': df[value_column].median(),
        'std': df[value_column].std(),
        'min': df[value_column].min(),
        'max': df[value_column].max()
    }

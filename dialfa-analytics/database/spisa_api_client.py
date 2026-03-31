"""
SPISA API Client - Fetches data from spisa-new (Railway) REST API
Replaces direct Azure SQL queries for sync data and stock snapshots.
"""
import requests
import pandas as pd
import logging
from config import Config

class SpisaApiClient:
    def __init__(self):
        self.config = Config()
        self.base_url = self.config.SPISA_API_URL.rstrip('/')
        self.api_key = self.config.SPISA_API_KEY
        self.logger = logging.getLogger(__name__)

    def _get(self, endpoint, params=None):
        """Make GET request to spisa-new API"""
        url = f"{self.base_url}{endpoint}"
        headers = {'x-api-key': self.api_key}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            self.logger.error(f"SPISA API request failed: {endpoint} - {e}")
            return []

    def get_balances(self):
        """Fetch sync_balances + customer data as DataFrame"""
        data = self._get('/api/public/sync-data/balances')
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame(columns=['CustomerId', 'Name', 'Type', 'Amount', 'Due', 'Date'])

    def get_transactions(self, months=12):
        """Fetch sync_transactions + customer data as DataFrame"""
        data = self._get('/api/public/sync-data/transactions', {'months': months})
        if data:
            df = pd.DataFrame(data)
            # Convert date strings to datetime
            for col in ['InvoiceDate', 'PaymentDate']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            return df
        return pd.DataFrame(columns=[
            'Id', 'CustomerId', 'CustomerName', 'Type', 'RowNum',
            'InvoiceNumber', 'InvoiceDate', 'InvoiceAmount', 'Balance',
            'PaymentReceipt', 'PaymentBank', 'PaymentDate', 'PaymentAmount'
        ])

    def get_stock_snapshots(self, months=12):
        """Fetch stock_snapshots as DataFrame"""
        data = self._get('/api/public/sync-data/stock-snapshots', {'months': months})
        if data:
            df = pd.DataFrame(data)
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            return df
        return pd.DataFrame(columns=['Date', 'StockValue', 'Year', 'Month', 'MonthName'])

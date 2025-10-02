"""
Purchase Order Analytics Module
Provides reorder analysis and supplier performance tracking
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from .utils import format_currency, clean_dataframe
from database.queries import PurchaseQueries
from cache_config import cache, get_cache_timeout

class PurchaseAnalytics:
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self.queries = PurchaseQueries()
    
    @cache.cached(timeout=get_cache_timeout('reorder_analysis'), key_prefix='purchase_reorder_analysis')
    def get_reorder_analysis(self):
        """Get comprehensive reorder analysis with priorities"""
        self.logger.info("Executing get_reorder_analysis (cache miss or expired)")
        try:
            df = self.db.execute_query(self.queries.REORDER_ANALYSIS, 'SPISA')
            df = clean_dataframe(df)
            
            if not df.empty:
                # Format values
                df['FormattedUnitPrice'] = df['UnitPrice'].apply(lambda x: format_currency(x, '', 'SPISA'))
                df['FormattedStockValue'] = df['StockValue'].apply(lambda x: format_currency(x, '', 'SPISA'))
                df['FormattedOrderValue'] = df['SuggestedOrderValue'].apply(lambda x: format_currency(x, '', 'SPISA'))
                df['FormattedReorderPoint'] = df['ReorderPoint'].apply(lambda x: f"{x:.0f}")
                df['FormattedDaysOfCoverage'] = df['DaysOfCoverage'].apply(lambda x: f"{x:.0f}" if x < 999 else '∞')
                df['FormattedExpectedStockoutDate'] = df['ExpectedStockoutDate'].apply(
                    lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) and x is not pd.NaT else '-'
                )
                # Convert ExpectedStockoutDate to string to avoid serialization issues
                df['ExpectedStockoutDate'] = df['ExpectedStockoutDate'].apply(
                    lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) and x is not pd.NaT else None
                )
                
                return df.to_dict('records')
            return []
        except Exception as e:
            self.logger.error(f"Error in reorder analysis: {e}")
            return []
    
    def get_reorder_summary(self):
        """Get summary KPIs for reorder dashboard"""
        try:
            reorder_data = self.get_reorder_analysis()
            
            if not reorder_data:
                return {}
            
            df = pd.DataFrame(reorder_data)
            
            # Calculate KPIs
            urgent_count = len(df[df['Priority'].isin(['OUT_OF_STOCK', 'URGENT'])])
            high_priority_count = len(df[df['Priority'] == 'HIGH'])
            total_order_value = df['SuggestedOrderValue'].sum()
            
            # Items needing reorder
            needs_reorder = df[df['SuggestedOrderQuantity'] > 0]
            
            # By supplier
            by_supplier = needs_reorder.groupby('PreferredSupplier').agg({
                'SuggestedOrderValue': 'sum',
                'idArticulo': 'count'
            }).to_dict('index')
            
            # By priority
            by_priority = needs_reorder.groupby('Priority').agg({
                'SuggestedOrderValue': 'sum',
                'idArticulo': 'count'
            }).to_dict('index')
            
            return {
                'total_items_to_reorder': len(needs_reorder),
                'urgent_items': urgent_count,
                'high_priority_items': high_priority_count,
                'total_order_value': total_order_value,
                'by_supplier': by_supplier,
                'by_priority': by_priority,
                'formatted': {
                    'total_order_value': format_currency(total_order_value, '', 'SPISA')
                }
            }
        except Exception as e:
            self.logger.error(f"Error in reorder summary: {e}")
            return {}
    
    @cache.cached(timeout=get_cache_timeout('supplier_performance'), key_prefix='purchase_supplier_performance')
    def get_supplier_performance(self):
        """Get supplier performance metrics"""
        self.logger.info("Executing get_supplier_performance (cache miss or expired)")
        try:
            df = self.db.execute_query(self.queries.SUPPLIER_PERFORMANCE, 'SPISA')
            df = clean_dataframe(df)
            
            if not df.empty:
                # Format values
                df['FormattedStockValue'] = df['CurrentStockValue'].apply(lambda x: format_currency(x, '', 'SPISA'))
                df['FormattedPurchaseValue'] = df['TotalPurchaseValue'].apply(lambda x: format_currency(x, '', 'SPISA') if pd.notna(x) else '-')
                df['FormattedLeadTime'] = df['AvgLeadTimeDays'].apply(lambda x: f"{x:.0f} dias" if pd.notna(x) else 'N/A')
                
                return df.to_dict('records')
            return []
        except Exception as e:
            self.logger.error(f"Error getting supplier performance: {e}")
            return []


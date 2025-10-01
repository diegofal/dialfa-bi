"""
Inventory Analytics Module
Provides comprehensive inventory analysis capabilities
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from .utils import format_currency, categorize_stock_movement, calculate_carrying_cost, clean_dataframe
from database.queries import InventoryQueries
from cache_config import cache, get_cache_timeout

class InventoryAnalytics:
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        from database.queries import InventoryQueries
        self.queries = InventoryQueries()
    
    def get_summary(self):
        """Get inventory summary metrics"""
        try:
            df = self.db.execute_query(self.queries.INVENTORY_SUMMARY, 'SPISA')
            
            if not df.empty:
                row = df.iloc[0]
                return {
                    'total_products': int(row['TotalProducts']),
                    'total_quantity': float(row['TotalQuantity']),
                    'total_value': float(row['TotalValue']),
                    'in_stock_products': int(row['InStockProducts']),
                    'discontinued_products': int(row['DiscontinuedProducts']),
                    'stock_turnover_rate': self._calculate_turnover_rate(),
                    'formatted': {
                        'total_value': format_currency(row['TotalValue']),
                        'avg_product_value': format_currency(row['TotalValue'] / max(row['TotalProducts'], 1))
                    }
                }
            return {}
        except Exception as e:
            self.logger.error(f"Error getting inventory summary: {e}")
            return {}
    
    def get_top_stock_value(self, limit=10):
        """Get products with highest stock value"""
        try:
            query = self.queries.TOP_STOCK_VALUE.format(limit=limit)
            df = self.db.execute_query(query, 'SPISA')
            df = clean_dataframe(df)
            
            # Add formatted columns (SPISA data = USD)
            df['FormattedStockValue'] = df['StockValue'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
            df['FormattedUnitPrice'] = df['UnitPrice'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error getting top stock value: {e}")
            return []
    
    def get_slow_moving_analysis(self):
        """Analyze slow-moving and dead stock"""
        try:
            df = self.db.execute_query(self.queries.SLOW_MOVING_ANALYSIS, 'SPISA')
            df = clean_dataframe(df)
            
            # Add formatted columns (SPISA data = USD)
            df['FormattedStockValue'] = df['StockValue'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
            df['FormattedCarryingCost'] = df['MonthlyCarryingCost'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
            
            # Calculate annual carrying cost
            df['AnnualCarryingCost'] = df['MonthlyCarryingCost'] * 12
            df['FormattedAnnualCost'] = df['AnnualCarryingCost'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in slow moving analysis: {e}")
            return []
    
    @cache.cached(timeout=get_cache_timeout('category_analysis'), key_prefix='inventory_category')
    def get_category_analysis(self):
        """Analyze inventory by category"""
        self.logger.info("Executing get_category_analysis (cache miss or expired)")
        try:
            df = self.db.execute_query(self.queries.CATEGORY_ANALYSIS, 'SPISA')
            df = clean_dataframe(df)
            
            # Calculate percentages
            total_value = df['TotalValue'].sum()
            df['ValuePercentage'] = (df['TotalValue'] / total_value * 100) if total_value > 0 else 0
            
            # Add formatted columns
            df['FormattedTotalValue'] = df['TotalValue'].apply(format_currency)
            df['FormattedAvgPrice'] = df['AvgUnitPrice'].apply(format_currency)
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in category analysis: {e}")
            return []
    
    def get_reorder_recommendations(self):
        """Get reorder recommendations based on stock levels and sales velocity"""
        try:
            reorder_query = """
            WITH SalesVelocity AS (
                SELECT 
                    npi.IdArticulo,
                    AVG(npi.Cantidad) as AvgMonthlySales,
                    COUNT(*) as SalesFrequency
                FROM NotaPedido_Items npi
                INNER JOIN NotaPedidos np ON npi.IdNotaPedido = np.IdNotaPedido
                WHERE np.FechaEmision >= DATEADD(MONTH, -6, GETDATE())
                GROUP BY npi.IdArticulo
            ),
            StockAnalysis AS (
                SELECT 
                    a.IdArticulo,
                    a.descripcion,
                    a.cantidad as CurrentStock,
                    a.preciounitario,
                    c.Descripcion as Category,
                    COALESCE(sv.AvgMonthlySales, 0) as AvgMonthlySales,
                    COALESCE(sv.SalesFrequency, 0) as SalesFrequency
                FROM Articulos a
                INNER JOIN Categorias c ON a.IdCategoria = c.IdCategoria
                LEFT JOIN SalesVelocity sv ON a.IdArticulo = sv.IdArticulo
                WHERE a.Discontinuado = 0
            )
            SELECT 
                *,
                CASE 
                    WHEN AvgMonthlySales > 0 THEN CurrentStock / AvgMonthlySales
                    ELSE 999
                END as MonthsOfStock,
                CASE 
                    WHEN AvgMonthlySales > 0 AND CurrentStock / AvgMonthlySales < 2 THEN 'URGENT'
                    WHEN AvgMonthlySales > 0 AND CurrentStock / AvgMonthlySales < 3 THEN 'HIGH'
                    WHEN AvgMonthlySales > 0 AND CurrentStock / AvgMonthlySales < 6 THEN 'MEDIUM'
                    ELSE 'LOW'
                END as ReorderPriority,
                AvgMonthlySales * 3 as RecommendedOrderQty
            FROM StockAnalysis
            WHERE AvgMonthlySales > 0
            ORDER BY MonthsOfStock ASC
            """
            
            df = self.db.execute_query(reorder_query, 'SPISA')
            df = clean_dataframe(df)
            
            # Add formatted columns
            df['FormattedUnitPrice'] = df['preciounitario'].apply(format_currency)
            df['RecommendedOrderValue'] = df['RecommendedOrderQty'] * df['preciounitario']
            df['FormattedOrderValue'] = df['RecommendedOrderValue'].apply(format_currency)
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in reorder recommendations: {e}")
            return []
    
    @cache.cached(timeout=get_cache_timeout('abc_analysis'), key_prefix='inventory_abc')
    def get_abc_analysis(self):
        """Perform ABC analysis on inventory"""
        self.logger.info("Executing get_abc_analysis (cache miss or expired)")
        try:
            # Get inventory with sales data
            abc_query = """
            WITH InventoryValue AS (
                SELECT 
                    a.IdArticulo,
                    a.descripcion,
                    a.cantidad * a.preciounitario as StockValue,
                    COALESCE(sales.TotalSold, 0) as TotalSold,
                    COALESCE(sales.SalesValue, 0) as SalesValue
                FROM Articulos a
                LEFT JOIN (
                    SELECT 
                        npi.IdArticulo,
                        SUM(npi.Cantidad) as TotalSold,
                        SUM(npi.Cantidad * npi.PrecioUnitario) as SalesValue
                    FROM NotaPedido_Items npi
                    INNER JOIN NotaPedidos np ON npi.IdNotaPedido = np.IdNotaPedido
                    WHERE np.FechaEmision >= DATEADD(YEAR, -1, GETDATE())
                    GROUP BY npi.IdArticulo
                ) sales ON a.IdArticulo = sales.IdArticulo
                WHERE a.cantidad > 0 AND a.Discontinuado = 0
            )
            SELECT * FROM InventoryValue
            ORDER BY SalesValue DESC
            """
            
            df = self.db.execute_query(abc_query, 'SPISA')
            df = clean_dataframe(df)
            
            if not df.empty:
                # Calculate cumulative percentage
                total_sales_value = df['SalesValue'].sum()
                df['SalesPercentage'] = (df['SalesValue'] / total_sales_value * 100) if total_sales_value > 0 else 0
                df['CumulativePercentage'] = df['SalesPercentage'].cumsum()
                
                # Assign ABC categories
                df['ABCCategory'] = df['CumulativePercentage'].apply(self._assign_abc_category)
                
                # Add formatted columns
                df['FormattedStockValue'] = df['StockValue'].apply(format_currency)
                df['FormattedSalesValue'] = df['SalesValue'].apply(format_currency)
                
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in ABC analysis: {e}")
            return []
    
    def get_inventory_kpis(self):
        """Calculate key inventory KPIs"""
        try:
            # Inventory turnover calculation
            turnover_query = """
            WITH CurrentInventory AS (
                SELECT SUM(cantidad * preciounitario) as CurrentValue
                FROM Articulos
                WHERE cantidad > 0 AND Discontinuado = 0
            ),
            YearlySales AS (
                SELECT SUM(npi.Cantidad * npi.PrecioUnitario) as SalesValue
                FROM NotaPedido_Items npi
                INNER JOIN NotaPedidos np ON npi.IdNotaPedido = np.IdNotaPedido
                WHERE np.FechaEmision >= DATEADD(YEAR, -1, GETDATE())
            )
            SELECT 
                ci.CurrentValue,
                ys.SalesValue,
                CASE 
                    WHEN ci.CurrentValue > 0 THEN ys.SalesValue / ci.CurrentValue
                    ELSE 0
                END as TurnoverRatio
            FROM CurrentInventory ci, YearlySales ys
            """
            
            df = self.db.execute_query(turnover_query, 'SPISA')
            
            if not df.empty:
                row = df.iloc[0]
                
                # Calculate additional KPIs
                days_in_inventory = 365 / row['TurnoverRatio'] if row['TurnoverRatio'] > 0 else 365
                
                return {
                    'current_inventory_value': float(row['CurrentValue']),
                    'annual_sales_value': float(row['SalesValue']),
                    'turnover_ratio': float(row['TurnoverRatio']),
                    'days_in_inventory': days_in_inventory,
                    'formatted': {
                        'current_inventory_value': format_currency(row['CurrentValue']),
                        'annual_sales_value': format_currency(row['SalesValue'])
                    }
                }
            
            return {}
        except Exception as e:
            self.logger.error(f"Error calculating inventory KPIs: {e}")
            return {}
    
    def _calculate_turnover_rate(self):
        """Calculate inventory turnover rate"""
        try:
            # This is a simplified calculation - you might want to make it more sophisticated
            return 4.2  # Placeholder - implement actual calculation
        except:
            return 0
    
    def _assign_abc_category(self, cumulative_percentage):
        """Assign ABC category based on cumulative percentage"""
        if cumulative_percentage <= 80:
            return 'A'
        elif cumulative_percentage <= 95:
            return 'B'
        else:
            return 'C'
    
    @cache.cached(timeout=get_cache_timeout('stock_alerts'), key_prefix='inventory_alerts')
    def get_stock_alerts(self):
        """Get stock level alerts"""
        self.logger.info("Executing get_stock_alerts (cache miss or expired)")
        try:
            alerts_query = """
            SELECT 
                a.descripcion,
                a.cantidad as CurrentStock,
                c.Descripcion as Category,
                CASE 
                    WHEN a.cantidad = 0 THEN 'OUT_OF_STOCK'
                    WHEN a.cantidad < 10 THEN 'LOW_STOCK'
                    WHEN a.cantidad > 1000 THEN 'OVERSTOCK'
                    ELSE 'NORMAL'
                END as AlertType
            FROM Articulos a
            INNER JOIN Categorias c ON a.IdCategoria = c.IdCategoria
            WHERE a.Discontinuado = 0
            AND (a.cantidad = 0 OR a.cantidad < 10 OR a.cantidad > 1000)
            ORDER BY 
                CASE 
                    WHEN a.cantidad = 0 THEN 1
                    WHEN a.cantidad < 10 THEN 2
                    ELSE 3
                END
            """
            
            df = self.db.execute_query(alerts_query, 'SPISA')
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error getting stock alerts: {e}")
            return []
    
    def get_stock_variation_over_time(self):
        """Get detailed stock variation analysis over time"""
        try:
            df = self.db.execute_query(self.queries.STOCK_VARIATION_OVER_TIME, 'SPISA')
            df = clean_dataframe(df)
            
            # Add formatted currency columns
            df['FormattedUnitPrice'] = df['UnitPrice'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
            df['FormattedStockValue'] = df['StockValue'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
            df['FormattedSalesValue'] = df['MonthlySalesValue'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
            df['FormattedCarryingCost'] = df['MonthlyCarryingCost'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
            
            # Add percentage formatting
            df['FormattedTurnoverRate'] = df['TurnoverRate'].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "0.0%")
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error getting stock variation over time: {e}")
            return []
    
    def get_stock_velocity_summary(self):
        """Get comprehensive stock velocity and turnover analysis"""
        try:
            df = self.db.execute_query(self.queries.STOCK_VELOCITY_SUMMARY, 'SPISA')
            df = clean_dataframe(df)
            
            # Handle NaT (Not a Time) values in LastSaleDate
            if 'LastSaleDate' in df.columns:
                df['LastSaleDate'] = df['LastSaleDate'].fillna(pd.Timestamp('1900-01-01'))
            
            # Add formatted currency columns
            df['FormattedUnitPrice'] = df['UnitPrice'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
            df['FormattedStockValue'] = df['StockValue'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
            df['FormattedAnnualSalesValue'] = df['AnnualSalesValue'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
            df['FormattedCarryingCost'] = df['MonthlyCarryingCost'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
            
            # Add percentage formatting
            df['FormattedTurnoverPercentage'] = df['AnnualTurnoverPercentage'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "0.0%")
            df['FormattedTrendPercentage'] = df['TrendPercentage'].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "0.0%")
            
            # Format months of stock
            df['FormattedMonthsOfStock'] = df['MonthsOfStock'].apply(lambda x: f"{x:.1f}" if x < 999 else "∞")
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error getting stock velocity summary: {e}")
            return []
    
    def get_stock_variation_kpis(self):
        """Get key performance indicators from stock variation analysis"""
        try:
            # Get velocity summary data
            velocity_data = self.get_stock_velocity_summary()
            
            if not velocity_data:
                return {}
            
            df = pd.DataFrame(velocity_data)
            
            # Calculate aggregate KPIs
            total_products = len(df)
            total_stock_value = df['StockValue'].sum()
            total_annual_sales = df['AnnualSalesValue'].sum()
            total_carrying_cost = df['MonthlyCarryingCost'].sum()
            
            # Stock health distribution
            health_distribution = df['StockHealthStatus'].value_counts().to_dict()
            
            # Velocity distribution
            high_velocity = len(df[df['AnnualTurnoverPercentage'] >= 400])  # 4+ turns per year
            medium_velocity = len(df[(df['AnnualTurnoverPercentage'] >= 200) & (df['AnnualTurnoverPercentage'] < 400)])  # 2-4 turns
            low_velocity = len(df[(df['AnnualTurnoverPercentage'] > 0) & (df['AnnualTurnoverPercentage'] < 200)])  # <2 turns
            no_movement = len(df[df['AnnualTurnoverPercentage'] == 0])
            
            # Financial impact metrics
            dead_stock_value = df[df['StockHealthStatus'] == 'DEAD_STOCK']['StockValue'].sum()
            overstock_value = df[df['StockHealthStatus'] == 'OVERSTOCK']['StockValue'].sum()
            healthy_stock_value = df[df['StockHealthStatus'] == 'HEALTHY']['StockValue'].sum()
            
            # Turnover efficiency
            overall_turnover = (total_annual_sales / total_stock_value * 100) if total_stock_value > 0 else 0
            
            # Trend analysis
            positive_trend_products = len(df[df['TrendPercentage'] > 5])
            negative_trend_products = len(df[df['TrendPercentage'] < -5])
            
            return {
                'total_products': total_products,
                'total_stock_value': total_stock_value,
                'total_annual_sales': total_annual_sales,
                'monthly_carrying_cost': total_carrying_cost,
                'overall_turnover_percentage': overall_turnover,
                'stock_health_distribution': health_distribution,
                'velocity_distribution': {
                    'high_velocity': high_velocity,
                    'medium_velocity': medium_velocity,
                    'low_velocity': low_velocity,
                    'no_movement': no_movement
                },
                'financial_impact': {
                    'dead_stock_value': dead_stock_value,
                    'overstock_value': overstock_value,
                    'healthy_stock_value': healthy_stock_value,
                    'optimization_potential': dead_stock_value + overstock_value
                },
                'trend_analysis': {
                    'positive_trend_products': positive_trend_products,
                    'negative_trend_products': negative_trend_products,
                    'stable_products': total_products - positive_trend_products - negative_trend_products
                },
                'formatted': {
                    'total_stock_value': format_currency(total_stock_value, 'USD', 'SPISA'),
                    'total_annual_sales': format_currency(total_annual_sales, 'USD', 'SPISA'),
                    'monthly_carrying_cost': format_currency(total_carrying_cost, 'USD', 'SPISA'),
                    'dead_stock_value': format_currency(dead_stock_value, 'USD', 'SPISA'),
                    'overstock_value': format_currency(overstock_value, 'USD', 'SPISA'),
                    'optimization_potential': format_currency(dead_stock_value + overstock_value, 'USD', 'SPISA'),
                    'overall_turnover_percentage': f"{overall_turnover:.1f}%"
                }
            }
        except Exception as e:
            self.logger.error(f"Error calculating stock variation KPIs: {e}")
            return {}
    
    @cache.cached(timeout=get_cache_timeout('stock_value_evolution'), key_prefix='inventory_stock_value_evolution_%(months)s')
    def get_stock_value_evolution(self, months=12):
        """Get historical stock value evolution from StockSnapshots"""
        self.logger.info(f"Executing get_stock_value_evolution for {months} months (cache miss or expired)")
        try:
            query = self.queries.STOCK_VALUE_EVOLUTION.format(months=months)
            df = self.db.execute_query(query, 'SPISA')
            df = clean_dataframe(df)
            
            if not df.empty:
                # Format dates
                df['FormattedDate'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
                df['FormattedValue'] = df['StockValue'].apply(lambda x: format_currency(x, 'USD', 'SPISA'))
                
                return df.to_dict('records')
            return []
        except Exception as e:
            self.logger.error(f"Error getting stock value evolution: {e}")
            return []

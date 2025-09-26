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

class InventoryAnalytics:
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
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
            
            # Add formatted columns
            df['FormattedStockValue'] = df['StockValue'].apply(format_currency)
            df['FormattedUnitPrice'] = df['UnitPrice'].apply(format_currency)
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error getting top stock value: {e}")
            return []
    
    def get_slow_moving_analysis(self):
        """Analyze slow-moving and dead stock"""
        try:
            df = self.db.execute_query(self.queries.SLOW_MOVING_ANALYSIS, 'SPISA')
            df = clean_dataframe(df)
            
            # Add formatted columns
            df['FormattedStockValue'] = df['StockValue'].apply(format_currency)
            df['FormattedCarryingCost'] = df['MonthlyCarryingCost'].apply(format_currency)
            
            # Calculate annual carrying cost
            df['AnnualCarryingCost'] = df['MonthlyCarryingCost'] * 12
            df['FormattedAnnualCost'] = df['AnnualCarryingCost'].apply(format_currency)
            
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error in slow moving analysis: {e}")
            return []
    
    def get_category_analysis(self):
        """Analyze inventory by category"""
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
    
    def get_abc_analysis(self):
        """Perform ABC analysis on inventory"""
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
    
    def get_stock_alerts(self):
        """Get stock level alerts"""
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

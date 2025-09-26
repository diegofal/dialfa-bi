"""
SQL Queries for Dialfa Analytics Dashboard
Based on the comprehensive database analysis
"""

class FinancialQueries:
    """Financial analysis SQL queries"""
    
    EXECUTIVE_SUMMARY = """
    SELECT 
        COUNT(DISTINCT CustomerId) as UniqueCustomers,
        SUM(Amount) as TotalOutstanding,
        SUM(Due) as TotalOverdue,
        AVG(Amount) as AvgBalance
    FROM Balances 
    WHERE Amount > 0
    """
    
    CREDIT_RISK_ANALYSIS = """
    SELECT 
        c.Name,
        b.Amount as CurrentBalance,
        b.Due as OverdueAmount,
        (b.Due / NULLIF(b.Amount, 0)) * 100 as OverduePercentage,
        CASE 
            WHEN b.Due > b.Amount * 0.5 THEN 'HIGH RISK'
            WHEN b.Due > b.Amount * 0.2 THEN 'MEDIUM RISK'
            ELSE 'LOW RISK'
        END as RiskLevel
    FROM Customers c
    INNER JOIN Balances b ON c.Id = b.CustomerId
    WHERE b.Amount > 1000
    ORDER BY OverduePercentage DESC
    """
    
    CASH_FLOW_FORECAST = """
    SELECT 
        YEAR(PaymentDate) as Year,
        MONTH(PaymentDate) as Month,
        SUM(PaymentAmount) as ActualPayments,
        COUNT(*) as TransactionCount
    FROM Transactions 
    WHERE PaymentDate >= DATEADD(MONTH, -12, GETDATE())
    AND PaymentDate > '2020-01-01'
    GROUP BY YEAR(PaymentDate), MONTH(PaymentDate)
    ORDER BY Year, Month
    """
    
    TOP_CUSTOMERS = """
    SELECT TOP {limit}
        c.Name,
        c.Type,
        b.Amount as OutstandingBalance,
        b.Due as OverdueAmount,
        (b.Due / NULLIF(b.Amount, 0)) * 100 as OverduePercentage
    FROM Customers c
    INNER JOIN Balances b ON c.Id = b.CustomerId
    WHERE b.Amount > 0
    ORDER BY b.Amount DESC
    """
    
    CUSTOMER_PROFITABILITY = """
    WITH CustomerMetrics AS (
        SELECT 
            c.Name,
            COUNT(DISTINCT t.Id) as TransactionCount,
            SUM(CASE WHEN t.Type = 1 THEN t.InvoiceAmount ELSE 0 END) as TotalRevenue,
            SUM(CASE WHEN t.Type = 0 THEN t.PaymentAmount ELSE 0 END) as TotalPayments,
            AVG(t.InvoiceAmount) as AvgInvoiceSize,
            DATEDIFF(DAY, MIN(t.InvoiceDate), MAX(t.InvoiceDate)) as CustomerLifespanDays,
            b.Amount as CurrentBalance,
            b.Due as OverdueAmount
        FROM Customers c
        INNER JOIN Transactions t ON c.Id = t.CustomerId
        LEFT JOIN Balances b ON c.Id = b.CustomerId
        WHERE t.InvoiceDate >= '2020-01-01'
        GROUP BY c.Id, c.Name, b.Amount, b.Due
    )
    SELECT 
        *,
        TotalRevenue / NULLIF(CustomerLifespanDays, 0) * 365 as AnnualizedRevenue,
        CASE 
            WHEN TotalRevenue > 1000000 AND OverdueAmount < TotalRevenue * 0.1 THEN 'Premium'
            WHEN TotalRevenue > 500000 AND OverdueAmount < TotalRevenue * 0.2 THEN 'Gold'
            WHEN TotalRevenue > 100000 THEN 'Silver'
            ELSE 'Bronze'
        END as CustomerTier
    FROM CustomerMetrics
    ORDER BY TotalRevenue DESC
    """

class InventoryQueries:
    """Inventory analysis SQL queries"""
    
    INVENTORY_SUMMARY = """
    SELECT 
        COUNT(*) as TotalProducts,
        SUM(cantidad) as TotalQuantity,
        SUM(cantidad * preciounitario) as TotalValue,
        COUNT(CASE WHEN cantidad > 0 THEN 1 END) as InStockProducts,
        COUNT(CASE WHEN Discontinuado = 1 THEN 1 END) as DiscontinuedProducts
    FROM Articulos
    """
    
    TOP_STOCK_VALUE = """
    SELECT TOP {limit}
        a.descripcion,
        a.cantidad as CurrentStock,
        a.preciounitario as UnitPrice,
        a.cantidad * a.preciounitario as StockValue,
        c.Descripcion as Category
    FROM Articulos a
    INNER JOIN Categorias c ON a.IdCategoria = c.IdCategoria
    WHERE a.cantidad > 0
    ORDER BY StockValue DESC
    """
    
    SLOW_MOVING_ANALYSIS = """
    WITH InventoryAnalysis AS (
        SELECT 
            a.descripcion,
            a.cantidad as CurrentStock,
            a.preciounitario * a.cantidad as StockValue,
            c.Descripcion as Category,
            COALESCE(sales.LastSaleDate, '1900-01-01') as LastSaleDate,
            COALESCE(sales.TotalSold, 0) as TotalSold,
            DATEDIFF(DAY, COALESCE(sales.LastSaleDate, '1900-01-01'), GETDATE()) as DaysSinceLastSale
        FROM Articulos a
        INNER JOIN Categorias c ON a.IdCategoria = c.IdCategoria
        LEFT JOIN (
            SELECT 
                npi.IdArticulo,
                MAX(np.FechaEmision) as LastSaleDate,
                SUM(npi.Cantidad) as TotalSold
            FROM NotaPedido_Items npi
            INNER JOIN NotaPedidos np ON npi.IdNotaPedido = np.IdNotaPedido
            WHERE np.FechaEmision >= DATEADD(YEAR, -2, GETDATE())
            GROUP BY npi.IdArticulo
        ) sales ON a.IdArticulo = sales.IdArticulo
        WHERE a.cantidad > 0 AND a.Discontinuado = 0
    )
    SELECT 
        *,
        CASE 
            WHEN DaysSinceLastSale > 365 THEN 'Dead Stock'
            WHEN DaysSinceLastSale > 180 THEN 'Slow Moving'
            WHEN DaysSinceLastSale > 90 THEN 'Moderate'
            ELSE 'Fast Moving'
        END as StockCategory,
        StockValue * 0.02 as MonthlyCarryingCost
    FROM InventoryAnalysis
    ORDER BY StockValue DESC
    """
    
    CATEGORY_ANALYSIS = """
    SELECT 
        c.Descripcion as Category,
        COUNT(a.IdArticulo) as ProductCount,
        SUM(a.cantidad) as TotalQuantity,
        SUM(a.cantidad * a.preciounitario) as TotalValue,
        AVG(a.preciounitario) as AvgUnitPrice
    FROM Categorias c
    LEFT JOIN Articulos a ON c.IdCategoria = a.IdCategoria
    WHERE a.cantidad > 0 AND a.Discontinuado = 0
    GROUP BY c.IdCategoria, c.Descripcion
    ORDER BY TotalValue DESC
    """

class SalesQueries:
    """Sales analysis SQL queries"""
    
    SALES_SUMMARY = """
    SELECT 
        COUNT(*) as TotalTransactions,
        SUM(CASE WHEN Type = 1 THEN InvoiceAmount ELSE 0 END) as TotalRevenue,
        COUNT(DISTINCT CustomerId) as UniqueCustomers,
        AVG(CASE WHEN Type = 1 THEN InvoiceAmount ELSE NULL END) as AvgInvoiceSize
    FROM Transactions
    WHERE InvoiceDate >= DATEADD(YEAR, -1, GETDATE())
    AND InvoiceDate > '2020-01-01'
    """
    
    MONTHLY_SALES_TREND = """
    WITH MonthlySales AS (
        SELECT 
            YEAR(InvoiceDate) as Year,
            MONTH(InvoiceDate) as Month,
            DATENAME(MONTH, InvoiceDate) as MonthName,
            SUM(InvoiceAmount) as MonthlyRevenue,
            COUNT(DISTINCT CustomerId) as UniqueCustomers,
            COUNT(*) as TransactionCount
        FROM Transactions 
        WHERE Type = 1 AND InvoiceDate >= DATEADD(YEAR, -2, GETDATE())
        AND InvoiceDate > '2020-01-01'
        GROUP BY YEAR(InvoiceDate), MONTH(InvoiceDate), DATENAME(MONTH, InvoiceDate)
    )
    SELECT 
        *,
        LAG(MonthlyRevenue) OVER (ORDER BY Year, Month) as PreviousMonth,
        (MonthlyRevenue - LAG(MonthlyRevenue) OVER (ORDER BY Year, Month)) / 
        NULLIF(LAG(MonthlyRevenue) OVER (ORDER BY Year, Month), 0) * 100 as MonthOverMonthGrowth
    FROM MonthlySales
    ORDER BY Year DESC, Month DESC
    """
    
    XERP_TOP_CUSTOMERS = """
    SELECT TOP {limit}
        dm.name as CustomerName,
        COUNT(so.order_no) as OrderCount,
        SUM(dt.ov_amount) as TotalRevenue
    FROM [0_debtors_master] dm
    INNER JOIN [0_sales_orders] so ON dm.debtor_no = so.debtor_no
    INNER JOIN [0_debtor_trans] dt ON so.ID = dt.order_
    WHERE dt.type = 10
    GROUP BY dm.debtor_no, dm.name
    ORDER BY TotalRevenue DESC
    """
    
    XERP_MONTHLY_SALES_TREND = """
    DECLARE @FromDate DATETIME
    SET @FromDate = DATEADD(MONTH, -12, GETDATE())

    SELECT 
      CAST(
        CONCAT(
          DATEPART(YEAR, ord_date),
          RIGHT('00' + CAST(DATEPART(MONTH, ord_date) AS VARCHAR), 2),
          '01'
        ) AS DATETIME
      ) as MonthYear,
      DATEPART(YEAR, ord_date) as Year,
      DATEPART(MONTH, ord_date) as Month,
      DATENAME(MONTH, ord_date) as MonthName,
      SUM(
        CASE 
          WHEN dt.Type = 10 THEN (total * 1.21)
          WHEN dt.Type = 11 THEN (total * -1.21)
          ELSE total
        END
      ) as MonthlyRevenue,
      COUNT(DISTINCT dm.debtor_no) as UniqueCustomers,
      COUNT(*) as TransactionCount
    FROM [0_debtor_trans] dt
      INNER JOIN [0_sales_orders] so ON so.ID = dt.order_
      INNER JOIN [0_debtors_master] dm ON dm.debtor_no = so.debtor_no
    WHERE dt.Type IN (10, 11)
      AND ord_date >= @FromDate
    GROUP BY DATEPART(YEAR, ord_date),
             DATEPART(MONTH, ord_date),
             DATENAME(MONTH, ord_date)
    ORDER BY DATEPART(YEAR, ord_date) DESC,
             DATEPART(MONTH, ord_date) DESC
    """

class CrossSystemQueries:
    """Cross-system comparison queries"""
    
    SYSTEM_COMPARISON = """
    SELECT 
        'SPISA' as System,
        COUNT(*) as CustomerCount,
        SUM(Amount) as TotalOutstanding
    FROM SPISA.dbo.Balances
    WHERE Amount > 0
    """
    
    XERP_COMPARISON = """
    SELECT 
        'xERP' as System,
        COUNT(DISTINCT debtor_no) as CustomerCount,
        SUM(ov_amount) as TotalOutstanding
    FROM xERP.dbo.[0_debtor_trans]
    WHERE type = 10
    """

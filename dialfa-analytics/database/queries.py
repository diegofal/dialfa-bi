"""
SQL Queries for Dialfa Analytics Dashboard
Based on the comprehensive database analysis
"""

class FinancialQueries:
    """Financial analysis SQL queries"""
    
    # xERP-based financial queries (ARS currency)
    XERP_EXECUTIVE_SUMMARY = """
    SELECT 
        COUNT(DISTINCT dm.debtor_no) as UniqueCustomers,
        SUM(dt.ov_amount * 1.21) as TotalOutstanding,
        SUM(CASE WHEN dt.due_date < DATEADD(HOUR, -3, GETDATE()) THEN dt.ov_amount * 1.21 ELSE 0 END) as TotalOverdue,
        AVG(dt.ov_amount * 1.21) as AvgBalance
    FROM [0_debtor_trans] dt
    INNER JOIN [0_debtors_master] dm ON dt.debtor_no = dm.debtor_no
    WHERE dt.Type = 10 
    AND dt.ov_amount > 0
    AND dt.alloc < dt.ov_amount  -- Not fully paid
    """
    
    XERP_CREDIT_RISK_ANALYSIS = """
    SELECT 
        dm.name as Name,
        SUM(dt.ov_amount * 1.21) as CurrentBalance,
        SUM(CASE WHEN dt.due_date < DATEADD(HOUR, -3, GETDATE()) THEN dt.ov_amount * 1.21 ELSE 0 END) as OverdueAmount,
        (SUM(CASE WHEN dt.due_date < DATEADD(HOUR, -3, GETDATE()) THEN dt.ov_amount * 1.21 ELSE 0 END) / 
         NULLIF(SUM(dt.ov_amount * 1.21), 0)) * 100 as OverduePercentage,
        CASE 
            WHEN (SUM(CASE WHEN dt.due_date < DATEADD(HOUR, -3, GETDATE()) THEN dt.ov_amount * 1.21 ELSE 0 END) / 
                  NULLIF(SUM(dt.ov_amount * 1.21), 0)) > 0.5 THEN 'HIGH RISK'
            WHEN (SUM(CASE WHEN dt.due_date < DATEADD(HOUR, -3, GETDATE()) THEN dt.ov_amount * 1.21 ELSE 0 END) / 
                  NULLIF(SUM(dt.ov_amount * 1.21), 0)) > 0.2 THEN 'MEDIUM RISK'
            ELSE 'LOW RISK'
        END as RiskLevel
    FROM [0_debtor_trans] dt
    INNER JOIN [0_debtors_master] dm ON dt.debtor_no = dm.debtor_no
    WHERE dt.Type = 10 
    AND dt.ov_amount > 0
    AND dt.alloc < dt.ov_amount  -- Not fully paid
    GROUP BY dm.debtor_no, dm.name
    HAVING SUM(dt.ov_amount * 1.21) > 1000
    ORDER BY OverduePercentage DESC
    """
    
    XERP_TOP_CUSTOMERS_FINANCIAL = """
    SELECT TOP {limit}
        dm.name as Name,
        'Customer' as Type,
        SUM(dt.ov_amount * 1.21) as OutstandingBalance,
        SUM(CASE WHEN dt.due_date < DATEADD(HOUR, -3, GETDATE()) THEN dt.ov_amount * 1.21 ELSE 0 END) as OverdueAmount,
        (SUM(CASE WHEN dt.due_date < DATEADD(HOUR, -3, GETDATE()) THEN dt.ov_amount * 1.21 ELSE 0 END) / 
         NULLIF(SUM(dt.ov_amount * 1.21), 0)) * 100 as OverduePercentage
    FROM [0_debtor_trans] dt
    INNER JOIN [0_debtors_master] dm ON dt.debtor_no = dm.debtor_no
    WHERE dt.Type = 10 
    AND dt.ov_amount > 0
    AND dt.alloc < dt.ov_amount  -- Not fully paid
    GROUP BY dm.debtor_no, dm.name
    HAVING SUM(dt.ov_amount * 1.21) > 100
    ORDER BY OutstandingBalance DESC
    """
    
    # SPISA financial queries (USD currency) - kept for reference
    EXECUTIVE_SUMMARY = """
    SELECT 
        COUNT(DISTINCT CustomerId) as UniqueCustomers,
        SUM(Amount) as TotalOutstanding,
        SUM(Due) as TotalOverdue,
        AVG(Amount) as AvgBalance
    FROM Balances 
    WHERE Amount > 100
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
        SUM(CASE WHEN Type = 1 THEN PaymentAmount ELSE 0 END) as CashPayments,
        SUM(CASE WHEN Type = 0 THEN PaymentAmount ELSE 0 END) as ElectronicPayments,
        COUNT(*) as TransactionCount,
        COUNT(CASE WHEN Type = 1 THEN 1 END) as CashCount,
        COUNT(CASE WHEN Type = 0 THEN 1 END) as ElectronicCount
    FROM Transactions 
    WHERE PaymentDate >= DATEADD(MONTH, -{months}, DATEADD(HOUR, -3, GETDATE()))
    AND PaymentDate <= DATEADD(HOUR, -3, GETDATE())
    AND PaymentDate != '0001-01-01 00:00:00'
    AND PaymentDate > '2020-01-01'
    AND PaymentAmount > 0  -- Solo pagos reales (excluir registros sin pago)
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
    WHERE b.Amount > 100
    ORDER BY b.Amount DESC
    """
    
    # Retool-compatible queries
    SPISA_BALANCES = """
    SELECT c.Name, b.Amount, b.Due, c.Type
    FROM Balances b
    INNER JOIN Customers c on c.Id = b.CustomerId
    WHERE b.Amount > 100
    """
    
    SPISA_FUTURE_PAYMENTS = """
    SELECT COALESCE(Sum(PaymentAmount),0) as PaymentAmount
    FROM Transactions t
    WHERE t.Type=0 and t.PaymentAmount<>0 and PaymentDate >= GETDATE()
    """
    
    SPISA_DUE_BALANCE = """
    SELECT Sum(Due) as Due
    FROM Balances b
    """
    
    SPISA_BILLED_MONTHLY = """
    SELECT Sum(InvoiceAmount) as InvoiceAmount
    FROM Transactions t
    WHERE MONTH(InvoiceDate) = MONTH(DATEADD(HOUR, -3, GETDATE())) 
    AND YEAR(InvoiceDate) = YEAR(DATEADD(HOUR, -3, GETDATE()))
    AND Type=1
    """
    
    SPISA_BILLED_TODAY = """
    SELECT COALESCE(Sum(InvoiceAmount),0) as InvoiceAmount
    FROM Transactions t
    WHERE CAST(InvoiceDate AS DATE) = CAST(DATEADD(HOUR, -3, GETDATE()) AS DATE)
    AND Type=1
    """
    
    SPISA_COLLECTED_MONTHLY = """
    SELECT 
        COALESCE(SUM(PaymentAmount), 0) as TotalPayments,
        COALESCE(SUM(CASE WHEN Type = 1 THEN PaymentAmount ELSE 0 END), 0) as CashPayments,
        COALESCE(SUM(CASE WHEN Type = 0 THEN PaymentAmount ELSE 0 END), 0) as ElectronicPayments,
        COUNT(*) as TransactionCount,
        COUNT(CASE WHEN Type = 1 THEN 1 END) as CashCount,
        COUNT(CASE WHEN Type = 0 THEN 1 END) as ElectronicCount
    FROM Transactions t
    WHERE MONTH(PaymentDate) = MONTH(DATEADD(HOUR, -3, GETDATE()))
    AND YEAR(PaymentDate) = YEAR(DATEADD(HOUR, -3, GETDATE()))
    AND PaymentDate != '0001-01-01 00:00:00'
    AND PaymentDate > '2020-01-01'
    AND PaymentAmount > 0  -- Solo pagos reales
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
    
    STOCK_VARIATION_OVER_TIME = """
    WITH MonthlyStockMovement AS (
        SELECT 
            a.IdArticulo,
            a.descripcion as ProductName,
            c.Descripcion as Category,
            a.cantidad as CurrentStock,
            a.preciounitario as UnitPrice,
            YEAR(np.FechaEmision) as Year,
            MONTH(np.FechaEmision) as Month,
            DATENAME(MONTH, np.FechaEmision) as MonthName,
            SUM(npi.Cantidad) as QuantitySold,
            COUNT(npi.IdNotaPedido) as OrderCount,
            AVG(npi.Cantidad) as AvgOrderSize,
            SUM(npi.Cantidad * a.preciounitario) as SalesValue
        FROM Articulos a
        INNER JOIN Categorias c ON a.IdCategoria = c.IdCategoria
        LEFT JOIN NotaPedido_Items npi ON a.IdArticulo = npi.IdArticulo
        LEFT JOIN NotaPedidos np ON npi.IdNotaPedido = np.IdNotaPedido
        WHERE np.FechaEmision >= DATEADD(MONTH, -12, GETDATE())
        AND np.FechaEmision > '2020-01-01'
        AND a.Discontinuado = 0
        GROUP BY a.IdArticulo, a.descripcion, c.Descripcion, a.cantidad, a.preciounitario,
                 YEAR(np.FechaEmision), MONTH(np.FechaEmision), DATENAME(MONTH, np.FechaEmision)
    ),
    StockTurnoverAnalysis AS (
        SELECT 
            *,
            -- Calculate stock turnover rate (monthly sales / current stock)
            CASE 
                WHEN CurrentStock > 0 THEN QuantitySold / NULLIF(CurrentStock, 0)
                ELSE 0
            END as TurnoverRate,
            -- Calculate days of stock remaining
            CASE 
                WHEN QuantitySold > 0 THEN (CurrentStock / NULLIF(QuantitySold, 0)) * 30
                ELSE 999
            END as DaysOfStockRemaining,
            -- Calculate velocity category
            CASE 
                WHEN QuantitySold = 0 THEN 'No Movement'
                WHEN (QuantitySold / NULLIF(CurrentStock, 0)) >= 0.5 THEN 'High Velocity'
                WHEN (QuantitySold / NULLIF(CurrentStock, 0)) >= 0.2 THEN 'Medium Velocity'
                WHEN (QuantitySold / NULLIF(CurrentStock, 0)) >= 0.1 THEN 'Low Velocity'
                ELSE 'Very Low Velocity'
            END as VelocityCategory
        FROM MonthlyStockMovement
    )
    SELECT 
        *,
        -- Add financial impact metrics
        CurrentStock * UnitPrice as StockValue,
        SalesValue as MonthlySalesValue,
        (CurrentStock * UnitPrice) * 0.02 as MonthlyCarryingCost,
        -- Add reorder recommendations
        CASE 
            WHEN DaysOfStockRemaining < 30 AND QuantitySold > 0 THEN 'URGENT REORDER'
            WHEN DaysOfStockRemaining < 60 AND QuantitySold > 0 THEN 'REORDER SOON'
            WHEN DaysOfStockRemaining > 180 THEN 'OVERSTOCK RISK'
            ELSE 'NORMAL'
        END as StockStatus
    FROM StockTurnoverAnalysis
    ORDER BY Year DESC, Month DESC, SalesValue DESC
    """
    
    STOCK_VELOCITY_SUMMARY = """
    WITH VelocityAnalysis AS (
        SELECT 
            a.IdArticulo,
            a.descripcion as ProductName,
            c.Descripcion as Category,
            a.cantidad as CurrentStock,
            a.preciounitario as UnitPrice,
            -- Last 3 months sales
            COALESCE(SUM(CASE WHEN np.FechaEmision >= DATEADD(MONTH, -3, GETDATE()) THEN npi.Cantidad END), 0) as Last3MonthsSales,
            -- Last 6 months sales  
            COALESCE(SUM(CASE WHEN np.FechaEmision >= DATEADD(MONTH, -6, GETDATE()) THEN npi.Cantidad END), 0) as Last6MonthsSales,
            -- Last 12 months sales
            COALESCE(SUM(CASE WHEN np.FechaEmision >= DATEADD(MONTH, -12, GETDATE()) THEN npi.Cantidad END), 0) as Last12MonthsSales,
            -- Average monthly sales
            COALESCE(SUM(npi.Cantidad) / NULLIF(DATEDIFF(MONTH, MIN(np.FechaEmision), GETDATE()), 0), 0) as AvgMonthlySales,
            -- Last sale date
            MAX(np.FechaEmision) as LastSaleDate
        FROM Articulos a
        INNER JOIN Categorias c ON a.IdCategoria = c.IdCategoria
        LEFT JOIN NotaPedido_Items npi ON a.IdArticulo = npi.IdArticulo
        LEFT JOIN NotaPedidos np ON npi.IdNotaPedido = np.IdNotaPedido
        WHERE a.Discontinuado = 0
        AND (np.FechaEmision IS NULL OR (np.FechaEmision >= DATEADD(YEAR, -2, GETDATE()) AND np.FechaEmision <= GETDATE()))
        GROUP BY a.IdArticulo, a.descripcion, c.Descripcion, a.cantidad, a.preciounitario
    )
    SELECT 
        *,
        -- Stock turnover metrics
        CASE 
            WHEN CurrentStock > 0 AND AvgMonthlySales > 0 THEN CurrentStock / AvgMonthlySales
            ELSE 999
        END as MonthsOfStock,
        
        CASE 
            WHEN AvgMonthlySales > 0 THEN (Last12MonthsSales / 12.0) / NULLIF(CurrentStock, 0) * 100
            ELSE 0
        END as AnnualTurnoverPercentage,
        
        -- Trend analysis (comparing recent vs historical performance)
        CASE 
            WHEN Last6MonthsSales > 0 AND Last12MonthsSales > 0 THEN 
                ((Last3MonthsSales / 3.0) - ((Last12MonthsSales - Last3MonthsSales) / 9.0)) / 
                NULLIF(((Last12MonthsSales - Last3MonthsSales) / 9.0), 0) * 100
            ELSE 0
        END as TrendPercentage,
        
        -- Stock health classification
        CASE 
            WHEN CurrentStock = 0 THEN 'OUT_OF_STOCK'
            WHEN AvgMonthlySales = 0 AND CurrentStock > 0 THEN 'DEAD_STOCK'
            WHEN CurrentStock / NULLIF(AvgMonthlySales, 0) < 1 THEN 'LOW_STOCK'
            WHEN CurrentStock / NULLIF(AvgMonthlySales, 0) > 6 THEN 'OVERSTOCK'
            ELSE 'HEALTHY'
        END as StockHealthStatus,
        
        -- Financial metrics
        CurrentStock * UnitPrice as StockValue,
        Last12MonthsSales * UnitPrice as AnnualSalesValue,
        (CurrentStock * UnitPrice) * 0.02 as MonthlyCarryingCost
        
    FROM VelocityAnalysis
    WHERE CurrentStock >= 0
    ORDER BY AnnualSalesValue DESC, StockValue DESC
    """
    
    STOCK_VALUE_EVOLUTION = """
    SELECT 
        Date,
        StockValue,
        YEAR(Date) as Year,
        MONTH(Date) as Month,
        DATENAME(MONTH, Date) as MonthName
    FROM StockSnapshots
    WHERE Date >= DATEADD(MONTH, -{months}, GETDATE())
    ORDER BY Date ASC
    """
    
    OUT_OF_STOCK_ANALYSIS = """
    WITH OutOfStockAnalysis AS (
        SELECT 
            a.IdArticulo,
            a.descripcion as ProductName,
            a.preciounitario as UnitPrice,
            c.Descripcion as Category,
            a.Discontinuado as IsDiscontinued,
            COALESCE(sales.LastSaleDate, '1900-01-01') as LastSaleDate,
            COALESCE(sales.TotalSold, 0) as TotalSold,
            COALESCE(sales.Last90DaysSales, 0) as Last90DaysSales,
            COALESCE(sales.Last180DaysSales, 0) as Last180DaysSales,
            COALESCE(sales.Last365DaysSales, 0) as Last365DaysSales,
            DATEDIFF(DAY, COALESCE(sales.LastSaleDate, '1900-01-01'), GETDATE()) as DaysSinceLastSale,
            -- Estimate lost sales (average daily sales * days out of stock, capped at 90 days)
            CASE 
                WHEN sales.Last90DaysSales > 0 THEN 
                    (sales.Last90DaysSales / 90.0) * 
                    CASE WHEN DATEDIFF(DAY, sales.LastSaleDate, GETDATE()) > 90 
                         THEN 90 
                         ELSE DATEDIFF(DAY, sales.LastSaleDate, GETDATE()) 
                    END * a.preciounitario
                ELSE 0
            END as EstimatedLostSales
        FROM Articulos a
        INNER JOIN Categorias c ON a.IdCategoria = c.IdCategoria
        LEFT JOIN (
            SELECT 
                npi.IdArticulo,
                MAX(np.FechaEmision) as LastSaleDate,
                SUM(npi.Cantidad) as TotalSold,
                SUM(CASE WHEN np.FechaEmision >= DATEADD(DAY, -90, GETDATE()) THEN npi.Cantidad ELSE 0 END) as Last90DaysSales,
                SUM(CASE WHEN np.FechaEmision >= DATEADD(DAY, -180, GETDATE()) THEN npi.Cantidad ELSE 0 END) as Last180DaysSales,
                SUM(CASE WHEN np.FechaEmision >= DATEADD(DAY, -365, GETDATE()) THEN npi.Cantidad ELSE 0 END) as Last365DaysSales
            FROM NotaPedido_Items npi
            INNER JOIN NotaPedidos np ON npi.IdNotaPedido = np.IdNotaPedido
            WHERE np.FechaEmision >= DATEADD(YEAR, -2, GETDATE())
            GROUP BY npi.IdArticulo
        ) sales ON a.IdArticulo = sales.IdArticulo
        WHERE a.cantidad = 0  -- Out of stock
    )
    SELECT 
        *,
        CASE 
            WHEN IsDiscontinued = 1 THEN 'Discontinued'
            WHEN DaysSinceLastSale > 365 OR LastSaleDate = '1900-01-01' THEN 'Dead Stock'
            WHEN DaysSinceLastSale > 180 THEN 'Slow Moving'
            WHEN DaysSinceLastSale > 90 THEN 'Moderate'
            ELSE 'Healthy'
        END as StockProfile,
        CASE 
            WHEN IsDiscontinued = 1 THEN 'No Action'
            WHEN DaysSinceLastSale > 365 OR LastSaleDate = '1900-01-01' THEN 'Consider Discontinuing'
            WHEN DaysSinceLastSale > 180 THEN 'Low Priority Reorder'
            WHEN DaysSinceLastSale > 90 THEN 'Monitor & Reorder if Needed'
            ELSE 'URGENT REORDER'
        END as RecommendedAction,
        CASE 
            WHEN IsDiscontinued = 1 THEN 0
            WHEN Last90DaysSales > 0 THEN 4  -- Critical
            WHEN Last180DaysSales > 0 THEN 3  -- High
            WHEN Last365DaysSales > 0 THEN 2  -- Medium
            ELSE 1  -- Low
        END as Priority
    FROM OutOfStockAnalysis
    ORDER BY Priority DESC, EstimatedLostSales DESC
    """

class PurchaseQueries:
    """Purchase order and supplier analysis SQL queries"""
    
    REORDER_ANALYSIS = """
    WITH ProductDemand AS (
        SELECT 
            a.idArticulo,
            a.codigo as ProductCode,
            a.descripcion as ProductName,
            a.cantidad as CurrentStock,
            a.preciounitario as UnitPrice,
            a.cantidad * a.preciounitario as StockValue,
            c.Descripcion as Category,
            s.Name as PreferredSupplier,
            s.Country as SupplierCountry,
            a.proveedor as SupplierId,
            -- Demand calculations
            COALESCE(sales.Last30DaysSales, 0) as Last30DaysSales,
            COALESCE(sales.Last90DaysSales, 0) as Last90DaysSales,
            COALESCE(sales.Last180DaysSales, 0) as Last180DaysSales,
            COALESCE(sales.Last365DaysSales, 0) as Last365DaysSales,
            -- Average daily demand (last 90 days)
            COALESCE(sales.Last90DaysSales, 0) / 90.0 as AvgDailyDemand,
            -- Standard deviation estimate (simplified)
            CASE 
                WHEN sales.Last90DaysSales > 0 THEN 
                    SQRT(COALESCE(sales.Last90DaysSales, 0) / 90.0) * 1.5
                ELSE 0
            END as DemandStdDev,
            COALESCE(sales.LastSaleDate, '1900-01-01') as LastSaleDate,
            DATEDIFF(DAY, COALESCE(sales.LastSaleDate, '1900-01-01'), GETDATE()) as DaysSinceLastSale
        FROM Articulos a
        INNER JOIN Categorias c ON a.IdCategoria = c.IdCategoria
        LEFT JOIN Suppliers s ON CAST(a.proveedor AS VARCHAR(50)) = CAST(s.InternalId AS VARCHAR(50))
        LEFT JOIN (
            SELECT 
                npi.IdArticulo,
                MAX(np.FechaEmision) as LastSaleDate,
                SUM(CASE WHEN np.FechaEmision >= DATEADD(DAY, -30, GETDATE()) THEN npi.Cantidad ELSE 0 END) as Last30DaysSales,
                SUM(CASE WHEN np.FechaEmision >= DATEADD(DAY, -90, GETDATE()) THEN npi.Cantidad ELSE 0 END) as Last90DaysSales,
                SUM(CASE WHEN np.FechaEmision >= DATEADD(DAY, -180, GETDATE()) THEN npi.Cantidad ELSE 0 END) as Last180DaysSales,
                SUM(CASE WHEN np.FechaEmision >= DATEADD(DAY, -365, GETDATE()) THEN npi.Cantidad ELSE 0 END) as Last365DaysSales
            FROM NotaPedido_Items npi
            INNER JOIN NotaPedidos np ON npi.IdNotaPedido = np.IdNotaPedido
            WHERE np.FechaEmision >= DATEADD(YEAR, -2, GETDATE())
            GROUP BY npi.IdArticulo
        ) sales ON a.idArticulo = sales.IdArticulo
        WHERE a.Discontinuado = 0
    ),
    ReorderCalculations AS (
        SELECT 
            *,
            -- Lead time estimation (default 60 days for overseas, can be refined)
            CASE 
                WHEN SupplierCountry = 'China' THEN 60
                WHEN SupplierCountry = 'India' THEN 45
                ELSE 30
            END as EstimatedLeadTimeDays,
            -- Safety stock (1.65 * std dev * sqrt(lead time)) for 95% service level
            CASE 
                WHEN SupplierCountry = 'China' THEN DemandStdDev * SQRT(60.0) * 1.65
                WHEN SupplierCountry = 'India' THEN DemandStdDev * SQRT(45.0) * 1.65
                ELSE DemandStdDev * SQRT(30.0) * 1.65
            END as SafetyStock,
            -- Reorder point calculation
            CASE 
                WHEN SupplierCountry = 'China' THEN (AvgDailyDemand * 60) + (DemandStdDev * SQRT(60.0) * 1.65)
                WHEN SupplierCountry = 'India' THEN (AvgDailyDemand * 45) + (DemandStdDev * SQRT(45.0) * 1.65)
                ELSE (AvgDailyDemand * 30) + (DemandStdDev * SQRT(30.0) * 1.65)
            END as ReorderPoint,
            -- Economic Order Quantity (simplified Wilson formula)
            CASE 
                WHEN AvgDailyDemand > 0 AND UnitPrice > 0 THEN
                    SQRT((2 * AvgDailyDemand * 365 * 100) / (UnitPrice * 0.25))
                ELSE 0
            END as EOQ,
            -- Days of coverage remaining
            CASE 
                WHEN AvgDailyDemand > 0 THEN CurrentStock / AvgDailyDemand
                ELSE 999
            END as DaysOfCoverage
        FROM ProductDemand
    ),
    FinalCalculations AS (
        SELECT 
            *,
            -- Quantity to order
            CASE 
                WHEN CurrentStock < ReorderPoint THEN 
                    CEILING(CASE WHEN EOQ > (ReorderPoint - CurrentStock + SafetyStock) 
                                 THEN EOQ 
                                 ELSE (ReorderPoint - CurrentStock + SafetyStock) 
                            END)
                ELSE 0
            END as SuggestedOrderQuantity,
            -- Priority classification
            CASE 
                WHEN DaysOfCoverage <= 0 THEN 'OUT_OF_STOCK'
                WHEN CurrentStock < ReorderPoint AND DaysOfCoverage <= 15 THEN 'URGENT'
                WHEN CurrentStock < ReorderPoint AND DaysOfCoverage <= 30 THEN 'HIGH'
                WHEN CurrentStock < ReorderPoint AND DaysOfCoverage <= 60 THEN 'MEDIUM'
                WHEN CurrentStock < ReorderPoint THEN 'LOW'
                ELSE 'ADEQUATE'
            END as Priority,
            -- Expected stockout date
            CASE 
                WHEN AvgDailyDemand > 0 AND DaysOfCoverage < 999 THEN 
                    DATEADD(DAY, CAST(DaysOfCoverage AS INT), GETDATE())
                ELSE NULL
            END as ExpectedStockoutDate,
            -- Order value
            CASE 
                WHEN CurrentStock < ReorderPoint THEN 
                    CEILING(CASE WHEN EOQ > (ReorderPoint - CurrentStock + SafetyStock) 
                                 THEN EOQ 
                                 ELSE (ReorderPoint - CurrentStock + SafetyStock) 
                            END) * UnitPrice
                ELSE 0
            END as SuggestedOrderValue
        FROM ReorderCalculations
        WHERE Last90DaysSales > 0  -- Only products with recent demand
    )
    SELECT *
    FROM FinalCalculations
    ORDER BY 
        CASE Priority
            WHEN 'OUT_OF_STOCK' THEN 1
            WHEN 'URGENT' THEN 2
            WHEN 'HIGH' THEN 3
            WHEN 'MEDIUM' THEN 4
            WHEN 'LOW' THEN 5
            ELSE 6
        END,
        DaysOfCoverage ASC
    """
    
    SUPPLIER_PERFORMANCE = """
    WITH SupplierStock AS (
        SELECT 
            s.Id,
            s.Name as SupplierName,
            s.Country,
            s.InternalId,
            COUNT(DISTINCT a.idArticulo) as ProductCount,
            SUM(a.cantidad * a.preciounitario) as CurrentStockValue
        FROM Suppliers s
        LEFT JOIN Articulos a ON CAST(a.proveedor AS VARCHAR(50)) = CAST(s.InternalId AS VARCHAR(50))
            AND a.Discontinuado = 0
        GROUP BY s.Id, s.Name, s.Country, s.InternalId
    ),
    SupplierOrders AS (
        SELECT 
            CAST(po.supplierId AS VARCHAR(50)) as SupplierId,
            COUNT(DISTINCT po.id) as TotalOrders,
            AVG(CASE 
                WHEN po.boardingDate IS NOT NULL AND po.nationalizationDate IS NOT NULL
                AND TRY_CAST(po.boardingDate AS DATE) IS NOT NULL
                AND TRY_CAST(po.nationalizationDate AS DATE) IS NOT NULL
                THEN DATEDIFF(DAY, TRY_CAST(po.boardingDate AS DATE), TRY_CAST(po.nationalizationDate AS DATE))
                ELSE NULL
            END) as AvgLeadTimeDays,
            SUM(po.totalAmount) as TotalPurchaseValue
        FROM PurchaseOrders po
        GROUP BY CAST(po.supplierId AS VARCHAR(50))
    )
    SELECT 
        ss.SupplierName,
        ss.Country,
        COALESCE(so.TotalOrders, 0) as TotalOrders,
        ss.ProductCount,
        COALESCE(ss.CurrentStockValue, 0) as CurrentStockValue,
        so.AvgLeadTimeDays,
        so.TotalPurchaseValue
    FROM SupplierStock ss
    LEFT JOIN SupplierOrders so ON CAST(ss.InternalId AS VARCHAR(50)) = so.SupplierId
    ORDER BY CurrentStockValue DESC
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
    
    XERP_SALES_SUMMARY = """
    SELECT 
        COUNT(*) as TotalTransactions,
        SUM(
            CASE 
                WHEN dt.Type = 10 THEN (total * 1.21)
                WHEN dt.Type = 11 THEN (total * -1.21)
                ELSE 0
            END
        ) as TotalRevenue,
        COUNT(DISTINCT dm.debtor_no) as UniqueCustomers,
        AVG(
            CASE 
                WHEN dt.Type = 10 THEN (total * 1.21)
                ELSE NULL
            END
        ) as AvgInvoiceSize
    FROM [0_debtor_trans] dt
    INNER JOIN [0_sales_orders] so ON so.ID = dt.order_
    INNER JOIN [0_debtors_master] dm ON dm.debtor_no = so.debtor_no
    WHERE dt.Type IN (10, 11)
    AND ord_date >= DATEADD(YEAR, -1, GETDATE())
    AND ord_date > '2020-01-01'
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
    
    # Retool-compatible xERP queries
    XERP_BILLED_MONTHLY = """
    WITH FC AS (
      SELECT COALESCE(SUM(Total) * 1.21, 0) AS BilledMonthlyFC FROM [0_debtor_trans] dt
      INNER JOIN [0_sales_orders] so ON so.ID = dt.order_
      WHERE dt.Type=10 AND MONTH(ord_date) = MONTH(DATEADD(HOUR, -3, GETDATE())) AND YEAR(ord_date) = YEAR(DATEADD(HOUR, -3, GETDATE()))
    ),
    NC AS (
      SELECT COALESCE(SUM(Total) * 1.21, 0) AS BilledMonthlyNC FROM [0_debtor_trans] dt
      INNER JOIN [0_sales_orders] so ON so.ID = dt.order_
      WHERE dt.Type=11 AND MONTH(ord_date) = MONTH(DATEADD(HOUR, -3, GETDATE())) AND YEAR(ord_date) = YEAR(DATEADD(HOUR, -3, GETDATE()))
    )
    SELECT (BilledMonthlyFC - BilledMonthlyNC) AS BilledMonthly
    FROM FC, NC
    """
    
    XERP_BILLED_TODAY = """
    WITH FC AS (
      SELECT COALESCE(SUM(Total) * 1.21, 0) AS BilledTodayFC FROM [0_debtor_trans] dt
      INNER JOIN [0_sales_orders] so ON so.ID = dt.order_
      WHERE dt.Type=10 AND CAST(ord_date AS DATE) = CAST(DATEADD(HOUR, -3, GETDATE()) AS DATE)
    ),
    NC AS (
      SELECT COALESCE(SUM(Total) * 1.21, 0) AS BilledTodayNC FROM [0_debtor_trans] dt
      INNER JOIN [0_sales_orders] so ON so.ID = dt.order_
      WHERE dt.Type=11 AND CAST(ord_date AS DATE) = CAST(DATEADD(HOUR, -3, GETDATE()) AS DATE)
    )
    SELECT (BilledTodayFC - BilledTodayNC) AS BilledToday
    FROM FC, NC
    """
    
    XERP_BILLS = """
    SELECT 
    order_no ,
    ord_date as invoiceDate,
    [name] as customerName,
    dt.Type,
    concat(
      dt.[subtype],
      '-',
      RIGHT('00000000'+ISNULL(dt.[reference],''),8)
      ) as invoiceNumber,
      dm.[debtor_no] as IdCliente,
        (total * 1.21) as totalAmount
    FROM [0_debtor_trans] dt
      INNER JOIN [0_sales_orders] so ON so.ID = dt.order_
      INNER JOIN [0_debtors_master] dm on dm.debtor_no = so.debtor_no
      WHERE dt.Type=10 AND 
        (('{view_filter}' = 'month' AND 
    MONTH(ord_date) = MONTH(DATEADD(HOUR, -3, GETDATE())) AND YEAR(ord_date) = YEAR(DATEADD(HOUR, -3, GETDATE()))) OR
       ('{view_filter}' = 'day' 
    AND CAST(ord_date AS DATE) = CAST(DATEADD(HOUR, -3, GETDATE()) AS DATE)))
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

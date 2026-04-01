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

    # SPISA financial queries (USD currency)
    EXECUTIVE_SUMMARY = """
    SELECT
        COUNT(DISTINCT customer_id) as "UniqueCustomers",
        SUM(amount) as "TotalOutstanding",
        SUM(due) as "TotalOverdue",
        AVG(amount) as "AvgBalance"
    FROM sync_balances
    WHERE amount > 100
    """

    CREDIT_RISK_ANALYSIS = """
    SELECT
        c.name as "Name",
        b.amount as "CurrentBalance",
        b.due as "OverdueAmount",
        (b.due / NULLIF(b.amount, 0)) * 100 as "OverduePercentage",
        CASE
            WHEN b.due > b.amount * 0.5 THEN 'HIGH RISK'
            WHEN b.due > b.amount * 0.2 THEN 'MEDIUM RISK'
            ELSE 'LOW RISK'
        END as "RiskLevel"
    FROM sync_customers c
    INNER JOIN sync_balances b ON c.id = b.customer_id
    WHERE b.amount > 1000
    ORDER BY "OverduePercentage" DESC
    """

    CASH_FLOW_FORECAST = """
    SELECT
        EXTRACT(YEAR FROM payment_date)::int as "Year",
        EXTRACT(MONTH FROM payment_date)::int as "Month",
        SUM(payment_amount) as "ActualPayments",
        SUM(CASE WHEN type = 1 THEN payment_amount ELSE 0 END) as "CashPayments",
        SUM(CASE WHEN type = 0 THEN payment_amount ELSE 0 END) as "ElectronicPayments",
        COUNT(*) as "TransactionCount",
        COUNT(CASE WHEN type = 1 THEN 1 END) as "CashCount",
        COUNT(CASE WHEN type = 0 THEN 1 END) as "ElectronicCount"
    FROM sync_transactions
    WHERE payment_date >= NOW() - INTERVAL '{months} months'
    AND payment_date <= NOW()
    AND payment_date IS NOT NULL AND payment_date > '2020-01-01'
    AND payment_amount > 0  -- Solo pagos reales (excluir registros sin pago)
    GROUP BY EXTRACT(YEAR FROM payment_date)::int, EXTRACT(MONTH FROM payment_date)::int
    ORDER BY "Year", "Month"
    """

    TOP_CUSTOMERS = """
    SELECT
        c.name as "Name",
        c.type as "Type",
        b.amount as "OutstandingBalance",
        b.due as "OverdueAmount",
        (b.due / NULLIF(b.amount, 0)) * 100 as "OverduePercentage"
    FROM sync_customers c
    INNER JOIN sync_balances b ON c.id = b.customer_id
    WHERE b.amount > 100
    ORDER BY b.amount DESC
    LIMIT {limit}
    """

    # Retool-compatible queries
    SPISA_BALANCES = """
    SELECT c.name as "Name", b.amount as "Amount", b.due as "Due", c.type as "Type"
    FROM sync_balances b
    INNER JOIN sync_customers c on c.id = b.customer_id
    WHERE b.amount > 100
    """

    SPISA_FUTURE_PAYMENTS = """
    SELECT COALESCE(Sum(payment_amount),0) as "PaymentAmount"
    FROM sync_transactions t
    WHERE t.type=0 and t.payment_amount<>0 and payment_date >= NOW()
    """

    SPISA_DUE_BALANCE = """
    SELECT Sum(due) as "Due"
    FROM sync_balances b
    """

    SPISA_BILLED_MONTHLY = """
    SELECT Sum(invoice_amount) as "InvoiceAmount"
    FROM sync_transactions t
    WHERE EXTRACT(MONTH FROM invoice_date)::int = EXTRACT(MONTH FROM NOW())::int
    AND EXTRACT(YEAR FROM invoice_date)::int = EXTRACT(YEAR FROM NOW())::int
    AND type=1
    """

    SPISA_BILLED_TODAY = """
    SELECT COALESCE(Sum(invoice_amount),0) as "InvoiceAmount"
    FROM sync_transactions t
    WHERE invoice_date::date = NOW()::date
    AND type=1
    """

    SPISA_COLLECTED_MONTHLY = """
    SELECT
        COALESCE(SUM(payment_amount), 0) as "TotalPayments",
        COALESCE(SUM(CASE WHEN type = 1 THEN payment_amount ELSE 0 END), 0) as "CashPayments",
        COALESCE(SUM(CASE WHEN type = 0 THEN payment_amount ELSE 0 END), 0) as "ElectronicPayments",
        COUNT(*) as "TransactionCount",
        COUNT(CASE WHEN type = 1 THEN 1 END) as "CashCount",
        COUNT(CASE WHEN type = 0 THEN 1 END) as "ElectronicCount"
    FROM sync_transactions t
    WHERE EXTRACT(MONTH FROM payment_date)::int = EXTRACT(MONTH FROM NOW())::int
    AND EXTRACT(YEAR FROM payment_date)::int = EXTRACT(YEAR FROM NOW())::int
    AND payment_date IS NOT NULL AND payment_date > '2020-01-01'
    AND payment_amount > 0  -- Solo pagos reales
    """

    CUSTOMER_PROFITABILITY = """
    WITH CustomerMetrics AS (
        SELECT
            c.name as "Name",
            COUNT(DISTINCT t.id) as "TransactionCount",
            SUM(CASE WHEN t.type = 1 THEN t.invoice_amount ELSE 0 END) as "TotalRevenue",
            SUM(CASE WHEN t.type = 0 THEN t.payment_amount ELSE 0 END) as "TotalPayments",
            AVG(t.invoice_amount) as "AvgInvoiceSize",
            EXTRACT(EPOCH FROM (MAX(t.invoice_date) - MIN(t.invoice_date))) / 86400 as "CustomerLifespanDays",
            b.amount as "CurrentBalance",
            b.due as "OverdueAmount"
        FROM sync_customers c
        INNER JOIN sync_transactions t ON c.id = t.customer_id
        LEFT JOIN sync_balances b ON c.id = b.customer_id
        WHERE t.invoice_date >= '2020-01-01'
        GROUP BY c.id, c.name, b.amount, b.due
    )
    SELECT
        *,
        "TotalRevenue" / NULLIF("CustomerLifespanDays", 0) * 365 as "AnnualizedRevenue",
        CASE
            WHEN "TotalRevenue" > 1000000 AND "OverdueAmount" < "TotalRevenue" * 0.1 THEN 'Premium'
            WHEN "TotalRevenue" > 500000 AND "OverdueAmount" < "TotalRevenue" * 0.2 THEN 'Gold'
            WHEN "TotalRevenue" > 100000 THEN 'Silver'
            ELSE 'Bronze'
        END as "CustomerTier"
    FROM CustomerMetrics
    ORDER BY "TotalRevenue" DESC
    """

    # Expected Collections based on invoice aging (xERP)
    XERP_EXPECTED_COLLECTIONS = """
    WITH AgingBuckets AS (
        SELECT
            dt.trans_no,
            dt.debtor_no,
            dm.name as CustomerName,
            dt.ov_amount * 1.21 as InvoiceAmount,
            (dt.ov_amount - dt.alloc) * 1.21 as OutstandingAmount,
            dt.due_date as DueDate,
            DATEDIFF(DAY, DATEADD(HOUR, -3, GETDATE()), dt.due_date) as DaysUntilDue,
            CASE
                WHEN DATEDIFF(DAY, DATEADD(HOUR, -3, GETDATE()), dt.due_date) > 0 THEN 'NotYetDue'
                WHEN DATEDIFF(DAY, dt.due_date, DATEADD(HOUR, -3, GETDATE())) BETWEEN 0 AND 30 THEN 'Overdue_0_30'
                WHEN DATEDIFF(DAY, dt.due_date, DATEADD(HOUR, -3, GETDATE())) BETWEEN 31 AND 60 THEN 'Overdue_31_60'
                WHEN DATEDIFF(DAY, dt.due_date, DATEADD(HOUR, -3, GETDATE())) BETWEEN 61 AND 90 THEN 'Overdue_61_90'
                ELSE 'Overdue_90_Plus'
            END as AgingBucket
        FROM [0_debtor_trans] dt
        INNER JOIN [0_debtors_master] dm ON dt.debtor_no = dm.debtor_no
        WHERE dt.Type = 10  -- Invoices
        AND dt.ov_amount > 0
        AND dt.alloc < dt.ov_amount  -- Not fully paid
    )
    SELECT
        AgingBucket,
        COUNT(*) as InvoiceCount,
        SUM(OutstandingAmount) as TotalAmount,
        AVG(OutstandingAmount) as AvgAmount,
        MIN(DaysUntilDue) as MinDays,
        MAX(DaysUntilDue) as MaxDays
    FROM AgingBuckets
    GROUP BY AgingBucket
    ORDER BY
        CASE AgingBucket
            WHEN 'NotYetDue' THEN 1
            WHEN 'Overdue_0_30' THEN 2
            WHEN 'Overdue_31_60' THEN 3
            WHEN 'Overdue_61_90' THEN 4
            WHEN 'Overdue_90_Plus' THEN 5
        END
    """

    # Collection Performance - Using allocations table (xERP)
    XERP_COLLECTION_PERFORMANCE = """
    WITH InvoicePayments AS (
        SELECT
            inv.trans_no as InvoiceNo,
            YEAR(inv.tran_date) as Year,
            MONTH(inv.tran_date) as Month,
            inv.debtor_no,
            inv.ov_amount * 1.21 as InvoiceAmount,
            inv.alloc * 1.21 as AllocatedAmount,
            inv.due_date,
            inv.tran_date as InvoiceDate,
            -- First payment date from allocations
            (
                SELECT MIN(alloc.date_alloc)
                FROM [0_cust_allocations] alloc
                WHERE alloc.trans_type_to = 10
                AND alloc.trans_no_to = inv.trans_no
            ) as FirstPaymentDate,
            -- Check if fully paid
            CASE WHEN inv.alloc >= inv.ov_amount THEN 1 ELSE 0 END as IsFullyPaid
        FROM [0_debtor_trans] inv
        WHERE inv.Type = 10  -- Invoices only
        AND inv.tran_date >= DATEADD(MONTH, -12, DATEADD(HOUR, -3, GETDATE()))
        AND inv.tran_date <= DATEADD(HOUR, -3, GETDATE())
        AND inv.ov_amount > 0
    )
    SELECT
        Year,
        Month,
        SUM(InvoiceAmount) as MonthlySales,
        SUM(InvoiceAmount - AllocatedAmount) as OutstandingAmount,
        COUNT(*) as TotalInvoices,
        SUM(IsFullyPaid) as InvoicesPaid,
        -- Invoices paid within 30 days of due date
        SUM(CASE
            WHEN FirstPaymentDate IS NOT NULL
            AND DATEDIFF(DAY, due_date, FirstPaymentDate) <= 30
            THEN 1
            ELSE 0
        END) as InvoicesPaidOnTime,
        -- Average days from due date to first payment
        AVG(CASE
            WHEN FirstPaymentDate IS NOT NULL
            THEN DATEDIFF(DAY, due_date, FirstPaymentDate)
            ELSE NULL
        END) as AvgDaysToPayment,
        -- DSO: (Outstanding / Monthly Sales) * 30 days
        CASE
            WHEN SUM(InvoiceAmount) > 0
            THEN (SUM(InvoiceAmount - AllocatedAmount) / SUM(InvoiceAmount)) * 30
            ELSE 0
        END as DSO,
        -- On-time payment percentage (all invoices with payment activity)
        CASE
            WHEN COUNT(*) > 0
            THEN (CAST(SUM(CASE
                WHEN FirstPaymentDate IS NOT NULL
                AND DATEDIFF(DAY, due_date, FirstPaymentDate) <= 30
                THEN 1
                ELSE 0
            END) AS FLOAT) / NULLIF(SUM(CASE WHEN FirstPaymentDate IS NOT NULL THEN 1 ELSE 0 END), 0)) * 100
            ELSE 0
        END as OnTimePaymentPercentage
    FROM InvoicePayments
    GROUP BY Year, Month
    ORDER BY Year DESC, Month DESC
    """

class InventoryQueries:
    """Inventory analysis SQL queries"""

    INVENTORY_SUMMARY = """
    SELECT
        COUNT(*) as "TotalProducts",
        SUM(a.stock) as "TotalQuantity",
        SUM(a.stock * a.unit_price) as "TotalValue",
        COUNT(CASE WHEN a.stock > 0 THEN 1 END) as "InStockProducts",
        COUNT(CASE WHEN a.is_discontinued = true THEN 1 END) as "DiscontinuedProducts"
    FROM articles a
    WHERE a.deleted_at IS NULL
    """

    TOP_STOCK_VALUE = """
    SELECT
        a.description as "ProductName",
        a.stock as "CurrentStock",
        a.unit_price as "UnitPrice",
        a.stock * a.unit_price as "StockValue",
        c.name as "Category"
    FROM articles a
    INNER JOIN categories c ON a.category_id = c.id
    WHERE a.stock > 0
    AND a.deleted_at IS NULL
    AND c.deleted_at IS NULL
    ORDER BY "StockValue" DESC
    LIMIT {limit}
    """

    SLOW_MOVING_ANALYSIS = """
    WITH InventoryAnalysis AS (
        SELECT
            a.description as "ProductName",
            a.stock as "CurrentStock",
            a.unit_price * a.stock as "StockValue",
            c.name as "Category",
            COALESCE(sales."LastSaleDate", '1900-01-01'::date) as "LastSaleDate",
            COALESCE(sales."TotalSold", 0) as "TotalSold",
            EXTRACT(EPOCH FROM (NOW() - COALESCE(sales."LastSaleDate", '1900-01-01'::date))) / 86400 as "DaysSinceLastSale"
        FROM articles a
        INNER JOIN categories c ON a.category_id = c.id
        LEFT JOIN (
            SELECT
                soi.article_id,
                MAX(so.order_date) as "LastSaleDate",
                SUM(soi.quantity) as "TotalSold"
            FROM sales_order_items soi
            INNER JOIN sales_orders so ON soi.sales_order_id = so.id
            WHERE so.order_date >= NOW() - INTERVAL '2 years'
            AND so.deleted_at IS NULL
            GROUP BY soi.article_id
        ) sales ON a.id = sales.article_id
        WHERE a.stock > 0 AND a.is_discontinued = false
        AND a.deleted_at IS NULL
        AND c.deleted_at IS NULL
    )
    SELECT
        *,
        CASE
            WHEN "DaysSinceLastSale" > 365 THEN 'Dead Stock'
            WHEN "DaysSinceLastSale" > 180 THEN 'Slow Moving'
            WHEN "DaysSinceLastSale" > 90 THEN 'Moderate'
            ELSE 'Fast Moving'
        END as "StockCategory",
        "StockValue" * 0.02 as "MonthlyCarryingCost"
    FROM InventoryAnalysis
    ORDER BY "StockValue" DESC
    """

    CATEGORY_ANALYSIS = """
    SELECT
        c.name as "Category",
        COUNT(a.id) as "ProductCount",
        SUM(a.stock) as "TotalQuantity",
        SUM(a.stock * a.unit_price) as "TotalValue",
        AVG(a.unit_price) as "AvgUnitPrice"
    FROM categories c
    LEFT JOIN articles a ON c.id = a.category_id AND a.deleted_at IS NULL
    WHERE a.stock > 0 AND a.is_discontinued = false
    AND c.deleted_at IS NULL
    GROUP BY c.id, c.name
    ORDER BY "TotalValue" DESC
    """

    STOCK_VARIATION_OVER_TIME = """
    WITH MonthlyStockMovement AS (
        SELECT
            a.id as "Id",
            a.description as "ProductName",
            c.name as "Category",
            a.stock as "CurrentStock",
            a.unit_price as "UnitPrice",
            EXTRACT(YEAR FROM so.order_date)::int as "Year",
            EXTRACT(MONTH FROM so.order_date)::int as "Month",
            TO_CHAR(so.order_date, 'Month') as "MonthName",
            SUM(soi.quantity) as "QuantitySold",
            COUNT(soi.sales_order_id) as "OrderCount",
            AVG(soi.quantity) as "AvgOrderSize",
            SUM(soi.quantity * a.unit_price) as "SalesValue"
        FROM articles a
        INNER JOIN categories c ON a.category_id = c.id
        LEFT JOIN sales_order_items soi ON a.id = soi.article_id
        LEFT JOIN sales_orders so ON soi.sales_order_id = so.id
        WHERE so.order_date >= NOW() - INTERVAL '12 months'
        AND so.order_date > '2020-01-01'
        AND a.is_discontinued = false
        AND a.deleted_at IS NULL
        AND c.deleted_at IS NULL
        AND so.deleted_at IS NULL
        GROUP BY a.id, a.description, c.name, a.stock, a.unit_price,
                 EXTRACT(YEAR FROM so.order_date)::int, EXTRACT(MONTH FROM so.order_date)::int, TO_CHAR(so.order_date, 'Month')
    ),
    StockTurnoverAnalysis AS (
        SELECT
            *,
            -- Calculate stock turnover rate (monthly sales / current stock)
            CASE
                WHEN "CurrentStock" > 0 THEN "QuantitySold" / NULLIF("CurrentStock", 0)
                ELSE 0
            END as "TurnoverRate",
            -- Calculate days of stock remaining
            CASE
                WHEN "QuantitySold" > 0 THEN ("CurrentStock" / NULLIF("QuantitySold", 0)) * 30
                ELSE 999
            END as "DaysOfStockRemaining",
            -- Calculate velocity category
            CASE
                WHEN "QuantitySold" = 0 THEN 'No Movement'
                WHEN ("QuantitySold" / NULLIF("CurrentStock", 0)) >= 0.5 THEN 'High Velocity'
                WHEN ("QuantitySold" / NULLIF("CurrentStock", 0)) >= 0.2 THEN 'Medium Velocity'
                WHEN ("QuantitySold" / NULLIF("CurrentStock", 0)) >= 0.1 THEN 'Low Velocity'
                ELSE 'Very Low Velocity'
            END as "VelocityCategory"
        FROM MonthlyStockMovement
    )
    SELECT
        *,
        -- Add financial impact metrics
        "CurrentStock" * "UnitPrice" as "StockValue",
        "SalesValue" as "MonthlySalesValue",
        ("CurrentStock" * "UnitPrice") * 0.02 as "MonthlyCarryingCost",
        -- Add reorder recommendations
        CASE
            WHEN "DaysOfStockRemaining" < 30 AND "QuantitySold" > 0 THEN 'URGENT REORDER'
            WHEN "DaysOfStockRemaining" < 60 AND "QuantitySold" > 0 THEN 'REORDER SOON'
            WHEN "DaysOfStockRemaining" > 180 THEN 'OVERSTOCK RISK'
            ELSE 'NORMAL'
        END as "StockStatus"
    FROM StockTurnoverAnalysis
    ORDER BY "Year" DESC, "Month" DESC, "SalesValue" DESC
    """

    STOCK_VELOCITY_SUMMARY = """
    WITH VelocityAnalysis AS (
        SELECT
            a.id as "Id",
            a.description as "ProductName",
            c.name as "Category",
            a.stock as "CurrentStock",
            a.unit_price as "UnitPrice",
            -- Last 3 months sales
            COALESCE(SUM(CASE WHEN so.order_date >= NOW() - INTERVAL '3 months' THEN soi.quantity END), 0) as "Last3MonthsSales",
            -- Last 6 months sales
            COALESCE(SUM(CASE WHEN so.order_date >= NOW() - INTERVAL '6 months' THEN soi.quantity END), 0) as "Last6MonthsSales",
            -- Last 12 months sales
            COALESCE(SUM(CASE WHEN so.order_date >= NOW() - INTERVAL '12 months' THEN soi.quantity END), 0) as "Last12MonthsSales",
            -- Average monthly sales
            COALESCE(SUM(soi.quantity) / NULLIF(EXTRACT(EPOCH FROM (NOW() - MIN(so.order_date))) / 2592000, 0), 0) as "AvgMonthlySales",
            -- Last sale date
            MAX(so.order_date) as "LastSaleDate"
        FROM articles a
        INNER JOIN categories c ON a.category_id = c.id
        LEFT JOIN sales_order_items soi ON a.id = soi.article_id
        LEFT JOIN sales_orders so ON soi.sales_order_id = so.id AND so.deleted_at IS NULL
        WHERE a.is_discontinued = false
        AND a.deleted_at IS NULL
        AND c.deleted_at IS NULL
        AND (so.order_date IS NULL OR (so.order_date >= NOW() - INTERVAL '2 years' AND so.order_date <= NOW()))
        GROUP BY a.id, a.description, c.name, a.stock, a.unit_price
    )
    SELECT
        *,
        -- Stock turnover metrics
        CASE
            WHEN "CurrentStock" > 0 AND "AvgMonthlySales" > 0 THEN "CurrentStock" / "AvgMonthlySales"
            ELSE 999
        END as "MonthsOfStock",

        CASE
            WHEN "AvgMonthlySales" > 0 THEN ("Last12MonthsSales" / 12.0) / NULLIF("CurrentStock", 0) * 100
            ELSE 0
        END as "AnnualTurnoverPercentage",

        -- Trend analysis (comparing recent vs historical performance)
        CASE
            WHEN "Last6MonthsSales" > 0 AND "Last12MonthsSales" > 0 THEN
                (("Last3MonthsSales" / 3.0) - (("Last12MonthsSales" - "Last3MonthsSales") / 9.0)) /
                NULLIF((("Last12MonthsSales" - "Last3MonthsSales") / 9.0), 0) * 100
            ELSE 0
        END as "TrendPercentage",

        -- Stock health classification
        CASE
            WHEN "CurrentStock" = 0 THEN 'OUT_OF_STOCK'
            WHEN "AvgMonthlySales" = 0 AND "CurrentStock" > 0 THEN 'DEAD_STOCK'
            WHEN "CurrentStock" / NULLIF("AvgMonthlySales", 0) < 1 THEN 'LOW_STOCK'
            WHEN "CurrentStock" / NULLIF("AvgMonthlySales", 0) > 6 THEN 'OVERSTOCK'
            ELSE 'HEALTHY'
        END as "StockHealthStatus",

        -- Financial metrics
        "CurrentStock" * "UnitPrice" as "StockValue",
        "Last12MonthsSales" * "UnitPrice" as "AnnualSalesValue",
        ("CurrentStock" * "UnitPrice") * 0.02 as "MonthlyCarryingCost"

    FROM VelocityAnalysis
    WHERE "CurrentStock" >= 0
    ORDER BY "AnnualSalesValue" DESC, "StockValue" DESC
    """

    STOCK_VALUE_EVOLUTION = """
    SELECT
        date as "Date",
        stock_value as "StockValue",
        EXTRACT(YEAR FROM date)::int as "Year",
        EXTRACT(MONTH FROM date)::int as "Month",
        TO_CHAR(date, 'Month') as "MonthName"
    FROM stock_snapshots
    WHERE date >= NOW() - INTERVAL '{months} months'
    ORDER BY date ASC
    """

    OUT_OF_STOCK_ANALYSIS = """
    WITH OutOfStockAnalysis AS (
        SELECT
            a.id as "Id",
            a.description as "ProductName",
            a.unit_price as "UnitPrice",
            c.name as "Category",
            a.is_discontinued as "IsDiscontinued",
            COALESCE(sales."LastSaleDate", '1900-01-01'::date) as "LastSaleDate",
            COALESCE(sales."TotalSold", 0) as "TotalSold",
            COALESCE(sales."Last90DaysSales", 0) as "Last90DaysSales",
            COALESCE(sales."Last180DaysSales", 0) as "Last180DaysSales",
            COALESCE(sales."Last365DaysSales", 0) as "Last365DaysSales",
            EXTRACT(EPOCH FROM (NOW() - COALESCE(sales."LastSaleDate", '1900-01-01'::date))) / 86400 as "DaysSinceLastSale",
            -- Estimate lost sales (average daily sales * days out of stock, capped at 90 days)
            CASE
                WHEN sales."Last90DaysSales" > 0 THEN
                    (sales."Last90DaysSales" / 90.0) *
                    CASE WHEN EXTRACT(EPOCH FROM (NOW() - sales."LastSaleDate")) / 86400 > 90
                         THEN 90
                         ELSE EXTRACT(EPOCH FROM (NOW() - sales."LastSaleDate")) / 86400
                    END * a.unit_price
                ELSE 0
            END as "EstimatedLostSales"
        FROM articles a
        INNER JOIN categories c ON a.category_id = c.id
        LEFT JOIN (
            SELECT
                soi.article_id,
                MAX(so.order_date) as "LastSaleDate",
                SUM(soi.quantity) as "TotalSold",
                SUM(CASE WHEN so.order_date >= NOW() - INTERVAL '90 days' THEN soi.quantity ELSE 0 END) as "Last90DaysSales",
                SUM(CASE WHEN so.order_date >= NOW() - INTERVAL '180 days' THEN soi.quantity ELSE 0 END) as "Last180DaysSales",
                SUM(CASE WHEN so.order_date >= NOW() - INTERVAL '365 days' THEN soi.quantity ELSE 0 END) as "Last365DaysSales"
            FROM sales_order_items soi
            INNER JOIN sales_orders so ON soi.sales_order_id = so.id
            WHERE so.order_date >= NOW() - INTERVAL '2 years'
            AND so.deleted_at IS NULL
            GROUP BY soi.article_id
        ) sales ON a.id = sales.article_id
        WHERE a.stock = 0  -- Out of stock
        AND a.deleted_at IS NULL
        AND c.deleted_at IS NULL
    )
    SELECT
        *,
        CASE
            WHEN "IsDiscontinued" = true THEN 'Discontinued'
            WHEN "DaysSinceLastSale" > 365 OR "LastSaleDate" = '1900-01-01'::date THEN 'Dead Stock'
            WHEN "DaysSinceLastSale" > 180 THEN 'Slow Moving'
            WHEN "DaysSinceLastSale" > 90 THEN 'Moderate'
            ELSE 'Healthy'
        END as "StockProfile",
        CASE
            WHEN "IsDiscontinued" = true THEN 'No Action'
            WHEN "DaysSinceLastSale" > 365 OR "LastSaleDate" = '1900-01-01'::date THEN 'Consider Discontinuing'
            WHEN "DaysSinceLastSale" > 180 THEN 'Low Priority Reorder'
            WHEN "DaysSinceLastSale" > 90 THEN 'Monitor & Reorder if Needed'
            ELSE 'URGENT REORDER'
        END as "RecommendedAction",
        CASE
            WHEN "IsDiscontinued" = true THEN 0
            WHEN "Last90DaysSales" > 0 THEN 4  -- Critical
            WHEN "Last180DaysSales" > 0 THEN 3  -- High
            WHEN "Last365DaysSales" > 0 THEN 2  -- Medium
            ELSE 1  -- Low
        END as "Priority"
    FROM OutOfStockAnalysis
    ORDER BY "Priority" DESC, "EstimatedLostSales" DESC
    """

class PurchaseQueries:
    """Purchase order and supplier analysis SQL queries"""

    REORDER_ANALYSIS = """
    -- ABC Classification based on revenue contribution (last 365 days)
    WITH ProductRevenue AS (
        SELECT
            a.id,
            SUM(soi.quantity) * a.unit_price as "TotalRevenue"
        FROM articles a
        INNER JOIN sales_order_items soi ON a.id = soi.article_id
        INNER JOIN sales_orders so ON soi.sales_order_id = so.id
        WHERE so.order_date >= NOW() - INTERVAL '1 year'
        AND so.deleted_at IS NULL
        AND a.deleted_at IS NULL
        GROUP BY a.id, a.unit_price
    ),
    ABCClassification AS (
        SELECT
            id,
            "TotalRevenue",
            SUM("TotalRevenue") OVER (ORDER BY "TotalRevenue" DESC) * 100.0 /
                SUM("TotalRevenue") OVER () as "CumulativeRevenuePercent",
            CASE
                WHEN SUM("TotalRevenue") OVER (ORDER BY "TotalRevenue" DESC) * 100.0 /
                     SUM("TotalRevenue") OVER () <= 80 THEN 'A'
                WHEN SUM("TotalRevenue") OVER (ORDER BY "TotalRevenue" DESC) * 100.0 /
                     SUM("TotalRevenue") OVER () <= 95 THEN 'B'
                ELSE 'C'
            END as "ABCClass"
        FROM ProductRevenue
    ),
    ProductDemand AS (
        SELECT
            a.id,
            a.code as "ProductCode",
            a.description as "ProductName",
            a.stock as "CurrentStock",
            a.unit_price as "UnitPrice",
            a.stock * a.unit_price as "StockValue",
            c.name as "Category",
            s.name as "PreferredSupplier",
            a.supplier_id as "SupplierId",
            COALESCE(abc."ABCClass", 'C') as "ABCClass",
            COALESCE(abc."TotalRevenue", 0) as "AnnualRevenue",
            -- Demand calculations
            COALESCE(sales."Last30DaysSales", 0) as "Last30DaysSales",
            COALESCE(sales."Last90DaysSales", 0) as "Last90DaysSales",
            COALESCE(sales."Last180DaysSales", 0) as "Last180DaysSales",
            COALESCE(sales."Last365DaysSales", 0) as "Last365DaysSales",
            COALESCE(sales."DemandWindowSales", 0) as "DemandWindowSales",
            -- Average daily demand (based on user-selected window)
            COALESCE(sales."DemandWindowSales", 0) / {demand_days}.0 as "AvgDailyDemand",
            -- Standard deviation estimate (simplified)
            CASE
                WHEN sales."Last90DaysSales" > 0 THEN
                    SQRT(COALESCE(sales."Last90DaysSales", 0) / 90.0) * 1.5
                ELSE 0
            END as "DemandStdDev",
            COALESCE(sales."LastSaleDate", '1900-01-01'::date) as "LastSaleDate",
            EXTRACT(EPOCH FROM (NOW() - COALESCE(sales."LastSaleDate", '1900-01-01'::date))) / 86400 as "DaysSinceLastSale",
            {demand_days} as "DemandWindowDays"
        FROM articles a
        INNER JOIN categories c ON a.category_id = c.id
        LEFT JOIN suppliers s ON a.supplier_id = s.id
        LEFT JOIN ABCClassification abc ON a.id = abc.id
        LEFT JOIN (
            SELECT
                soi.article_id,
                MAX(so.order_date) as "LastSaleDate",
                SUM(CASE WHEN so.order_date >= NOW() - INTERVAL '30 days' THEN soi.quantity ELSE 0 END) as "Last30DaysSales",
                SUM(CASE WHEN so.order_date >= NOW() - INTERVAL '90 days' THEN soi.quantity ELSE 0 END) as "Last90DaysSales",
                SUM(CASE WHEN so.order_date >= NOW() - INTERVAL '180 days' THEN soi.quantity ELSE 0 END) as "Last180DaysSales",
                SUM(CASE WHEN so.order_date >= NOW() - INTERVAL '365 days' THEN soi.quantity ELSE 0 END) as "Last365DaysSales",
                SUM(CASE WHEN so.order_date >= NOW() - INTERVAL '{demand_days} days' THEN soi.quantity ELSE 0 END) as "DemandWindowSales"
            FROM sales_order_items soi
            INNER JOIN sales_orders so ON soi.sales_order_id = so.id
            WHERE so.order_date >= NOW() - INTERVAL '2 years'
            AND so.deleted_at IS NULL
            GROUP BY soi.article_id
        ) sales ON a.id = sales.article_id
        WHERE a.is_discontinued = false
        AND a.deleted_at IS NULL
        AND c.deleted_at IS NULL
    ),
    ReorderCalculations AS (
        SELECT
            *,
            -- Lead time: FIXED at 135 days (90 production + 45 shipping)
            135 as "EstimatedLeadTimeDays",

            -- Safety stock adjusted by ABC class
            -- A: 95% SL (Z=1.65), B: 90% SL (Z=1.28), C: 80% SL (Z=0.84)
            CASE
                WHEN "ABCClass" = 'A' THEN "DemandStdDev" * SQRT(135.0) * 1.65
                WHEN "ABCClass" = 'B' THEN "DemandStdDev" * SQRT(135.0) * 1.28
                ELSE "DemandStdDev" * SQRT(135.0) * 0.84
            END as "SafetyStock",

            -- Reorder point = (Avg Daily Demand x Lead Time) + Safety Stock
            ("AvgDailyDemand" * 135) +
            CASE
                WHEN "ABCClass" = 'A' THEN "DemandStdDev" * SQRT(135.0) * 1.65
                WHEN "ABCClass" = 'B' THEN "DemandStdDev" * SQRT(135.0) * 1.28
                ELSE "DemandStdDev" * SQRT(135.0) * 0.84
            END as "ReorderPoint",

            -- Order quantity adjusted by ABC class (coverage multipliers)
            -- A: 2x lead time, B: 1.5x lead time, C: 1.2x lead time
            CASE
                WHEN "ABCClass" = 'A' THEN "AvgDailyDemand" * 135 * 2.0
                WHEN "ABCClass" = 'B' THEN "AvgDailyDemand" * 135 * 1.5
                ELSE "AvgDailyDemand" * 135 * 1.2
            END as "OptimalOrderQuantity",
            -- Days of coverage remaining
            CASE
                WHEN "AvgDailyDemand" > 0 THEN "CurrentStock" / "AvgDailyDemand"
                ELSE 999
            END as "DaysOfCoverage"
        FROM ProductDemand
    ),
    FinalCalculations AS (
        SELECT
            *,
            -- Quantity to order (gap to reorder point + optimal order quantity)
            CASE
                WHEN "CurrentStock" < "ReorderPoint" THEN
                    CEILING(CASE WHEN "OptimalOrderQuantity" > ("ReorderPoint" - "CurrentStock" + "SafetyStock")
                                 THEN "OptimalOrderQuantity"
                                 ELSE ("ReorderPoint" - "CurrentStock" + "SafetyStock")
                            END)
                ELSE 0
            END as "SuggestedOrderQuantity",

            -- Calculate coverage percentage relative to demand window
            CASE
                WHEN "DaysOfCoverage" < 999 THEN ("DaysOfCoverage" / {demand_days}.0) * 100
                ELSE 999
            END as "CoveragePercent",

            -- Priority classification based on PERCENTAGE of coverage vs demand window
            -- CRITICAL: < 20% | URGENT: < 40% | HIGH: < 60% | MEDIUM: < 100% | LOW: < 150%
            CASE
                WHEN "DaysOfCoverage" <= 0 THEN 'OUT_OF_STOCK'
                WHEN "DaysOfCoverage" < 999 AND ("DaysOfCoverage" / {demand_days}.0) * 100 < 20 THEN 'CRITICAL'
                WHEN "DaysOfCoverage" < 999 AND ("DaysOfCoverage" / {demand_days}.0) * 100 < 40 THEN 'URGENT'
                WHEN "DaysOfCoverage" < 999 AND ("DaysOfCoverage" / {demand_days}.0) * 100 < 60 THEN 'HIGH'
                WHEN "DaysOfCoverage" < 999 AND ("DaysOfCoverage" / {demand_days}.0) * 100 < 100 THEN 'MEDIUM'
                WHEN "DaysOfCoverage" < 999 AND ("DaysOfCoverage" / {demand_days}.0) * 100 < 150 THEN 'LOW'
                ELSE 'ADEQUATE'
            END as "Priority",
            -- Expected stockout date
            CASE
                WHEN "AvgDailyDemand" > 0 AND "DaysOfCoverage" < 999 THEN
                    NOW() + ("DaysOfCoverage"::int || ' days')::interval
                ELSE NULL
            END as "ExpectedStockoutDate",
            -- Order value
            CASE
                WHEN "CurrentStock" < "ReorderPoint" THEN
                    CEILING(CASE WHEN "OptimalOrderQuantity" > ("ReorderPoint" - "CurrentStock" + "SafetyStock")
                                 THEN "OptimalOrderQuantity"
                                 ELSE ("ReorderPoint" - "CurrentStock" + "SafetyStock")
                            END) * "UnitPrice"
                ELSE 0
            END as "SuggestedOrderValue"
        FROM ReorderCalculations
        WHERE "DemandWindowSales" > 0  -- Only products with recent demand in selected window
    )
    SELECT *
    FROM FinalCalculations
    ORDER BY
        CASE "Priority"
            WHEN 'OUT_OF_STOCK' THEN 1
            WHEN 'CRITICAL' THEN 2
            WHEN 'URGENT' THEN 3
            WHEN 'HIGH' THEN 4
            WHEN 'MEDIUM' THEN 5
            WHEN 'LOW' THEN 6
            ELSE 7
        END,
        -- Secondary sort: A products first, then by revenue impact
        CASE "ABCClass"
            WHEN 'A' THEN 1
            WHEN 'B' THEN 2
            ELSE 3
        END,
        "SuggestedOrderValue" DESC
    """

    SUPPLIER_PERFORMANCE = """
    WITH SupplierStock AS (
        SELECT
            s.id,
            s.name as "SupplierName",
            s.code,
            COUNT(DISTINCT a.id) as "ProductCount",
            SUM(a.stock * a.unit_price) as "CurrentStockValue"
        FROM suppliers s
        LEFT JOIN articles a ON a.supplier_id = s.id
            AND a.is_discontinued = false
            AND a.deleted_at IS NULL
        GROUP BY s.id, s.name, s.code
    ),
    SupplierOrders AS (
        SELECT
            so.supplier_id::text as "SupplierId",
            COUNT(DISTINCT so.id) as "TotalOrders",
            SUM(soi.quantity * soi.unit_price) as "TotalPurchaseValue"
        FROM supplier_orders so
        LEFT JOIN supplier_order_items soi ON so.id = soi.supplier_order_id
        GROUP BY so.supplier_id::text
    )
    SELECT
        ss."SupplierName",
        COALESCE(sord."TotalOrders", 0) as "TotalOrders",
        ss."ProductCount",
        COALESCE(ss."CurrentStockValue", 0) as "CurrentStockValue",
        sord."TotalPurchaseValue"
    FROM SupplierStock ss
    LEFT JOIN SupplierOrders sord ON ss.code::text = sord."SupplierId"
    ORDER BY "CurrentStockValue" DESC
    """

class SalesQueries:
    """Sales analysis SQL queries"""

    SALES_SUMMARY = """
    SELECT
        COUNT(*) as "TotalTransactions",
        SUM(CASE WHEN type = 1 THEN invoice_amount ELSE 0 END) as "TotalRevenue",
        COUNT(DISTINCT customer_id) as "UniqueCustomers",
        AVG(CASE WHEN type = 1 THEN invoice_amount ELSE NULL END) as "AvgInvoiceSize"
    FROM sync_transactions
    WHERE invoice_date >= NOW() - INTERVAL '1 year'
    AND invoice_date > '2020-01-01'
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
            EXTRACT(YEAR FROM invoice_date)::int as "Year",
            EXTRACT(MONTH FROM invoice_date)::int as "Month",
            TO_CHAR(invoice_date, 'Month') as "MonthName",
            SUM(invoice_amount) as "MonthlyRevenue",
            COUNT(DISTINCT customer_id) as "UniqueCustomers",
            COUNT(*) as "TransactionCount"
        FROM sync_transactions
        WHERE type = 1 AND invoice_date >= NOW() - INTERVAL '2 years'
        AND invoice_date > '2020-01-01'
        GROUP BY EXTRACT(YEAR FROM invoice_date)::int, EXTRACT(MONTH FROM invoice_date)::int, TO_CHAR(invoice_date, 'Month')
    )
    SELECT
        *,
        LAG("MonthlyRevenue") OVER (ORDER BY "Year", "Month") as "PreviousMonth",
        ("MonthlyRevenue" - LAG("MonthlyRevenue") OVER (ORDER BY "Year", "Month")) /
        NULLIF(LAG("MonthlyRevenue") OVER (ORDER BY "Year", "Month"), 0) * 100 as "MonthOverMonthGrowth"
    FROM MonthlySales
    ORDER BY "Year" DESC, "Month" DESC
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
        'SPISA' as "System",
        COUNT(*) as "CustomerCount",
        SUM(amount) as "TotalOutstanding"
    FROM sync_balances
    WHERE amount > 0
    """

    XERP_COMPARISON = """
    SELECT
        'xERP' as System,
        COUNT(DISTINCT debtor_no) as CustomerCount,
        SUM(ov_amount) as TotalOutstanding
    FROM xERP.dbo.[0_debtor_trans]
    WHERE type = 10
    """

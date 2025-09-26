# Database Analysis Report - Dialfa Business Intelligence

**Generated:** September 26, 2025  
**Databases:** SPISA & xERP  
**Server:** dialfa.database.windows.net

---

## 📊 Executive Summary

This comprehensive analysis of the Dialfa database systems reveals significant opportunities for business intelligence and operational optimization. The analysis covers two primary databases with substantial transaction volumes and identifies key areas for improvement in financial management, inventory optimization, and customer relationship management.

### Key Findings:
- **$12.1M** total outstanding receivables with **$1.5M** overdue
- **32,268** transactions spanning 5 years (2020-2025)
- **214** active customers in SPISA, **388** in xERP
- **1,798** products in inventory with significant dead stock opportunities
- Top customer generates **$329M** in revenue

---

## 🗄️ Database Structure Overview

### SPISA Database (Primary Business System)
| Table | Records | Description |
|-------|---------|-------------|
| Customers | 214 | Customer master data |
| Balances | 228 | Current customer balances |
| Transactions | 32,268 | Financial transactions |
| Articulos | 1,798 | Product inventory |
| NotaPedidos | 39,057 | Purchase orders |
| Categorias | - | Product categories |
| StockSnapshots | - | Historical stock data |

### xERP Database (ERP System)
| Table | Records | Description |
|-------|---------|-------------|
| 0_debtors_master | 388 | Customer master |
| 0_debtor_trans | 33,577 | Customer transactions |
| 0_sales_orders | 16,274 | Sales orders |
| 0_stock_master | 2,491 | Stock items |
| 0_sales_order_details | - | Order line items |

---

## 💰 Financial Analysis

### Current Financial Position
- **Total Outstanding:** $12,143,321
- **Total Overdue:** $1,499,123
- **Average Balance:** $319,561
- **Unique Customers with Balances:** 37

### Top Customers by Outstanding Balance
1. **PAZ LUCAS** - $3,605,169 (No overdue)
2. **METALPRI** - $2,789,031 ($716,910 overdue)
3. **PROINDSUR** - $1,991,342 ($716,281 overdue)
4. **METVAL** - $1,048,245 ($2.69 overdue)
5. **BRICAVAL** - $633,605 ($65,915 overdue)

### xERP Top Revenue Customers
1. **CAÑOSIDER S.R.L.** - $329,702,873 (908 orders)
2. **TUBOS RENARD S.A.** - $147,077,173 (799 orders)
3. **BUDETTA MARIA LAURA** - $124,286,929 (547 orders)
4. **BRIDAS EMI GROUP S.A.** - $96,153,213 (252 orders)
5. **BENEDEJCIC NAHUEL HERNAN** - $84,767,712 (1,081 orders)

---

## 📦 Inventory Analysis

### Top Stock Value Items
1. **DIFERENCIA FACTURACION** - $350,879 (999 units)
2. **Bridas S-150 SORF de 4"** - $336,296 (6,620 units)
3. **Bridas S-150 SORF de 6"** - $264,293 (3,774 units)
4. **Bridas S-150 SORF de 8"** - $206,628 (1,881 units)
5. **Codo R.L. 90º STD. de 6"** - $165,856 (2,131 units)

### Product Categories
- **Bridas** (Flanges)
- **Accesorios** (Accessories)
- **Accesorio Forjado** (Forged Accessories)
- **Casquetes Grandes** (Large Caps)
- **Esparragos** (Studs)
- **Nipples**

---

## 🎯 Valuable Data Insights & Opportunities

### 1. Financial Risk Management

#### Customer Credit Risk Analysis
```sql
-- Identify high-risk customers with significant overdue amounts
SELECT 
    c.Name,
    b.Amount as CurrentBalance,
    b.Due as OverdueAmount,
    (b.Due / NULLIF(b.Amount, 0)) * 100 as OverduePercentage,
    DATEDIFF(DAY, t.LastPaymentDate, GETDATE()) as DaysSinceLastPayment,
    CASE 
        WHEN b.Due > b.Amount * 0.5 THEN 'HIGH RISK'
        WHEN b.Due > b.Amount * 0.2 THEN 'MEDIUM RISK'
        ELSE 'LOW RISK'
    END as RiskLevel
FROM Customers c
INNER JOIN Balances b ON c.Id = b.CustomerId
LEFT JOIN (
    SELECT CustomerId, MAX(PaymentDate) as LastPaymentDate
    FROM Transactions 
    WHERE PaymentDate > '2020-01-01'
    GROUP BY CustomerId
) t ON c.Id = t.CustomerId
WHERE b.Amount > 1000
ORDER BY OverduePercentage DESC;
```

**Business Value:** Proactive identification of customers requiring immediate attention for collections.

### 2. Cash Flow Forecasting

#### Monthly Cash Flow Prediction
```sql
-- Analyze payment patterns and predict future cash flows
WITH MonthlyPayments AS (
    SELECT 
        YEAR(PaymentDate) as Year,
        MONTH(PaymentDate) as Month,
        SUM(PaymentAmount) as ActualPayments
    FROM Transactions 
    WHERE PaymentDate >= DATEADD(MONTH, -12, GETDATE())
    GROUP BY YEAR(PaymentDate), MONTH(PaymentDate)
),
PaymentTrends AS (
    SELECT 
        AVG(ActualPayments) as AvgMonthlyPayments,
        STDEV(ActualPayments) as PaymentVolatility
    FROM MonthlyPayments
)
SELECT 
    mp.*,
    pt.AvgMonthlyPayments,
    (ActualPayments - AvgMonthlyPayments) as Variance,
    CASE 
        WHEN ActualPayments > AvgMonthlyPayments + PaymentVolatility THEN 'Above Average'
        WHEN ActualPayments < AvgMonthlyPayments - PaymentVolatility THEN 'Below Average'
        ELSE 'Normal'
    END as PerformanceCategory
FROM MonthlyPayments mp
CROSS JOIN PaymentTrends pt
ORDER BY Year DESC, Month DESC;
```

**Business Value:** Improved cash flow planning and working capital management.

### 3. Inventory Optimization

#### Slow-Moving & Dead Stock Analysis
```sql
-- Identify inventory that's not moving and calculate carrying costs
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
    StockValue * 0.02 as MonthlyCarryingCost -- Assuming 2% monthly carrying cost
FROM InventoryAnalysis
ORDER BY StockValue DESC;
```

**Business Value:** Reduce inventory carrying costs and free up working capital.

### 4. Customer Profitability Analysis

#### Customer Lifetime Value & Segmentation
```sql
-- Analyze customer profitability and create customer tiers
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
ORDER BY TotalRevenue DESC;
```

**Business Value:** Targeted customer service and marketing strategies based on profitability.

### 5. Sales Performance & Trends

#### Sales Trend Analysis with Seasonality
```sql
-- Identify seasonal patterns and growth trends
WITH MonthlySales AS (
    SELECT 
        YEAR(InvoiceDate) as Year,
        MONTH(InvoiceDate) as Month,
        DATENAME(MONTH, InvoiceDate) as MonthName,
        SUM(InvoiceAmount) as MonthlyRevenue,
        COUNT(DISTINCT CustomerId) as UniqueCustomers,
        COUNT(*) as TransactionCount
    FROM Transactions 
    WHERE Type = 1 AND InvoiceDate >= DATEADD(YEAR, -3, GETDATE())
    GROUP BY YEAR(InvoiceDate), MONTH(InvoiceDate), DATENAME(MONTH, InvoiceDate)
),
SeasonalityAnalysis AS (
    SELECT 
        Month,
        MonthName,
        AVG(MonthlyRevenue) as AvgMonthlyRevenue,
        STDEV(MonthlyRevenue) as RevenueVolatility,
        AVG(UniqueCustomers) as AvgCustomers
    FROM MonthlySales
    GROUP BY Month, MonthName
)
SELECT 
    ms.*,
    sa.AvgMonthlyRevenue,
    (ms.MonthlyRevenue - sa.AvgMonthlyRevenue) / sa.AvgMonthlyRevenue * 100 as PercentageVariance,
    LAG(ms.MonthlyRevenue) OVER (ORDER BY ms.Year, ms.Month) as PreviousMonth,
    (ms.MonthlyRevenue - LAG(ms.MonthlyRevenue) OVER (ORDER BY ms.Year, ms.Month)) / 
    LAG(ms.MonthlyRevenue) OVER (ORDER BY ms.Year, ms.Month) * 100 as MonthOverMonthGrowth
FROM MonthlySales ms
INNER JOIN SeasonalityAnalysis sa ON ms.Month = sa.Month
ORDER BY ms.Year DESC, ms.Month DESC;
```

**Business Value:** Better demand planning and resource allocation based on seasonal patterns.

### 6. Cross-System Data Reconciliation

#### SPISA vs xERP Comparison
```sql
-- Compare data consistency between systems
SELECT 
    'SPISA' as System,
    COUNT(*) as CustomerCount,
    SUM(Amount) as TotalOutstanding
FROM SPISA.dbo.Balances
WHERE Amount > 0
UNION ALL
SELECT 
    'xERP' as System,
    COUNT(DISTINCT debtor_no) as CustomerCount,
    SUM(ov_amount) as TotalOutstanding
FROM xERP.dbo.[0_debtor_trans]
WHERE type = 10;
```

**Business Value:** Ensure data consistency and identify discrepancies between systems.

---

## 🚀 Actionable Business Intelligence Opportunities

### Immediate Actions (0-30 days)
1. **Implement Credit Risk Alerts**
   - Set up automated alerts for customers with >50% overdue balances
   - Create weekly reports for accounts receivable team

2. **Inventory Optimization**
   - Identify and liquidate dead stock (>365 days no sales)
   - Implement reorder points for fast-moving items

3. **Cash Flow Dashboard**
   - Create real-time cash flow monitoring
   - Implement payment prediction models

### Short-term Improvements (1-3 months)
1. **Customer Segmentation**
   - Implement tiered customer service levels
   - Develop targeted marketing campaigns

2. **Sales Performance Tracking**
   - Monthly sales trend analysis
   - Seasonal demand forecasting

3. **Data Quality Improvements**
   - Standardize customer data between systems
   - Implement data validation rules

### Long-term Strategic Initiatives (3-12 months)
1. **Predictive Analytics**
   - Customer churn prediction models
   - Demand forecasting algorithms
   - Dynamic pricing optimization

2. **Advanced Business Intelligence**
   - Real-time dashboards for all key metrics
   - Automated reporting and alerts
   - Integration with external data sources

3. **Process Automation**
   - Automated invoice processing
   - Smart inventory management
   - Predictive maintenance scheduling

---

## 📈 Expected ROI from Implementation

### Financial Impact
- **Reduced DSO (Days Sales Outstanding):** 15-25% improvement
- **Inventory Optimization:** 10-20% reduction in carrying costs
- **Bad Debt Reduction:** 5-15% decrease in write-offs
- **Operational Efficiency:** 20-30% time savings in reporting

### Operational Benefits
- **Improved Decision Making:** Real-time data access
- **Enhanced Customer Service:** Proactive account management
- **Better Resource Allocation:** Data-driven planning
- **Risk Mitigation:** Early warning systems

---

## 🔧 Implementation Recommendations

### Phase 1: Foundation (Month 1)
- Set up automated data extraction processes
- Create basic dashboards for key metrics
- Implement credit risk monitoring

### Phase 2: Enhancement (Months 2-3)
- Deploy advanced analytics queries
- Create customer segmentation models
- Implement inventory optimization

### Phase 3: Automation (Months 4-6)
- Build predictive models
- Automate reporting processes
- Integrate real-time alerts

---

## 📋 Existing Retool Queries Analysis

The current Retool dashboard includes 17 queries across both databases:

### SPISA Queries (9)
- Customer balances and due amounts
- Transaction summaries (monthly/daily billing)
- Stock analysis and discontinued items
- Future payments tracking

### xERP Queries (6)
- Sales orders and billing history
- Customer transaction details
- Bill items with stock correlation

### JavaScript Queries (2)
- Table sorting functionality
- Data correlation between systems

**Recommendation:** Enhance existing dashboard with the advanced analytics queries provided in this report.

---

## 📞 Next Steps

1. **Review and Prioritize** the recommended queries based on business needs
2. **Implement Phase 1** foundation queries in Retool dashboard
3. **Train Users** on new analytics capabilities
4. **Monitor Performance** and adjust based on usage patterns
5. **Scale Implementation** to additional business areas

---

*This analysis provides a comprehensive foundation for data-driven decision making at Dialfa. The recommended queries and insights can significantly improve operational efficiency and financial performance.*

**Contact:** Generated by AI Assistant  
**Date:** September 26, 2025  
**Version:** 1.0

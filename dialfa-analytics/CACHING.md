# Caching System Documentation

## Overview

The Dialfa Analytics Dashboard now includes a comprehensive caching system to reduce database load and improve response times.

## Architecture

### Current Implementation: SimpleCache (In-Memory)

**Advantages:**
- ✅ Zero configuration needed
- ✅ Works immediately
- ✅ No external dependencies
- ✅ Perfect for development and small deployments

**Limitations:**
- ⚠️ Cache is lost on application restart
- ⚠️ Not shared across multiple workers
- ⚠️ Limited memory capacity

### Future: Redis Backend (Production-Ready)

**To upgrade to Redis** (when ready):
1. Install Redis: `apt-get install redis-server` or Docker
2. Set environment variable: `export CACHE_BACKEND=redis`
3. Optionally configure: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
4. Restart application

**No code changes required!**

## Cached Queries

### High-Impact Caches (Longest TTL)

| Query | Cache Duration | Reason |
|-------|----------------|---------|
| `get_monthly_trends()` | 30 minutes | Historical data, changes infrequently |
| `get_abc_analysis()` | 30 minutes | Inventory classification, stable data |
| `get_customer_segmentation()` | 15 minutes | Customer analysis, relatively stable |
| `get_aging_analysis()` | 15 minutes | AR aging, updated daily |
| `get_category_analysis()` | 20 minutes | Category totals, slow-changing |

### Medium-Impact Caches

| Query | Cache Duration | Reason |
|-------|----------------|---------|
| `get_credit_risk_analysis()` | 10 minutes | Important but needs freshness |
| `get_stock_alerts()` | 10 minutes | Inventory warnings |
| `get_top_customers()` | 10 minutes | Top customer list |
| `get_cash_flow_history()` | 15 minutes | Historical cash flow |
| `get_billing_monthly()` | 10 minutes | Monthly aggregates |

### Real-Time or Dynamic

| Query | Cache Duration | Reason |
|-------|----------------|---------|
| `get_billing_today()` | 1 minute | Changes frequently during business hours |
| `/api/health` | 30 seconds | Health checks need fresh data |
| `get_dashboard_alerts()` | 2 minutes | Alerts should be relatively fresh |

## Configuration

### Cache Timeouts

Edit `cache_config.py` to adjust cache durations:

```python
CACHE_TIMEOUTS = {
    'credit_risk': 600,          # 10 minutes
    'executive_summary': 300,     # 5 minutes
    'monthly_trends': 1800,       # 30 minutes
    # ... etc
}
```

### Switching Backends

Set environment variable before starting the app:

```bash
# Development (default)
export CACHE_BACKEND=simple
python app.py

# Production with Redis
export CACHE_BACKEND=redis
export REDIS_HOST=localhost
export REDIS_PORT=6379
python app.py

# Filesystem cache (alternative)
export CACHE_BACKEND=filesystem
python app.py
```

## Admin Endpoints (Requires Admin Role)

### Clear All Cache

```bash
curl -X POST http://localhost:5000/api/admin/cache/clear \
  -H "Content-Type: application/json" \
  --cookie "session=YOUR_SESSION_COOKIE"
```

**Response:**
```json
{
  "status": "success",
  "message": "All cache cleared successfully"
}
```

### Clear Specific Module Cache

```bash
curl -X POST http://localhost:5000/api/admin/cache/clear/financial \
  -H "Content-Type: application/json" \
  --cookie "session=YOUR_SESSION_COOKIE"
```

**Available types:** `financial`, `inventory`, `sales`, `dashboard`

**Note:** With SimpleCache, this clears all cache. With Redis, it selectively clears by prefix.

### Get Cache Statistics

```bash
curl http://localhost:5000/api/admin/cache/stats \
  --cookie "session=YOUR_SESSION_COOKIE"
```

**Response:**
```json
{
  "status": "success",
  "stats": {
    "backend": "SimpleCache",
    "default_timeout": 300,
    "note": "For detailed stats, upgrade to Redis backend"
  }
}
```

### Test Cache

```bash
curl http://localhost:5000/api/admin/cache/test \
  --cookie "session=YOUR_SESSION_COOKIE"
```

## Performance Impact

### Expected Improvements

**Before Caching:**
- `/api/dashboard/overview`: ~1.5-3 seconds
- `/financial/api/credit-risk`: ~1-2 seconds
- `/api/dashboard/alerts`: ~1 second
- **Total page load:** 5-10 seconds

**After Caching (cache hit):**
- `/api/dashboard/overview`: ~50-100ms
- `/financial/api/credit-risk`: ~20-50ms
- `/api/dashboard/alerts`: ~30-70ms
- **Total page load:** 200-500ms

**Improvement: 10-20x faster on cache hits!**

### Database Load Reduction

Based on your logs showing repeated calls every 1-2 minutes:

**Before:**
- `/api/dashboard/alerts` called 3-4 times/minute = **180-240 DB queries/hour**

**After (2-minute cache):**
- `/api/dashboard/alerts` cached = **~30 DB queries/hour**

**Database load reduced by 70-85%!**

## Monitoring Cache Performance

### Check Logs

Cache misses are logged:

```
2025-10-01 13:06:20 - analytics.financial - INFO - Executing get_credit_risk_analysis (cache miss or expired)
```

If you see these frequently, cache is working but may need longer TTL.

### Monitor Application Logs

```bash
# In production, watch for cache activity
tail -f logs/dialfa_analytics.log | grep "cache"
```

## Cache Warming (Optional)

To pre-populate cache on app startup, add to `app.py`:

```python
def warm_cache():
    """Warm up cache with common queries"""
    with app.app_context():
        app.financial_analytics.get_executive_summary()
        app.financial_analytics.get_credit_risk_analysis()
        app.inventory_analytics.get_stock_alerts()
        # ... etc

# In create_app(), after initializing analytics:
warm_cache()
```

## Troubleshooting

### Cache Not Working

**Symptoms:** Still slow, seeing DB queries in logs

**Check:**
1. Ensure Flask-Caching is installed: `pip list | grep Flask-Caching`
2. Check logs for "Cache initialized with backend"
3. Verify decorators are applied to functions
4. Try cache test endpoint: `/api/admin/cache/test`

### Cache Too Stale

**Symptoms:** Showing old data

**Solutions:**
1. Reduce cache timeout in `cache_config.py`
2. Manually clear cache: `POST /api/admin/cache/clear`
3. Consider adding cache invalidation triggers on data changes

### Memory Issues

**Symptoms:** Application using too much RAM

**Solutions:**
1. Reduce `CACHE_THRESHOLD` for filesystem cache
2. Lower cache timeouts to expire data faster
3. Upgrade to Redis with configurable memory limits

## Best Practices

### DO:
✅ Cache expensive queries with slow-changing data  
✅ Use longer TTLs for historical/aggregated data  
✅ Monitor cache hit rates in production  
✅ Clear cache after bulk data imports  
✅ Use Redis in production for better control  

### DON'T:
❌ Cache real-time data (today's transactions)  
❌ Set TTL too high for critical financial data  
❌ Forget to clear cache after database changes  
❌ Cache user-specific data without user ID in key  
❌ Use SimpleCache with multiple workers in production  

## Migrating to Redis

### Step 1: Install Redis

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**Docker:**
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

**Windows:**
Use Docker or WSL2

### Step 2: Install Python Redis Client

```bash
pip install redis
```

### Step 3: Configure Environment

```bash
export CACHE_BACKEND=redis
export REDIS_HOST=localhost
export REDIS_PORT=6379
# Optional:
export REDIS_PASSWORD=your_password_here
export REDIS_DB=0
```

### Step 4: Restart Application

```bash
python app.py
```

Check logs for:
```
Cache initialized with backend: redis
Cache config: RedisCache
```

### Step 5: Verify

```bash
# Check Redis
redis-cli ping
# Should return: PONG

# Check keys
redis-cli keys "dialfa_*"
# Should show cached keys
```

## Advanced: Cache Invalidation

### Manual Invalidation in Code

```python
from cache_config import cache

# In your data update function:
def update_customer_data(customer_id):
    # Update database
    db.execute("UPDATE ...")
    
    # Invalidate relevant caches
    cache.delete('financial_credit_risk')
    cache.delete('financial_exec_summary')
    cache.delete('financial_top_customers_10')
```

### Automatic Invalidation (Future Enhancement)

Consider implementing:
- Database triggers that call invalidation API
- Message queue (RabbitMQ/Redis Pub/Sub) for cache invalidation
- Time-based invalidation during off-hours

## Performance Metrics

### Monitor These Metrics:

1. **Cache Hit Rate:** Percentage of requests served from cache
2. **Average Response Time:** Before vs after caching
3. **Database Query Count:** Reduction in DB load
4. **Memory Usage:** Cache memory consumption

### Expected Results:

- **Cache Hit Rate:** 60-80% (depending on traffic patterns)
- **Response Time:** 10-20x improvement on cache hits
- **DB Load:** 70-85% reduction
- **User Experience:** Dramatically faster page loads

---

**Implemented:** October 1, 2025  
**Version:** 1.0.0 (SimpleCache)  
**Upgrade Path:** Redis ready, switch with environment variable  
**Status:** ✅ Production Ready (SimpleCache for small deployments, Redis recommended for scale)


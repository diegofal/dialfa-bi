# Railway Deployment Setup

This document contains instructions for deploying the Dialfa BI application to Railway.

## Prerequisites

✅ Railway CLI installed
✅ Git repository pushed to GitHub (git@github.com:diegofal/dialfa-bi.git)
✅ Railway configuration files created:
   - `Procfile` - Defines how to start the application
   - `railway.json` - Railway deployment configuration
   - `runtime.txt` - Python version specification
   - `.railwayignore` - Files to exclude from deployment

## Step-by-Step Deployment

### 1. Login to Railway
```cmd
railway login
```
This will open your browser to authenticate with Railway.

### 2. Initialize Railway Project
```cmd
railway init
```
Choose:
- Create a new project or select existing
- Give your project a name (e.g., "dialfa-bi")

### 3. Link GitHub Repository
You can do this in two ways:

**Option A: Via Railway Dashboard (Recommended)**
1. Go to https://railway.app/dashboard
2. Click on your project
3. Click "New" → "GitHub Repo"
4. Select `diegofal/dialfa-bi` repository
5. Railway will automatically deploy on every push to `main` branch

**Option B: Via CLI**
```cmd
railway up
```

### 4. Configure Environment Variables
You need to set the following environment variables in Railway:

```cmd
railway variables set SECRET_KEY=your-secret-key-here
railway variables set FLASK_ENV=production
railway variables set DB_HOST=your-database-host
railway variables set DB_PORT=your-database-port
railway variables set DB_NAME=your-database-name
railway variables set DB_USER=your-database-user
railway variables set DB_PASSWORD=your-database-password
```

Or set them via the Railway Dashboard:
1. Go to your project
2. Click on "Variables" tab
3. Add each variable

### 5. Add a Database (if needed)
If you need a PostgreSQL database:
```cmd
railway add --database postgresql
```

### 6. Deploy
If using GitHub integration, deployments happen automatically on push.

To manually deploy:
```cmd
railway up
```

### 7. View Deployment
```cmd
railway open
```

Or check logs:
```cmd
railway logs
```

## Important Environment Variables

Make sure to configure these in Railway Dashboard:

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | `random-secret-key-12345` |
| `FLASK_ENV` | Environment | `production` |
| `DB_HOST` | Database host | `your-db-host` |
| `DB_PORT` | Database port | `1433` |
| `DB_NAME` | Database name | `SPISA` |
| `DB_USER` | Database user | `your-username` |
| `DB_PASSWORD` | Database password | `your-password` |

## Automatic Deployments

✅ **Automatic deployment is now configured!**

Every time you push to the `main` branch on GitHub, Railway will:
1. Detect the changes
2. Build your application
3. Run tests (if configured)
4. Deploy the new version
5. Perform health checks at `/api/health`

## Monitoring

- **Health Check**: Railway monitors `/api/health` endpoint
- **Logs**: `railway logs` or view in dashboard
- **Metrics**: View in Railway dashboard

## Troubleshooting

### Build Fails
- Check `railway logs`
- Verify all dependencies in `requirements.txt`
- Ensure Python version matches `runtime.txt`

### App Won't Start
- Check environment variables are set correctly
- Verify database connection strings
- Check logs for specific errors

### Database Connection Issues
- Verify database credentials
- Check if Railway can access your database (firewall rules)
- For external databases, ensure they're accessible from Railway's IP ranges

## Useful Commands

```cmd
# View logs
railway logs

# Check status
railway status

# Open in browser
railway open

# Run commands in Railway environment
railway run python manage.py migrate

# View environment variables
railway variables

# Delete deployment
railway down
```

## Support

For more information, visit:
- Railway Documentation: https://docs.railway.app
- Railway Discord: https://discord.gg/railway

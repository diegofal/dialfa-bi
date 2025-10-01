# Quick Railway Deployment Guide

Your Railway project is created but not connected to GitHub yet. Follow these steps:

## Step 1: Go to Railway Dashboard
Open: https://railway.com/project/9dd91ada-9703-46ac-bdef-dc63b1be694b

## Step 2: Add GitHub Service

1. In the Railway dashboard, click the **"+ New"** button
2. Select **"GitHub Repo"**
3. Authorize Railway to access your GitHub if needed
4. Select repository: **`diegofal/dialfa-bi`**
5. Select branch: **`main`**
6. Click **"Deploy"**

## Step 3: Configure Environment Variables

After the service is created, go to the **Variables** tab and add:

```
SECRET_KEY=dialfa-analytics-production-2025
FLASK_DEBUG=False
DB_SERVER=dialfa.database.windows.net
DB_USER=fp
DB_PASSWORD=Ab1234,,,
SPISA_DB=SPISA
XERP_DB=xERP
```

## Step 4: Wait for Deployment

Railway will:
- Build your Docker image (this may take 3-5 minutes)
- Deploy the container
- Assign the URL: https://dialfa-bi-production.up.railway.app

## Step 5: Monitor Deployment

Watch the build logs in the Railway dashboard to see:
- Docker build progress
- Package installation
- Application startup

## Troubleshooting

If deployment fails:
1. Check the build logs in Railway dashboard
2. Verify all environment variables are set
3. Ensure the database is accessible from Railway's IP

## Success Indicators

✅ Build completes without errors
✅ Health check passes at `/api/health`
✅ App is accessible at the Railway URL

# 🚀 Quick Deployment Guide

## ✅ Configuration Complete!

Vercel will now ignore your Python backend and only deploy the Next.js frontend.

## What Changed

### 1. `.vercelignore` (NEW)
Tells Vercel to ignore:
- `api/` folder (Python backend)
- All Python files and config
- Railway configuration files

### 2. `vercel.json` (UPDATED)
Removed Python API configuration. Now only contains Next.js settings.



## Deployment Steps

### Step 1: Deploy Backend to Railway

\`\`\`bash
# Commit your changes
git add .
git commit -m "Configure split deployment: Vercel + Railway"
git push origin main
\`\`\`

Railway will automatically:
1. Detect `Dockerfile`
2. Build Docker image
3. Deploy FastAPI backend
4. Give you a URL like: `https://firmable-production.up.railway.app`

### Step 2: Set Environment Variables in Vercel

Go to Vercel Dashboard → Your Project → Settings → Environment Variables

Add these variables:
\`\`\`
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
API_SECRET_KEY=your-secret-key-here
\`\`\`

**Important**: Use the exact Railway URL you get from Step 1!

### Step 3: Deploy Frontend to Vercel

Vercel will automatically deploy when you push to GitHub.

Or deploy manually:
\`\`\`bash
npx vercel --prod
\`\`\`

Vercel will:
1. ✅ Ignore `api/` folder (thanks to `.vercelignore`)
2. ✅ Build Next.js app
3. ✅ Use Railway backend URL from environment variables

## Test Your Deployment

### 1. Test Backend (Railway)
\`\`\`bash
curl https://your-backend.railway.app/api/health
\`\`\`
Expected response:
\`\`\`json
{"status":"healthy"}
\`\`\`

### 2. Test Frontend (Vercel)
Visit: `https://your-project.vercel.app`

The frontend should be able to call the Railway backend!

## Local Development

For local development, run both servers:

**Terminal 1 - Backend:**
\`\`\`bash
cd api
uv run uvicorn index:app --reload --port 8000
\`\`\`

**Terminal 2 - Frontend:**
\`\`\`bash
pnpm dev
\`\`\`

The Next.js rewrites will automatically proxy `/api/*` to `http://localhost:8000/api/*`.

## Environment Variables Summary

### Railway (Backend)
\`\`\`env
OPENAI_API_KEY=sk-...
API_SECRET_KEY=your-secret-key
UNSTRUCTURED_API_KEY=your-key (optional)
\`\`\`

### Vercel (Frontend)
\`\`\`env
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
API_SECRET_KEY=your-secret-key (same as backend)
\`\`\`

### Local (.env.local)
\`\`\`env
# Backend keys
OPENAI_API_KEY=sk-...
API_SECRET_KEY=your-secret-key
UNSTRUCTURED_API_KEY=your-key (optional)

# Frontend will use localhost:8000 in development
NEXT_PUBLIC_API_URL=http://localhost:8000
\`\`\`

## File Checklist

### Vercel Configuration
- ✅ `.vercelignore` - Ignores Python backend
- ✅ `vercel.json` - Vercel settings
- ✅ `next.config.mjs` - Rewrites for API proxy

### Railway Configuration
- ✅ `Dockerfile` - Docker build
- ✅ `docker-compose.yml` - Local Docker testing
- ✅ `.railwayignore` - Ignores frontend files
- ✅ `railway.json` - Railway settings
- ✅ `.dockerignore` - Excludes files from Docker build

## Common Issues

### ❌ Vercel tries to build Python
**Solution**: Make sure `.vercelignore` exists and contains `api/`

### ❌ API calls fail on Vercel
**Solution**: Check `NEXT_PUBLIC_API_URL` environment variable in Vercel

### ❌ CORS errors
**Solution**: Make sure Railway backend allows your Vercel domain in CORS settings

### ❌ 401 Unauthorized
**Solution**: Make sure `API_SECRET_KEY` matches between Vercel and Railway

## Architecture

\`\`\`
┌──────────────┐         ┌──────────────┐
│   GitHub     │         │   GitHub     │
│   (Push)     │         │   (Push)     │
└──────┬───────┘         └──────┬───────┘
       │                        │
       ▼                        ▼
┌──────────────┐         ┌──────────────┐
│   Vercel     │         │   Railway    │
│              │         │              │
│  Next.js     │─────────│  FastAPI     │
│  Frontend    │  API    │  Backend     │
│              │  Calls  │  (Docker)    │
└──────────────┘         └──────────────┘
       │                        │
       │                        │
       ▼                        ▼
   your-app           your-backend
   .vercel.app        .railway.app
\`\`\`

## Next Steps

1. ✅ Configuration complete
2. ⏭️ Push to GitHub
3. ⏭️ Get Railway backend URL
4. ⏭️ Add Railway URL to Vercel env vars
5. ⏭️ Test both deployments
6. ⏭️ Celebrate! 🎉

---

**Your app is ready for production!** 🚀

Need help? Check:
- `DEPLOYMENT_ARCHITECTURE.md` - Detailed architecture
- `DOCKER_SUCCESS.md` - Docker configuration
- `RAILWAY_SETUP.md` - Railway deployment guide

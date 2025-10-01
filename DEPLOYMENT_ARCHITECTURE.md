# 🚀 Deployment Architecture

## Overview
Your application uses a **split deployment architecture**:
- **Frontend (Next.js)** → Vercel
- **Backend (FastAPI)** → Railway

## Deployment Setup

### Frontend on Vercel
Vercel will:
- ✅ Build and deploy Next.js app
- ✅ Ignore Python backend files (`.vercelignore`)
- ✅ Only deploy frontend code

**Configuration:**
- `vercel.json` - Vercel settings (removed Python API config)
- `.vercelignore` - Excludes `api/` folder and Python files

### Backend on Railway
Railway will:
- ✅ Build Docker container
- ✅ Deploy FastAPI backend
- ✅ Ignore frontend files (`.railwayignore`)
- ✅ Only deploy backend code

**Configuration:**
- `Dockerfile` - Docker build instructions
- `railway.json` - Railway settings
- `.railwayignore` - Excludes Next.js files

## File Structure

```
Firmable-AI-Business-Searcher/
├── api/                    # Backend (Railway)
│   ├── __init__.py
│   ├── index.py           # FastAPI app
│   ├── analyzer.py
│   ├── scraper.py
│   └── chat.py
│
├── app/                    # Frontend (Vercel)
│   ├── page.tsx
│   ├── layout.tsx
│   └── api/               # Next.js API routes (Vercel)
│       └── analyze/
│
├── components/             # Frontend (Vercel)
├── lib/                    # Frontend (Vercel)
│
├── .vercelignore          # Vercel: ignore backend
├── .railwayignore         # Railway: ignore frontend
├── vercel.json            # Vercel config
├── railway.json           # Railway config
└── Dockerfile             # Railway Docker build
```

## Deployment Flow

### 1. Deploy Backend to Railway

```bash
# Push to GitHub
git add .
git commit -m "Configure split deployment"
git push origin main

# Railway auto-deploys on push
# You'll get a URL like: https://your-app.railway.app
```

### 2. Update Frontend Environment Variables

In your local `.env.local`:
```env
API_URL=https://your-app.railway.app
API_SECRET_KEY=your-secret-key
```

In Vercel dashboard (Settings → Environment Variables):
```
API_URL=https://your-app.railway.app
API_SECRET_KEY=your-secret-key
NEXT_PUBLIC_API_URL=https://your-app.railway.app (if needed for client-side)
```

### 3. Deploy Frontend to Vercel

Vercel will auto-deploy when you push to GitHub (if connected).

Or manually:
```bash
vercel --prod
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│                   Internet                       │
└─────────────────────────────────────────────────┘
           │                        │
           │                        │
    ┌──────▼─────┐           ┌─────▼──────┐
    │   Vercel   │           │  Railway   │
    │            │           │            │
    │  Next.js   │──────────▶│  FastAPI   │
    │  Frontend  │   API     │  Backend   │
    │            │  Calls    │            │
    └────────────┘           └────────────┘
         │                         │
    Static Files              Python API
    React Components          + AI Processing
    Server Actions            + Web Scraping
```

## Why This Architecture?

### Advantages
1. **Separation of Concerns**
   - Frontend and backend can be developed/deployed independently
   - Different scaling strategies for each

2. **Platform Optimization**
   - Vercel is optimized for Next.js
   - Railway is optimized for Docker/Python

3. **Cost Efficiency**
   - Vercel's free tier for frontend
   - Railway's free tier for backend

4. **Better Performance**
   - Static frontend on Vercel's edge network
   - Backend scales independently

## Environment Variables

### Backend (Railway)
```env
OPENAI_API_KEY=sk-...
API_SECRET_KEY=your-secret-key
UNSTRUCTURED_API_KEY=your-key (optional)
PORT=(Railway sets automatically)
```

### Frontend (Vercel)
```env
API_URL=https://your-backend.railway.app
API_SECRET_KEY=your-secret-key (same as backend)
```

## Testing

### Test Backend (Railway)
```bash
curl https://your-backend.railway.app/api/health
# Expected: {"status":"healthy"}
```

### Test Frontend (Vercel)
Visit: `https://your-frontend.vercel.app`

## Updating Deployments

### Update Backend
```bash
# Make changes to api/ folder
git add api/
git commit -m "Update backend"
git push

# Railway auto-deploys
```

### Update Frontend
```bash
# Make changes to app/ or components/
git add app/ components/
git commit -m "Update frontend"
git push

# Vercel auto-deploys
```

## Troubleshooting

### Vercel tries to build Python files
✅ **Fixed!** `.vercelignore` now excludes `api/` folder

### Railway tries to build Next.js
✅ **Fixed!** `.railwayignore` now excludes frontend files

### CORS Errors
Make sure your FastAPI backend allows your Vercel domain:
```python
# api/index.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.vercel.app", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API Connection Failed
1. Check Railway URL is correct in Vercel environment variables
2. Verify Railway backend is running
3. Check API_SECRET_KEY matches on both sides

## Next Steps

1. ✅ Configure `.vercelignore` (Done!)
2. ⏭️ Push to GitHub
3. ⏭️ Deploy backend to Railway
4. ⏭️ Get Railway URL
5. ⏭️ Update Vercel environment variables
6. ⏭️ Deploy frontend to Vercel
7. ⏭️ Test end-to-end

---

**Your app is now configured for split deployment!** 🎉

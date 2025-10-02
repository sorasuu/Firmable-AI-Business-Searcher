# Quick Deployment Guide 🚀

## Pre-Deployment Checklist

- [ ] All tests passing: `pytest api/test_api.py -v`
- [ ] Code pushed to GitHub
- [ ] Environment variables documented
- [ ] README updated with project info

## Deployment Steps

### 1. Deploy Backend to Railway

1. **Sign up at [railway.app](https://railway.app)**

2. **Create New Project**
   - Click "New Project"
   - Choose "Deploy from GitHub repo"
   - Select your repository

3. **Configure Environment Variables**
   ```
   GROQ_API_KEY=gsk_your_actual_key
   API_SECRET_KEY=your-production-secret-key
   ```

4. **Railway Auto-Detects**
   - Sees `Dockerfile` → builds container
   - Sees `requirements.txt` → installs dependencies
   - Sets `PORT` automatically

5. **Get Your Backend URL**
   - Railway assigns: `https://your-app.railway.app`
   - Copy this URL for frontend setup

### 2. Deploy Frontend to Vercel

1. **Sign up at [vercel.com](https://vercel.com)**

2. **Import GitHub Repository**
   - Click "New Project"
   - Import your repository
   - Vercel auto-detects Next.js

3. **Configure Environment Variables**
   - Go to Project Settings → Environment Variables
   - Add:
     ```
     API_URL=https://your-app.railway.app
     API_SECRET_KEY=your-production-secret-key
     ```
   - ⚠️ Use the SAME secret key as backend

4. **Deploy**
   - Click "Deploy"
   - Vercel builds and deploys
   - Get URL: `https://your-project.vercel.app`

### 3. Update Documentation

Update `README.md` with your live URLs:

```markdown
## 🚀 Live Demo

- **Frontend URL**: https://your-project.vercel.app
- **Backend API**: https://your-app.railway.app
- **API Endpoints**:
  - `POST https://your-app.railway.app/api/analyze` - Website analysis
  - `POST https://your-app.railway.app/api/chat` - Conversational Q&A
```

### 4. Test Deployed Application

```bash
# Test backend health
curl https://your-app.railway.app/health

# Test analyze endpoint
curl -X POST https://your-app.railway.app/api/analyze \
  -H "Authorization: Bearer your-production-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Visit frontend
# Open https://your-project.vercel.app in browser
```

## Environment Variables Summary

### Backend (Railway)
```env
GROQ_API_KEY=gsk_your_actual_key
API_SECRET_KEY=your-production-secret-key
PORT=(auto-set by Railway)
```

### Frontend (Vercel)
```env
API_URL=https://your-app.railway.app
API_SECRET_KEY=your-production-secret-key
```

## Troubleshooting

### Frontend can't connect to backend
- ✅ Check `API_URL` in Vercel matches Railway URL
- ✅ Check `API_SECRET_KEY` matches on both
- ✅ Check backend health: `curl https://your-app.railway.app/health`
- ✅ Check Railway logs for errors

### Backend won't start
- ✅ Check `GROQ_API_KEY` is set and valid
- ✅ Check Railway build logs
- ✅ Verify `requirements.txt` is complete
- ✅ Check `Dockerfile` is valid

### Authentication errors
- ✅ Verify `API_SECRET_KEY` is the SAME on both deployments
- ✅ Check it's not accidentally `undefined` or empty
- ✅ Don't commit secret key to GitHub (use environment variables)

### CORS errors
- ✅ Backend CORS is set to `allow_origins=["*"]` (already configured)
- ✅ For production, update to specific domain in `api/index.py`:
  ```python
  allow_origins=["https://your-project.vercel.app"]
  ```

## Post-Deployment

### Monitor
- Railway Dashboard: View logs, metrics
- Vercel Analytics: View usage, performance

### Update
- Push to GitHub → Auto-deploys to both platforms
- Or use CLI:
  ```bash
  # Vercel
  vercel --prod
  
  # Railway redeploys automatically on git push
  ```

### Cost
- **Railway**: Free tier includes 500 hours/month
- **Vercel**: Free tier for hobby projects
- **Groq**: Free tier with rate limits

## Production Optimization

### Security
- [ ] Use production secret key (not "your-secret-key-here")
- [ ] Rotate keys periodically
- [ ] Enable HTTPS only (already done by Railway/Vercel)
- [ ] Set specific CORS origins (not `*`)

### Performance
- [ ] Monitor Railway response times
- [ ] Add Redis cache if needed (Railway add-on)
- [ ] Consider CDN for static assets (Vercel does this)

### Monitoring
- [ ] Set up error tracking (Sentry)
- [ ] Set up uptime monitoring (UptimeRobot)
- [ ] Set up analytics (Vercel Analytics)

## Quick Links

- **Railway**: https://railway.app
- **Vercel**: https://vercel.com
- **Groq**: https://console.groq.com
- **Your GitHub**: https://github.com/sorasuu/Firmable-AI-Business-Searcher

---

**Ready to Deploy?** Follow the steps above and you'll be live in ~10 minutes! 🚀

# Deployment Guide for Portfoliq.xyz

## Quick Start Deployment Steps

### 1. Push to GitHub
```bash
# Initialize git (if not already done)
cd "C:\Users\Tausif-Aventador\SaaS Ideas\cryptoportfoliotracker"
git init
git add .
git commit -m "Initial commit for portfoliq.xyz"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/cryptoportfoliotracker.git
git push -u origin main
```

### 2. Deploy Backend to Render

1. Go to [render.com](https://render.com) and sign up (free)
2. Click "New +" → "Web Service"
3. Connect your GitHub account
4. Select your repository
5. Configure:
   - Name: `portfoliq-api`
   - Branch: `main`
   - Root Directory: `crypto-ai-backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
6. Click "Create Web Service"

### 3. Set Environment Variables in Render

After deployment, go to Environment tab and add:

```
FLASK_ENV=production
CORS_ORIGINS=https://portfoliq.xyz,https://www.portfoliq.xyz
MAIL_USERNAME=your-gmail@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=Portfoliq <your-gmail@gmail.com>
```

### 4. Deploy Frontend

For React Native Web:
1. Build for web: `cd crypto-portfolio && npx expo build:web`
2. Deploy to Netlify/Vercel (drag & drop the `web-build` folder)

### 5. Connect Your Domain

#### In GoDaddy:
1. Go to DNS Management
2. Add these records:

For Render (Backend API):
```
Type: CNAME
Name: api
Value: portfoliq-api.onrender.com
```

For Netlify/Vercel (Frontend):
```
Type: A
Name: @
Value: [Netlify/Vercel will provide this]
```

```
Type: CNAME
Name: www
Value: [Netlify/Vercel will provide this]
```

### 6. Update Frontend API URL

In `crypto-portfolio/src/services/exchangeService.js`:
```javascript
this.baseURL = process.env.EXPO_PUBLIC_API_BASE_URL || 'https://api.portfoliq.xyz/api';
```

## Your URLs will be:
- Frontend: https://portfoliq.xyz
- Backend API: https://api.portfoliq.xyz

## SSL Certificates
Both Render and Netlify/Vercel provide free SSL certificates automatically!

## Total Cost:
- Domain: $15/year
- Hosting: FREE (Render + Netlify free tiers)
- SSL: FREE
- Database: FREE (Render PostgreSQL)

## Next Steps:
1. Monitor your app at Render Dashboard
2. Set up error tracking (Sentry - free tier)
3. Add Google Analytics
4. Submit to search engines
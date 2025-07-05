# User Flow & Data Security Architecture

## Complete User Journey

### 1. New User Registration
```mermaid
User Signs Up
    │
    ├─> Email + Password entered
    ├─> Password hashed (bcrypt)
    ├─> User record created in PostgreSQL
    ├─> JWT tokens generated
    │   ├─> Access token (15 min)
    │   └─> Refresh token (7 days)
    └─> Tokens stored in AsyncStorage (mobile)
```

### 2. Exchange Integration Flow
```mermaid
User Adds Exchange
    │
    ├─> Enters API Key + Secret
    ├─> Frontend sends to Backend (HTTPS)
    ├─> Backend encrypts with AES-256
    ├─> Encrypted credentials stored in DB
    ├─> Test connection to exchange
    └─> Success notification
```

### 3. Daily Usage Flow
```mermaid
App Opens
    │
    ├─> Check AsyncStorage for tokens
    ├─> If expired, use refresh token
    ├─> Fetch user profile from backend
    ├─> Backend decrypts exchange credentials
    ├─> Connect to exchanges (in memory only)
    ├─> Fetch portfolio data
    └─> Display in app with real-time updates
```

## Data Storage Locations

### Backend (PostgreSQL Database)
```sql
-- What's stored in the database:
1. User account info
   - Email (unique)
   - Password hash (bcrypt)
   - Account creation date
   - Subscription tier

2. Encrypted exchange credentials
   - User ID (foreign key)
   - Exchange name (binance, coinbase, etc.)
   - Encrypted API key
   - Encrypted API secret
   - Never stored in plain text!

3. Portfolio snapshots
   - Historical portfolio values
   - Holdings at specific times
   - Used for charts and analytics

4. Trade history
   - All executed trades
   - P&L calculations
   - Strategy performance
```

### Mobile App (AsyncStorage)
```javascript
// What's stored on the phone:
{
  "auth_token": "JWT access token",
  "refresh_token": "JWT refresh token",
  "user_email": "user@example.com",
  "theme_preference": "dark",
  "last_sync": "2024-01-15T10:30:00Z",
  "cached_portfolio": {
    // Temporary cache for offline viewing
  }
}

// NEVER stored on mobile:
// - Exchange API keys
// - Passwords
// - Other users' data
```

## Security Measures

### 1. Authentication Security
- **Passwords**: Hashed with bcrypt (cost factor 12)
- **JWT Tokens**: Signed with HS256, short expiration
- **Refresh Tokens**: Rotated on use, stored securely
- **Session Management**: Redis for active sessions

### 2. API Credential Security
```python
# How exchange credentials are protected:

# 1. User enters API keys in app
# 2. Sent to backend over HTTPS
# 3. Backend encrypts immediately:
encrypted_key = encryption_service.encrypt(api_key)
encrypted_secret = encryption_service.encrypt(api_secret)

# 4. Only encrypted versions stored in DB
# 5. Decrypted only when needed in memory:
api_key = encryption_service.decrypt(encrypted_key)
# Use for API call
# Immediately garbage collected
```

### 3. Data Isolation
- Each user can only access their own data
- Row-level security in PostgreSQL
- API endpoints filter by user ID from JWT
- No cross-user data leakage possible

## Production Infrastructure

### Recommended Setup
```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Cloudflare │────▶│  Load Balancer  │────▶│  Web Servers │
│     (CDN)    │     │   (Nginx/ALB)   │     │  (Flask x3)  │
└──────────────┘     └─────────────────┘     └──────────────┘
                                                      │
                            ┌─────────────────────────┴─────┐
                            │                               │
                      ┌─────▼──────┐              ┌────────▼────────┐
                      │ PostgreSQL │              │     Redis       │
                      │  (Primary)  │              │ (Cache/Sessions)│
                      └─────┬──────┘              └─────────────────┘
                            │
                      ┌─────▼──────┐
                      │ PostgreSQL │
                      │  (Replica)  │
                      └────────────┘
```

## Deployment Steps Summary

1. **Database Setup**
   - Create PostgreSQL database
   - Run migrations
   - Set up automated backups

2. **Backend Deployment**
   - Deploy to Heroku/Railway/AWS
   - Set environment variables
   - Configure domain and SSL

3. **Mobile App Release**
   - Update API endpoints
   - Build production versions
   - Submit to app stores

4. **Post-Launch**
   - Monitor error rates
   - Track user signups
   - Optimize performance

## Cost Estimates (Monthly)

### Starting (0-100 users)
- Heroku Hobby: $7/month
- PostgreSQL: $0 (free tier)
- Total: ~$7/month

### Growing (100-1000 users)
- Heroku Standard: $25/month
- PostgreSQL: $9/month
- Redis: $15/month
- Total: ~$49/month

### Scaling (1000+ users)
- Multiple dynos: $50/month
- PostgreSQL cluster: $50/month
- Redis cluster: $30/month
- CDN: $20/month
- Total: ~$150/month

## Quick Launch Option

For fastest deployment:
1. Use Heroku for backend
2. Use Supabase for PostgreSQL
3. Deploy mobile app with Expo
4. Add Sentry for monitoring

This gets you live in under 2 hours!
# Frontend Authentication Update Guide

## Overview
All sensitive API endpoints now require authentication. This guide explains how to update your frontend code to work with the secured backend.

## Changes Made

### 1. **AI Service Updated**
- Added authentication helper method
- Updated `analyzePortfolio()` to use authenticated requests
- Updated `getPricePrediction()` to use authenticated requests
- Now uses environment variable for API URL

### 2. **Exchange Service**
- Already has `makeAuthenticatedRequest()` method
- Uses `authService` for JWT token management
- Properly handles authenticated requests

## Required Frontend Updates

### 1. **Ensure User Login**
Before accessing protected features, ensure users are logged in:

```javascript
// In your screens/components
import { authService } from '../services/authService';

// Check if user is logged in
if (!authService.isLoggedIn()) {
  // Redirect to login screen
  navigation.navigate('Login');
  return;
}
```

### 2. **Handle Authentication Errors**
Update error handling to catch 401 (Unauthorized) errors:

```javascript
try {
  const analysis = await aiService.analyzePortfolio(holdings, prices);
  // Handle success
} catch (error) {
  if (error.message.includes('Authentication required')) {
    // Redirect to login
    navigation.navigate('Login');
  } else {
    // Handle other errors
    Alert.alert('Error', error.message);
  }
}
```

### 3. **Update Strategy Screens**
All strategy endpoints now require authentication:

```javascript
// Before calling strategy analysis
if (!authService.isLoggedIn()) {
  Alert.alert('Login Required', 'Please log in to use trading strategies');
  navigation.navigate('Login');
  return;
}

// Then make the request
const response = await exchangeService.makeAuthenticatedRequest(
  '/strategies/trendline_breakout/analyze',
  strategyData
);
```

### 4. **Environment Configuration**

#### Development (.env.local)
```env
EXPO_PUBLIC_API_BASE_URL=http://192.168.0.177:5000/api
```

#### Production (.env.production)
```env
EXPO_PUBLIC_API_BASE_URL=https://api.yourdomain.com/api
```

### 5. **Update App Initialization**
In your App.js or main component:

```javascript
import { authService } from './src/services/authService';

// Check authentication status on app start
const checkAuthStatus = async () => {
  const isLoggedIn = await authService.isLoggedIn();
  if (isLoggedIn) {
    // Navigate to main app
    navigation.navigate('MainTabs');
  } else {
    // Navigate to login
    navigation.navigate('Login');
  }
};
```

## Testing Checklist

### 1. **Authentication Flow**
- [ ] User can register new account
- [ ] User can log in with credentials
- [ ] JWT token is stored in AsyncStorage
- [ ] Token is sent with API requests
- [ ] Token refresh works when expired

### 2. **Protected Features**
- [ ] Portfolio analysis requires login
- [ ] Price predictions require login
- [ ] Strategy analysis requires login
- [ ] Exchange operations require login

### 3. **Error Handling**
- [ ] 401 errors redirect to login
- [ ] Expired tokens trigger refresh
- [ ] Network errors show appropriate message
- [ ] Loading states work correctly

## Common Issues & Solutions

### Issue: "Authentication required" error
**Solution**: Ensure user is logged in before making API calls

### Issue: CORS errors in browser
**Solution**: Backend CORS is configured for production domains. Update CORS_ORIGINS in backend .env.production

### Issue: Token expired
**Solution**: authService automatically refreshes tokens. Ensure refresh token logic is working

### Issue: API calls failing after deployment
**Solution**: Update EXPO_PUBLIC_API_BASE_URL to use HTTPS production URL

## Security Best Practices

1. **Never store sensitive data in AsyncStorage unencrypted**
   - JWT tokens are okay (they expire)
   - Never store exchange API keys directly

2. **Always use HTTPS in production**
   - Update all API URLs to use https://
   - Ensure SSL certificates are valid

3. **Handle logout properly**
   ```javascript
   await authService.logout();
   // Clear any cached data
   // Navigate to login screen
   ```

4. **Implement session timeout**
   - Add inactivity detection
   - Auto-logout after period of inactivity

## Migration Guide for Existing Users

If you have existing users with saved credentials:

1. **On first login after update**:
   - Prompt users to log in
   - Migrate their exchange credentials to encrypted storage
   - Clear old unencrypted data

2. **Sample migration code**:
   ```javascript
   const migrateUserData = async () => {
     const oldCredentials = await AsyncStorage.getItem('exchange_credentials');
     if (oldCredentials && authService.isLoggedIn()) {
       // Send to backend for encrypted storage
       await exchangeService.storeEncryptedCredentials(JSON.parse(oldCredentials));
       // Clear old storage
       await AsyncStorage.removeItem('exchange_credentials');
     }
   };
   ```

## Summary

The frontend is now configured to work with the secured backend. Key points:
- All sensitive endpoints require authentication
- Use environment variables for API URLs
- Handle authentication errors gracefully
- Ensure HTTPS in production
- Test thoroughly before deployment
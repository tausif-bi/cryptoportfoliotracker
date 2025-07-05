# Debug Guide for Strategies Screen

## What to Check

### 1. **In Your App Console (Metro/Expo)**
Look for these console logs:
- `Fetching strategies...`
- `API URL: http://...`
- `Response status: 200`
- `Strategies response: {...}`
- `Setting strategies: 6`
- `Strategies state updated: 6 strategies`

### 2. **If You See Network Errors**
Check if the URL is correct:
- Should be: `http://192.168.0.177:5000/api/strategies/list`
- NOT: `http://192.168.0.177:5000/api/api/strategies/list` (double /api)

### 3. **Common Issues**

**Issue: "Network request failed"**
- Backend server is not running
- IP address is wrong
- Firewall blocking connection

**Issue: "strategies.length is 0"**
- Response format might be different
- State not updating properly
- Error in parsing response

### 4. **Quick Test**
In your app's debug console (shake device or Cmd+D), run:
```javascript
fetch('http://192.168.0.177:5000/api/strategies/list')
  .then(r => r.json())
  .then(data => console.log('Direct fetch result:', data))
  .catch(e => console.log('Direct fetch error:', e))
```

### 5. **Force Refresh**
1. Pull down on the strategies screen to refresh
2. Should trigger `fetchStrategies()` again
3. Watch console for logs

### 6. **Check exchangeService.baseURL**
The issue might be with the baseURL. In debug console:
```javascript
console.log('ExchangeService baseURL:', exchangeService.baseURL)
```
Should be: `http://192.168.0.177:5000/api`

If it's wrong, the URL becomes:
- Wrong: `http://192.168.0.177:5000/api/api/strategies/list`
- Right: `http://192.168.0.177:5000/api/strategies/list`

### 7. **Emergency Fix**
If baseURL is wrong, temporarily hardcode in StrategiesScreen.js:
```javascript
const response = await fetch('http://192.168.0.177:5000/api/strategies/list');
```

## Expected Flow
1. App loads → `useEffect` runs → `fetchStrategies()` called
2. Fetch request to backend → Returns 6 strategies
3. `setStrategies(data.strategies)` → Updates state
4. Re-render → Shows strategy cards

Check your console logs and let me know what you see!
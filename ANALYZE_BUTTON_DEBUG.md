# Debug Guide: Analyze Button Not Working

## What Should Happen
When you click "Analyze BTC/USDT":
1. Console shows: "Running strategy analysis for: trendline_breakout" (or other strategy ID)
2. Either:
   - Shows "Login Required" alert (if not logged in)
   - Makes API request and shows results (if logged in)

## Check Console Logs
When you click the button, look for these logs:
- `Running strategy analysis for: [strategy_id]`
- `User logged in status: true/false`
- `Auth token: Present/Missing`

## Common Issues

### 1. **No Console Logs = Button Handler Not Called**
- The button might be disabled
- Touch event not registering

### 2. **"User logged in status: false"**
You need to log in first:
1. Go to Profile tab
2. Log in with your credentials
3. Return to Strategies tab
4. Try analyzing again

### 3. **"Auth token: Missing"**
The auth token wasn't saved properly:
1. Log out and log in again
2. Check if login was successful

## Quick Test
In the app's debug console (shake device), run:
```javascript
// Check if logged in
authService.isLoggedIn()

// Check auth token
authService.accessToken

// Manually trigger analysis
runStrategyAnalysis('trendline_breakout')
```

## Temporary Fix
If nothing works, try this in StrategiesScreen.js:

Replace the onPress handler:
```javascript
onPress={() => {
  console.log('Button pressed!');
  Alert.alert('Debug', `Would analyze ${strategy.id}`);
  runStrategyAnalysis(strategy.id);
}}
```

This will at least confirm the button is working.

## Expected Flow
1. Click "Analyze BTC/USDT"
2. Console: "Running strategy analysis for: trendline_breakout"
3. If not logged in → Alert "Login Required"
4. If logged in → API request → Show loading → Display results

Let me know what you see in the console!
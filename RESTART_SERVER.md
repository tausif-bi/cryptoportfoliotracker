# Server Restart Instructions

The strategies endpoint has been updated to be public (no authentication required), but the Flask server may need to reload the changes.

## Option 1: Auto-reload (Should happen automatically)
Flask is running in debug mode, so it should automatically detect the file changes and reload. Look for this message in your terminal:
```
* Detected change in 'app.py', reloading
* Restarting with stat
```

## Option 2: Manual Restart
If auto-reload didn't work:

1. **Stop the server**: Press `Ctrl+C` in the terminal where Flask is running
2. **Start it again**:
   ```bash
   cd crypto-ai-backend
   python app.py
   ```

## Option 3: Force Kill and Restart
If the server is stuck:

1. **Find the process**:
   ```bash
   # On Windows
   netstat -ano | findstr :5000
   ```

2. **Kill the process**:
   ```bash
   # On Windows (replace PID with the actual process ID)
   taskkill /PID <PID> /F
   ```

3. **Start fresh**:
   ```bash
   cd crypto-ai-backend
   python app.py
   ```

## Verify It's Working

After restart, test the endpoint:
```bash
curl http://192.168.0.177:5000/api/strategies/list
```

Should return:
```json
{
  "success": true,
  "strategies": [...]
}
```

## In Your App

1. Pull down to refresh on the Strategies screen
2. You should now see the list of strategies
3. No login required to view strategies
4. Login required only when running analysis
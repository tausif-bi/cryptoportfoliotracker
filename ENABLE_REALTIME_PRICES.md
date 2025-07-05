# How to Enable Real-Time Price Updates

Your app's backend already supports real-time price updates via WebSocket, but the frontend needs to be connected.

## 1. Install Dependencies
```bash
cd crypto-portfolio
npm install socket.io-client
```

## 2. Use Real-Time Prices in Your Screens

### Example: Update HomeScreen with Real-Time Prices

```javascript
import { useRealTimePrices } from '../hooks/useRealTimePrices';

// Inside your component
const holdings = portfolio?.holdings || [];
const symbols = holdings.map(h => `${h.coin}/USDT`);
const { prices, connected } = useRealTimePrices(symbols);

// In your render
{holdings.map(holding => {
  const symbol = `${holding.coin}/USDT`;
  const realtimePrice = prices[symbol];
  
  return (
    <View key={holding.coin}>
      <Text>{holding.coin}</Text>
      <Text>
        ${realtimePrice ? realtimePrice.price.toFixed(2) : holding.price.toFixed(2)}
        {connected && realtimePrice && (
          <Text style={{ fontSize: 10, color: '#00ff88' }}> LIVE</Text>
        )}
      </Text>
      {realtimePrice && (
        <Text style={{ color: realtimePrice.change24h > 0 ? '#00ff88' : '#ff4444' }}>
          {realtimePrice.change24h > 0 ? '+' : ''}{realtimePrice.change24h.toFixed(2)}%
        </Text>
      )}
    </View>
  );
})}
```

## 3. Real-Time Features Available

### Price Updates (Every 30 seconds)
- Current price
- 24h change percentage
- 24h volume
- 24h high/low
- Update timestamp
- Data source (binance/coinbase)

### WebSocket Events
- `connect` - Connected to server
- `connected` - Authenticated successfully
- `price_update` - New price data
- `portfolio_summary` - Real-time portfolio value
- `error` - Error messages

## 4. Test Real-Time Updates

1. **Start your backend** with WebSocket support
2. **Login** to your app (WebSocket requires auth)
3. **Go to Home/Portfolio screen**
4. **Watch for "LIVE" indicator** next to prices
5. **Prices update automatically** every 30 seconds

## 5. Advanced Usage

### Subscribe to Specific Symbols
```javascript
// In any component
import { websocketService } from '../services/websocketService';

useEffect(() => {
  const handleBTCPrice = (data) => {
    console.log('BTC Price:', data.price);
  };
  
  websocketService.subscribeToPrices(['BTC/USDT'], handleBTCPrice);
  
  return () => {
    websocketService.unsubscribeFromPrices(['BTC/USDT'], handleBTCPrice);
  };
}, []);
```

### Get Real-Time Portfolio Summary
```javascript
websocketService.getPortfolioSummary((summary) => {
  console.log('Total Value:', summary.total_value);
  console.log('Holdings:', summary.holdings);
});
```

## Backend Configuration

The backend updates prices from:
- **Primary**: Binance (most pairs)
- **Backup**: Coinbase (BTC, ETH)
- **Frequency**: Every 30 seconds
- **Storage**: Price history saved every 5 minutes

## Production Considerations

1. **Change WebSocket URL** for production:
   ```javascript
   // In websocketService.js
   this.socket = io('https://api.yourdomain.com', {
     // ... options
   });
   ```

2. **Update CORS** in backend for production domain

3. **Use WSS (Secure WebSocket)** with HTTPS

4. **Handle Reconnection** - Already implemented with auto-reconnect

The real-time system is ready to use - just install socket.io-client and start using it!
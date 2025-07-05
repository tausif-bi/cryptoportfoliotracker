# Adding Real-Time Prices - Step by Step

## 1. First, install socket.io-client

Open a terminal in your crypto-portfolio directory and run:

```bash
cd crypto-portfolio
npm install socket.io-client
```

## 2. Files Being Created/Updated

1. **websocketService.js** - WebSocket connection service
2. **useRealTimePrices.js** - React hook for real-time prices
3. **PortfolioScreen.js** - Updated with live prices
4. **HomeScreen.js** - Updated with live portfolio value

## 3. After Installation

Once you've installed socket.io-client, the real-time features will work automatically!

- Portfolio tab will show live prices with a "LIVE" indicator
- Home tab will update total portfolio value in real-time
- Prices update every 30 seconds from exchanges

## 4. What You'll See

- 🟢 Green "LIVE" indicator next to real-time prices
- 📈 Price changes with color coding (green/red)
- 💰 Portfolio value updating automatically
- ⚡ No need to refresh!
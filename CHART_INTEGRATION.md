# Interactive Chart Integration Guide

This guide explains how to integrate the new interactive chart APIs with the React Native frontend.

## Chart API Endpoints

### 1. OHLCV Chart Data
```
GET /api/charts/ohlcv/{symbol}?timeframe=1h&limit=500
```

Returns candlestick and volume data for interactive charts.

**Response Format:**
```json
{
  "success": true,
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "source": "exchange",
  "data": {
    "candlestick": [
      {
        "x": 1703673600000,
        "o": 42000.5,
        "h": 42500.0,
        "l": 41800.0,
        "c": 42200.0
      }
    ],
    "volume": [
      {
        "x": 1703673600000,
        "y": 1523.45
      }
    ]
  },
  "statistics": {
    "current_price": 42200.0,
    "price_change": 200.0,
    "price_change_percent": 0.48,
    "high_24h": 42500.0,
    "low_24h": 41800.0,
    "volume_24h": 35432.15,
    "data_points": 500
  }
}
```

### 2. Strategy Chart Data
```
GET /api/charts/strategy/{symbol}?timeframe=1h&limit=500&strategy=trendline_breakout
```

Returns chart data with trading signals and trendlines.

**Additional Strategy Data:**
```json
{
  "strategy": {
    "name": "trendline_breakout",
    "signals": {
      "buy_signals": [
        {
          "x": 1703673600000,
          "y": 42150.0,
          "type": "support_breakout"
        }
      ],
      "sell_signals": [
        {
          "x": 1703677200000,
          "y": 42450.0,
          "type": "resistance_rejection"
        }
      ],
      "trendlines": [
        {
          "type": "support",
          "points": [
            {"x": 1703650000000, "y": 41800.0},
            {"x": 1703673600000, "y": 42000.0}
          ],
          "color": "#44ff44"
        }
      ]
    }
  }
}
```

### 3. Portfolio Performance Chart
```
GET /api/charts/portfolio/{portfolio_id}?timeframe=1d
```

Returns portfolio value over time based on trade history.

### 4. Supported Symbols
```
GET /api/charts/supported-symbols
```

Returns available symbols, timeframes, and strategies.

## Frontend Integration

### Recommended Chart Libraries

1. **react-native-chart-kit** (Current)
   - Simple to use
   - Limited customization
   - Good for basic charts

2. **Victory Native** (Recommended upgrade)
   - More interactive features
   - Better customization
   - Supports real-time updates

3. **React Native SVG Charts**
   - Lightweight
   - Highly customizable
   - Good performance

### Sample Integration with Victory Native

```javascript
// Install: npm install victory-native react-native-svg

import React, { useState, useEffect } from 'react';
import { VictoryCandlestick, VictoryChart, VictoryArea, VictoryScatter } from 'victory-native';
import { View, Dimensions } from 'react-native';

const InteractiveChart = ({ symbol, timeframe = '1h' }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchChartData();
  }, [symbol, timeframe]);

  const fetchChartData = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `${API_BASE_URL}/api/charts/strategy/${symbol}?timeframe=${timeframe}&strategy=trendline_breakout`,
        {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      const data = await response.json();
      if (data.success) {
        setChartData(data);
      }
    } catch (error) {
      console.error('Error fetching chart data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !chartData) {
    return <LoadingIndicator />;
  }

  const screenWidth = Dimensions.get('window').width;

  return (
    <View style={{ height: 400 }}>
      <VictoryChart
        width={screenWidth - 20}
        height={300}
        padding={{ left: 50, top: 20, right: 50, bottom: 50 }}
        scale={{ x: 'time' }}
      >
        {/* Candlestick Chart */}
        <VictoryCandlestick
          data={chartData.data.candlestick}
          candleColors={{ positive: "#00ff88", negative: "#ff4444" }}
          wickStrokeWidth={1}
          candleWidth={5}
        />
        
        {/* Buy Signals */}
        <VictoryScatter
          data={chartData.strategy.signals.buy_signals}
          size={6}
          style={{
            data: { fill: "#00ff88" }
          }}
          symbol="triangleUp"
        />
        
        {/* Sell Signals */}
        <VictoryScatter
          data={chartData.strategy.signals.sell_signals}
          size={6}
          style={{
            data: { fill: "#ff4444" }
          }}
          symbol="triangleDown"
        />
      </VictoryChart>
      
      {/* Volume Chart */}
      <VictoryChart
        width={screenWidth - 20}
        height={100}
        padding={{ left: 50, top: 10, right: 50, bottom: 30 }}
        scale={{ x: 'time' }}
      >
        <VictoryArea
          data={chartData.data.volume}
          style={{
            data: { fill: "#8884d8", opacity: 0.6 }
          }}
        />
      </VictoryChart>
    </View>
  );
};

export default InteractiveChart;
```

### WebSocket Integration for Real-time Updates

```javascript
import io from 'socket.io-client';

const useRealTimeChart = (symbol, onPriceUpdate) => {
  useEffect(() => {
    // Get WebSocket info
    const getWebSocketInfo = async () => {
      const response = await fetch(`${API_BASE_URL}/api/websocket/info`, {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });
      const data = await response.json();
      
      if (data.success) {
        connectWebSocket(data.websocket_url, data.token);
      }
    };

    const connectWebSocket = (url, token) => {
      const socket = io(url, {
        query: { token }
      });

      socket.on('connected', (data) => {
        console.log('WebSocket connected:', data);
        
        // Subscribe to price updates
        socket.emit('subscribe_prices', {
          symbols: [symbol]
        });
      });

      socket.on('price_update', (priceData) => {
        if (priceData.symbol === symbol) {
          onPriceUpdate(priceData);
        }
      });

      return socket;
    };

    const socket = getWebSocketInfo();
    
    return () => {
      if (socket) {
        socket.disconnect();
      }
    };
  }, [symbol]);
};
```

## Migration from Static Charts

### Current Implementation
- Charts generated as base64 images by matplotlib
- Static images returned in API responses
- Limited interactivity
- Slow rendering

### New Implementation Benefits
1. **Interactive Charts**: Zoom, pan, touch interactions
2. **Real-time Updates**: Live price feeds via WebSocket
3. **Better Performance**: Client-side rendering
4. **Responsive Design**: Adapts to different screen sizes
5. **Customizable**: Easy to modify appearance and behavior

### Migration Steps

1. **Update Package Dependencies**
   ```bash
   npm install victory-native react-native-svg
   # or
   npm install react-native-svg-charts
   ```

2. **Replace Chart Components**
   - Replace static image displays with interactive chart components
   - Update chart data fetching to use new API endpoints
   - Add real-time WebSocket integration

3. **Update Styling**
   - Remove image-based chart styling
   - Add chart-specific styling for Victory Native components
   - Implement dark/light theme support

4. **Test Integration**
   - Verify chart data loads correctly
   - Test real-time price updates
   - Ensure responsive behavior on different devices

## Chart Customization Options

### Colors and Themes
```javascript
const chartTheme = {
  candlestick: {
    positive: "#00ff88",  // Green for bullish candles
    negative: "#ff4444"   // Red for bearish candles
  },
  signals: {
    buy: "#00ff88",       // Green for buy signals
    sell: "#ff4444"       // Red for sell signals
  },
  trendlines: {
    support: "#44ff44",   // Green for support lines
    resistance: "#ff4444" // Red for resistance lines
  },
  volume: "#8884d8",      // Blue for volume bars
  background: "#1a1a1a",  // Dark background
  text: "#ffffff"         // White text
};
```

### Performance Optimization
1. **Data Limiting**: Limit chart data points (500-1000 max)
2. **Lazy Loading**: Load chart data only when screen is visible
3. **Caching**: Cache chart data for recently viewed symbols
4. **Debouncing**: Debounce real-time updates to avoid excessive re-renders

This new chart system provides a much more professional and interactive experience compared to static matplotlib images.
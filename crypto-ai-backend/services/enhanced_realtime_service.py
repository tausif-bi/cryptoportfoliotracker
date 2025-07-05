"""
Enhanced real-time price service with more frequent updates and multiple exchanges
"""
import ccxt
import asyncio
import threading
from datetime import datetime
import time
import json
from decimal import Decimal

class EnhancedRealtimeService:
    """Enhanced real-time price service using CCXT"""
    
    def __init__(self, socketio, update_interval=5):
        self.socketio = socketio
        self.update_interval = update_interval  # Update every 5 seconds instead of 30
        self.exchanges = {}
        self.price_cache = {}
        self.running = False
        
        # Initialize multiple exchanges for better coverage
        self.init_exchanges()
    
    def init_exchanges(self):
        """Initialize multiple exchanges for redundancy and coverage"""
        
        # Binance - Most liquid, most pairs
        try:
            self.exchanges['binance'] = ccxt.binance({
                'enableRateLimit': True,
                'rateLimit': 50,  # 20 requests per second
                'options': {
                    'defaultType': 'spot',
                }
            })
            print("✓ Binance initialized")
        except Exception as e:
            print(f"✗ Binance failed: {e}")
        
        # KuCoin - Good for altcoins
        try:
            self.exchanges['kucoin'] = ccxt.kucoin({
                'enableRateLimit': True,
                'rateLimit': 100,
            })
            print("✓ KuCoin initialized")
        except Exception as e:
            print(f"✗ KuCoin failed: {e}")
        
        # Bybit - Fast updates
        try:
            self.exchanges['bybit'] = ccxt.bybit({
                'enableRateLimit': True,
                'rateLimit': 50,
                'options': {
                    'defaultType': 'spot',
                }
            })
            print("✓ Bybit initialized")
        except Exception as e:
            print(f"✗ Bybit failed: {e}")
        
        # Gate.io - Wide token selection
        try:
            self.exchanges['gateio'] = ccxt.gateio({
                'enableRateLimit': True,
                'rateLimit': 100,
            })
            print("✓ Gate.io initialized")
        except Exception as e:
            print(f"✗ Gate.io failed: {e}")
    
    async def fetch_ticker_async(self, exchange, symbol):
        """Fetch ticker data asynchronously"""
        try:
            # Use CCXT's async support if available
            if hasattr(exchange, 'fetch_ticker'):
                ticker = exchange.fetch_ticker(symbol)
                return {
                    'symbol': symbol,
                    'price': float(ticker['last']) if ticker['last'] else 0,
                    'bid': float(ticker['bid']) if ticker['bid'] else 0,
                    'ask': float(ticker['ask']) if ticker['ask'] else 0,
                    'change_24h': float(ticker['percentage']) if ticker['percentage'] else 0,
                    'volume_24h': float(ticker['quoteVolume']) if ticker['quoteVolume'] else 0,
                    'high_24h': float(ticker['high']) if ticker['high'] else 0,
                    'low_24h': float(ticker['low']) if ticker['low'] else 0,
                    'timestamp': ticker['timestamp'],
                    'exchange': exchange.id
                }
        except Exception as e:
            return None
    
    def get_best_price(self, symbol):
        """Get best price from all exchanges"""
        prices = []
        
        # Try each exchange
        for exchange_name, exchange in self.exchanges.items():
            try:
                # Check if exchange supports this symbol
                if hasattr(exchange, 'markets') and not exchange.markets:
                    exchange.load_markets()
                
                if symbol in exchange.markets:
                    ticker_data = asyncio.run(self.fetch_ticker_async(exchange, symbol))
                    if ticker_data:
                        prices.append(ticker_data)
            except:
                pass
        
        if not prices:
            return None
        
        # Return price with highest volume (most reliable)
        best_price = max(prices, key=lambda x: x['volume_24h'])
        
        # Add aggregated data
        best_price['prices_from_exchanges'] = len(prices)
        best_price['price_range'] = {
            'min': min(p['price'] for p in prices),
            'max': max(p['price'] for p in prices),
            'avg': sum(p['price'] for p in prices) / len(prices)
        }
        
        return best_price
    
    def fetch_orderbook_data(self, symbol, limit=10):
        """Fetch order book for more detailed market data"""
        try:
            exchange = self.exchanges.get('binance')  # Use most liquid exchange
            if exchange:
                orderbook = exchange.fetch_order_book(symbol, limit)
                return {
                    'bids': orderbook['bids'][:5],  # Top 5 bids
                    'asks': orderbook['asks'][:5],  # Top 5 asks
                    'spread': float(orderbook['asks'][0][0] - orderbook['bids'][0][0]) if orderbook['asks'] and orderbook['bids'] else 0,
                    'timestamp': orderbook['timestamp']
                }
        except:
            return None
    
    def fetch_recent_trades(self, symbol, limit=20):
        """Fetch recent trades for market sentiment"""
        try:
            exchange = self.exchanges.get('binance')
            if exchange:
                trades = exchange.fetch_trades(symbol, limit=limit)
                
                # Analyze trades
                buy_volume = sum(t['amount'] for t in trades if t['side'] == 'buy')
                sell_volume = sum(t['amount'] for t in trades if t['side'] == 'sell')
                
                return {
                    'recent_trades': len(trades),
                    'buy_volume': buy_volume,
                    'sell_volume': sell_volume,
                    'buy_pressure': (buy_volume / (buy_volume + sell_volume) * 100) if (buy_volume + sell_volume) > 0 else 50,
                    'last_price': trades[0]['price'] if trades else 0,
                    'last_side': trades[0]['side'] if trades else 'unknown'
                }
        except:
            return None
    
    def get_multi_timeframe_data(self, symbol):
        """Get OHLCV data for multiple timeframes"""
        timeframes = {
            '1m': 60,      # Last 60 1-minute candles
            '5m': 60,      # Last 60 5-minute candles  
            '15m': 48,     # Last 48 15-minute candles
            '1h': 24,      # Last 24 hourly candles
            '4h': 24,      # Last 24 4-hour candles
            '1d': 30       # Last 30 daily candles
        }
        
        multi_tf_data = {}
        exchange = self.exchanges.get('binance')
        
        if exchange:
            for tf, limit in timeframes.items():
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=limit)
                    if ohlcv:
                        # Calculate simple metrics
                        closes = [c[4] for c in ohlcv]
                        multi_tf_data[tf] = {
                            'current': closes[-1],
                            'change': ((closes[-1] - closes[0]) / closes[0] * 100),
                            'high': max(closes),
                            'low': min(closes),
                            'sma': sum(closes) / len(closes)
                        }
                except:
                    pass
        
        return multi_tf_data

# Usage example:
"""
# In your Flask app:
enhanced_service = EnhancedRealtimeService(socketio, update_interval=5)

# Get comprehensive real-time data
symbol = 'BTC/USDT'
price_data = enhanced_service.get_best_price(symbol)
orderbook = enhanced_service.fetch_orderbook_data(symbol)
trades = enhanced_service.fetch_recent_trades(symbol)
multi_tf = enhanced_service.get_multi_timeframe_data(symbol)

# Broadcast comprehensive update
socketio.emit('enhanced_price_update', {
    'symbol': symbol,
    'price': price_data,
    'orderbook': orderbook,
    'market_sentiment': trades,
    'timeframes': multi_tf,
    'timestamp': datetime.utcnow().isoformat()
})
"""
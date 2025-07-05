"""
Direct API endpoints for real-time CCXT price data
"""
from flask import jsonify
import ccxt
from functools import lru_cache
from datetime import datetime, timedelta

# Cache exchange instances
@lru_cache(maxsize=10)
def get_exchange(exchange_name='binance'):
    """Get or create exchange instance"""
    exchanges = {
        'binance': ccxt.binance,
        'kucoin': ccxt.kucoin,
        'bybit': ccxt.bybit,
        'gateio': ccxt.gateio,
        'okx': ccxt.okx,
        'huobi': ccxt.huobi,
        'kraken': ccxt.kraken
    }
    
    if exchange_name in exchanges:
        return exchanges[exchange_name]({
            'enableRateLimit': True,
            'timeout': 10000
        })
    return None

def register_realtime_routes(app):
    """Register real-time price routes"""
    
    @app.route('/api/realtime/price/<symbol>')
    def get_realtime_price(symbol):
        """Get real-time price for a single symbol"""
        # Replace URL-safe character
        symbol = symbol.replace('-', '/')
        
        try:
            exchange = get_exchange('binance')
            ticker = exchange.fetch_ticker(symbol)
            
            return jsonify({
                'success': True,
                'data': {
                    'symbol': symbol,
                    'price': ticker['last'],
                    'bid': ticker['bid'],
                    'ask': ticker['ask'],
                    'spread': ticker['ask'] - ticker['bid'] if ticker['ask'] and ticker['bid'] else 0,
                    'change_24h': ticker['percentage'],
                    'volume_24h': ticker['quoteVolume'],
                    'high_24h': ticker['high'],
                    'low_24h': ticker['low'],
                    'timestamp': ticker['timestamp'],
                    'datetime': ticker['datetime']
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
    
    @app.route('/api/realtime/prices', methods=['POST'])
    def get_multiple_prices():
        """Get real-time prices for multiple symbols"""
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        results = {}
        exchange = get_exchange('binance')
        
        for symbol in symbols:
            try:
                ticker = exchange.fetch_ticker(symbol)
                results[symbol] = {
                    'price': ticker['last'],
                    'change_24h': ticker['percentage'],
                    'volume_24h': ticker['quoteVolume'],
                    'timestamp': ticker['timestamp']
                }
            except:
                results[symbol] = None
        
        return jsonify({
            'success': True,
            'data': results
        })
    
    @app.route('/api/realtime/orderbook/<symbol>')
    def get_orderbook(symbol):
        """Get real-time order book data"""
        symbol = symbol.replace('-', '/')
        
        try:
            exchange = get_exchange('binance')
            orderbook = exchange.fetch_order_book(symbol, limit=20)
            
            return jsonify({
                'success': True,
                'data': {
                    'symbol': symbol,
                    'bids': orderbook['bids'][:10],
                    'asks': orderbook['asks'][:10],
                    'spread': orderbook['asks'][0][0] - orderbook['bids'][0][0] if orderbook['asks'] and orderbook['bids'] else 0,
                    'spread_percentage': ((orderbook['asks'][0][0] - orderbook['bids'][0][0]) / orderbook['bids'][0][0] * 100) if orderbook['asks'] and orderbook['bids'] else 0,
                    'timestamp': orderbook['timestamp']
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
    
    @app.route('/api/realtime/trades/<symbol>')
    def get_recent_trades(symbol):
        """Get recent trades for market sentiment"""
        symbol = symbol.replace('-', '/')
        
        try:
            exchange = get_exchange('binance')
            trades = exchange.fetch_trades(symbol, limit=50)
            
            # Analyze trades
            buy_trades = [t for t in trades if t['side'] == 'buy']
            sell_trades = [t for t in trades if t['side'] == 'sell']
            
            buy_volume = sum(t['amount'] for t in buy_trades)
            sell_volume = sum(t['amount'] for t in sell_trades)
            total_volume = buy_volume + sell_volume
            
            return jsonify({
                'success': True,
                'data': {
                    'symbol': symbol,
                    'recent_trades': len(trades),
                    'buy_trades': len(buy_trades),
                    'sell_trades': len(sell_trades),
                    'buy_volume': buy_volume,
                    'sell_volume': sell_volume,
                    'buy_pressure': (buy_volume / total_volume * 100) if total_volume > 0 else 50,
                    'avg_trade_size': total_volume / len(trades) if trades else 0,
                    'last_trade': {
                        'price': trades[0]['price'],
                        'amount': trades[0]['amount'],
                        'side': trades[0]['side'],
                        'timestamp': trades[0]['timestamp']
                    } if trades else None
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
    
    @app.route('/api/realtime/ticker/<symbol>')
    def get_full_ticker(symbol):
        """Get comprehensive ticker data from multiple exchanges"""
        symbol = symbol.replace('-', '/')
        
        tickers = []
        for exchange_name in ['binance', 'kucoin', 'bybit']:
            try:
                exchange = get_exchange(exchange_name)
                if exchange:
                    ticker = exchange.fetch_ticker(symbol)
                    tickers.append({
                        'exchange': exchange_name,
                        'price': ticker['last'],
                        'volume': ticker['quoteVolume'],
                        'timestamp': ticker['timestamp']
                    })
            except:
                pass
        
        if tickers:
            # Aggregate data
            prices = [t['price'] for t in tickers]
            volumes = [t['volume'] for t in tickers]
            
            return jsonify({
                'success': True,
                'data': {
                    'symbol': symbol,
                    'aggregated': {
                        'price_avg': sum(prices) / len(prices),
                        'price_min': min(prices),
                        'price_max': max(prices),
                        'total_volume': sum(volumes),
                        'exchanges_count': len(tickers)
                    },
                    'exchanges': tickers
                }
            })
        
        return jsonify({
            'success': False,
            'error': 'No data available'
        }), 404

# Add these routes to your app.py:
# register_realtime_routes(app)
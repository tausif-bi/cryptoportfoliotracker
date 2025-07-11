import pandas as pd
import numpy as np
import ccxt
import ta
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
import random
import os
import json


class PortfolioAnalyzer:
    def __init__(self):
        self.exchange = None
        self.scaler = StandardScaler()
        self.model = None
        
    def initialize_exchange(self, exchange_name='binance'):
        """Initialize CCXT exchange for data fetching"""
        self.exchange = getattr(ccxt, exchange_name)()
        
    def fetch_ohlcv_data(self, symbol, timeframe='1d', limit=100):
        """Fetch historical OHLCV data"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
    
    def calculate_technical_indicators(self, df):
        """Calculate technical indicators for analysis"""
        # Moving averages
        df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
        df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
        df['ema_12'] = ta.trend.ema_indicator(df['close'], window=12)
        df['ema_26'] = ta.trend.ema_indicator(df['close'], window=26)
        
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
        
        # MACD
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(df['close'])
        df['bb_upper'] = bollinger.bollinger_hband()
        df['bb_lower'] = bollinger.bollinger_lband()
        df['bb_middle'] = bollinger.bollinger_mavg()
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        return df
    
    def analyze_portfolio(self, holdings, prices):
        """Analyze portfolio and provide insights"""
        insights = []
        recommendations = []
        
        # Calculate portfolio metrics
        total_value = sum(h.get('usdValue', 0) for h in holdings)
        
        # Calculate allocations if not provided
        for h in holdings:
            if 'allocation' not in h and total_value > 0:
                h['allocation'] = (h.get('usdValue', 0) / total_value) * 100
        
        # Analyze concentration risk
        max_allocation = max(h.get('allocation', 0) for h in holdings) if holdings else 0
        if max_allocation > 40:
            insights.append({
                'type': 'warning',
                'message': f'High concentration risk: {max_allocation:.1f}% in single asset',
                'severity': 'high'
            })
            recommendations.append('Consider diversifying to reduce concentration risk')
        
        # Analyze performance
        top_performers = [h for h in holdings if h.get('change24h', 0) > 5]
        poor_performers = [h for h in holdings if h.get('change24h', 0) < -5]
        
        if top_performers:
            insights.append({
                'type': 'positive',
                'message': f'{len(top_performers)} assets showing strong performance (>5% daily gain)',
                'severity': 'info'
            })
        
        if poor_performers:
            insights.append({
                'type': 'negative',
                'message': f'{len(poor_performers)} assets underperforming (<-5% daily loss)',
                'severity': 'medium'
            })
        
        return {
            'insights': insights,
            'recommendations': recommendations,
            'risk_score': self.calculate_risk_score(holdings),
            'diversity_score': self.calculate_diversity_score(holdings)
        }
    
    def calculate_risk_score(self, holdings):
        """Calculate portfolio risk score (0-100)"""
        # Factors: concentration, volatility, asset types
        max_allocation = max(h['allocation'] for h in holdings)
        concentration_risk = max_allocation / 100
        
        # Simple risk calculation
        risk_score = concentration_risk * 50 + 25  # Base risk
        
        return min(100, max(0, risk_score))
    
    def calculate_diversity_score(self, holdings):
        """Calculate portfolio diversity score (0-100)"""
        n_assets = len(holdings)
        
        # Calculate Herfindahl Index
        hhi = sum((h['allocation'] / 100) ** 2 for h in holdings)
        
        # Convert to diversity score
        diversity_score = (1 - hhi) * 100
        
        # Bonus for number of assets
        if n_assets > 10:
            diversity_score = min(100, diversity_score + 10)
        
        return diversity_score
    
    def predict_price_movement(self, symbol, timeframe='1h'):
        """Predict price movement using ML model"""
        try:
            # Fetch historical data
            df = self.fetch_ohlcv_data(symbol, timeframe, limit=200)
            if df is None:
                return None
            
            # Calculate indicators
            df = self.calculate_technical_indicators(df)
            
            # Prepare features
            feature_cols = ['rsi', 'macd', 'macd_signal', 'volume_sma']
            df = df.dropna()
            
            if len(df) < 50:
                return None
            
            # Simple prediction based on technical indicators
            last_row = df.iloc[-1]
            
            prediction = {
                'symbol': symbol,
                'current_price': last_row['close'],
                'rsi': last_row['rsi'],
                'trend': 'bullish' if last_row['sma_20'] > last_row['sma_50'] else 'bearish',
                'signal': self._generate_signal(last_row),
                'confidence': self._calculate_confidence(last_row)
            }
            
            return prediction
        except Exception as e:
            print(f"Error in prediction: {e}")
            return None
    
    def _generate_signal(self, row):
        """Generate trading signal based on indicators"""
        signals = []
        
        # RSI signals
        if row['rsi'] < 30:
            signals.append('oversold')
        elif row['rsi'] > 70:
            signals.append('overbought')
        
        # MACD signals
        if row['macd'] > row['macd_signal']:
            signals.append('bullish_crossover')
        else:
            signals.append('bearish_crossover')
        
        # Bollinger Band signals
        if row['close'] < row['bb_lower']:
            signals.append('bb_oversold')
        elif row['close'] > row['bb_upper']:
            signals.append('bb_overbought')
        
        # Determine overall signal
        if 'oversold' in signals or 'bb_oversold' in signals:
            return 'BUY'
        elif 'overbought' in signals or 'bb_overbought' in signals:
            return 'SELL'
        elif 'bullish_crossover' in signals:
            return 'BUY'
        elif 'bearish_crossover' in signals:
            return 'SELL'
        else:
            return 'HOLD'
    
    def _calculate_confidence(self, row):
        """Calculate confidence score for prediction"""
        confidence = 50  # Base confidence
        
        # RSI confidence
        if row['rsi'] < 20 or row['rsi'] > 80:
            confidence += 20
        elif row['rsi'] < 30 or row['rsi'] > 70:
            confidence += 10
        
        # MACD confidence
        macd_diff_strength = abs(row['macd_diff'])
        if macd_diff_strength > 0.5:
            confidence += 15
        
        # Volume confidence
        if row['volume'] > row['volume_sma'] * 1.5:
            confidence += 15
        
        return min(100, confidence)


# Utility functions that were associated with PortfolioAnalyzer

def fetch_real_ohlcv_data():
    """Fetch real OHLCV data from public exchange API"""
    try:
        # Use Binance public API (no authentication needed)
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })
        
        print("Fetching real market data for synthetic trades...")
        
        # Fetch OHLCV data for multiple symbols
        timeframe = '1h'  # 1 hour candles
        limit = 500  # Reduced from 1000 to avoid potential issues
        
        ohlcv_data = {}
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT']
        
        for symbol in symbols:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                if ohlcv and len(ohlcv) > 0:
                    ohlcv_data[symbol] = ohlcv
                    print(f"Fetched {len(ohlcv)} candles for {symbol}")
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                continue
        
        if len(ohlcv_data) == 0:
            print("No OHLCV data could be fetched")
            return None
            
        return ohlcv_data
    except Exception as e:
        print(f"Error initializing exchange or fetching OHLCV data: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_synthetic_trades(num_trades=1000):
    """Generate fallback synthetic trades"""
    try:
        trades = []
        
        # Define trading pairs and their weights
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT', 'MATIC/USDT', 'LINK/USDT', 'AVAX/USDT', 'XRP/USDT']
        
        # Estimated prices for fallback
        fallback_prices = {
            'BTC/USDT': 68000,
            'ETH/USDT': 3800,
            'BNB/USDT': 450,
            'SOL/USDT': 145,
            'ADA/USDT': 0.45,
            'DOT/USDT': 7.5,
            'MATIC/USDT': 0.75,
            'LINK/USDT': 15,
            'AVAX/USDT': 40,
            'XRP/USDT': 0.52
        }
        
        trade_frequency = {
            'BTC/USDT': 0.25,
            'ETH/USDT': 0.20,
            'BNB/USDT': 0.10,
            'SOL/USDT': 0.10,
            'ADA/USDT': 0.08,
            'DOT/USDT': 0.07,
            'MATIC/USDT': 0.07,
            'LINK/USDT': 0.05,
            'AVAX/USDT': 0.05,
            'XRP/USDT': 0.03
        }
        
        # Generate cumulative frequencies
        cumulative_freq = []
        cumulative = 0
        symbol_list = []
        for symbol, freq in trade_frequency.items():
            cumulative += freq
            cumulative_freq.append(cumulative)
            symbol_list.append(symbol)
        
        # Time range for trades (last 30 days)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        
        for i in range(num_trades):
            # Random timestamp within the range
            random_time = start_time + timedelta(seconds=random.randint(0, int((end_time - start_time).total_seconds())))
            trade_timestamp = int(random_time.timestamp() * 1000)
            
            # Weighted random symbol selection
            rand_val = random.random()
            symbol_index = 0
            for j, cum_freq in enumerate(cumulative_freq):
                if rand_val <= cum_freq:
                    symbol_index = j
                    break
            
            symbol = symbol_list[symbol_index]
            
            # Get price with some variation
            base_price = fallback_prices[symbol]
            price = base_price * random.uniform(0.9, 1.1)
            side = random.choice(['buy', 'sell'])
            
            # Determine amount based on symbol
            if 'BTC' in symbol:
                amount = random.triangular(0.001, 0.5, 0.01)
            elif 'ETH' in symbol:
                amount = random.triangular(0.01, 5, 0.5)
            else:
                amount = random.triangular(1, 100, 10)
            
            cost = price * amount
            
            trade = {
                'id': f'trade_{i}_{int(trade_timestamp)}',
                'orderId': f'order_{i}_{int(trade_timestamp)}',
                'symbol': symbol,
                'side': side,
                'price': round(price, 6),
                'amount': round(amount, 8),
                'cost': round(cost, 2),
                'fee': {
                    'cost': cost * 0.001,
                    'currency': 'USDT',
                    'rate': 0.001
                },
                'timestamp': int(trade_timestamp),
                'datetime': random_time.isoformat(),
                'type': 'limit',
                'takerOrMaker': 'taker',
                'info': {
                    'exchange': 'demo',
                    'pair': symbol.replace('/', '_')
                }
            }
            
            trades.append(trade)
        
        # Sort by timestamp (newest first)
        trades.sort(key=lambda x: x['timestamp'], reverse=True)
        
        print(f"Generated {len(trades)} fallback synthetic trades")
        return trades
        
    except Exception as e:
        print(f"Error in generate_synthetic_trades: {e}")
        return []


def generate_synthetic_trades_with_real_prices(num_trades=1000):
    """Generate synthetic trades based on real OHLCV data"""
    try:
        trades = []
        
        # Try to fetch real OHLCV data
        ohlcv_data = fetch_real_ohlcv_data()
        
        if not ohlcv_data or len(ohlcv_data) == 0:
            print("No OHLCV data fetched, using fallback synthetic data")
            return generate_synthetic_trades(num_trades)
        
        # Define trading pairs and their weights
        symbols = list(ohlcv_data.keys())
        
        # For symbols without real data, use estimated prices
        fallback_prices = {
            'DOT/USDT': 7.5,
            'MATIC/USDT': 0.75,
            'LINK/USDT': 15,
            'AVAX/USDT': 40,
            'XRP/USDT': 0.52
        }
        
        trade_frequency = {
            'BTC/USDT': 0.25,
            'ETH/USDT': 0.20,
            'BNB/USDT': 0.10,
            'SOL/USDT': 0.10,
            'ADA/USDT': 0.08,
            'DOT/USDT': 0.07,
            'MATIC/USDT': 0.07,
            'LINK/USDT': 0.05,
            'AVAX/USDT': 0.05,
            'XRP/USDT': 0.03
        }
        
        # Generate cumulative frequencies
        cumulative_freq = []
        cumulative = 0
        symbol_list = []
        for symbol, freq in trade_frequency.items():
            cumulative += freq
            cumulative_freq.append(cumulative)
            symbol_list.append(symbol)
        
        # Get time range from OHLCV data
        first_candle_time = min(ohlcv_data[s][0][0] for s in symbols if s in ohlcv_data)
        last_candle_time = max(ohlcv_data[s][-1][0] for s in symbols if s in ohlcv_data)
        
        print(f"Generating trades from {datetime.fromtimestamp(first_candle_time/1000)} to {datetime.fromtimestamp(last_candle_time/1000)}")
        
        for i in range(num_trades):
            # Random timestamp within the OHLCV range
            trade_timestamp = random.randint(first_candle_time, last_candle_time)
            trade_time = datetime.fromtimestamp(trade_timestamp / 1000)
            
            # Weighted random symbol selection
            rand_val = random.random()
            symbol_index = 0
            for j, cum_freq in enumerate(cumulative_freq):
                if rand_val <= cum_freq:
                    symbol_index = j
                    break
            
            symbol = symbol_list[symbol_index]
            
            # Get price from OHLCV data
            if symbol in ohlcv_data:
                # Find the candle for this timestamp
                candles = ohlcv_data[symbol]
                candle_index = 0
                
                for j, candle in enumerate(candles):
                    if candle[0] >= trade_timestamp:
                        candle_index = max(0, j - 1)
                        break
                
                # Get OHLCV values
                candle = candles[candle_index]
                low_price = candle[3]
                high_price = candle[2]
                close_price = candle[4]
                
                # Generate realistic price
                price = random.triangular(low_price, high_price, close_price)
                
                # Determine trade side
                price_position = (price - low_price) / (high_price - low_price) if high_price > low_price else 0.5
                
                if price_position < 0.3:
                    side = 'buy' if random.random() < 0.75 else 'sell'
                elif price_position > 0.7:
                    side = 'sell' if random.random() < 0.75 else 'buy'
                else:
                    side = random.choice(['buy', 'sell'])
            else:
                # Fallback pricing
                price = fallback_prices.get(symbol, 10) * random.uniform(0.9, 1.1)
                side = random.choice(['buy', 'sell'])
            
            # Determine amount based on symbol
            if 'BTC' in symbol:
                amount = random.triangular(0.001, 0.5, 0.01)
            elif 'ETH' in symbol:
                amount = random.triangular(0.01, 5, 0.5)
            else:
                amount = random.triangular(1, 100, 10)
            
            cost = price * amount
            
            trade = {
                'id': f'trade_{i}_{int(trade_timestamp)}',
                'orderId': f'order_{i}_{int(trade_timestamp)}',
                'symbol': symbol,
                'side': side,
                'price': round(price, 6),
                'amount': round(amount, 8),
                'cost': round(cost, 2),
                'fee': {
                    'cost': cost * 0.001,
                    'currency': 'USDT',
                    'rate': 0.001
                },
                'timestamp': int(trade_timestamp),
                'datetime': trade_time.isoformat(),
                'type': 'limit',
                'takerOrMaker': 'taker',
                'info': {
                    'exchange': 'demo',
                    'pair': symbol.replace('/', '_')
                }
            }
            
            trades.append(trade)
        
        # Sort by timestamp (newest first)
        trades.sort(key=lambda x: x['timestamp'], reverse=True)
        
        print(f"Generated {len(trades)} synthetic trades")
        return trades
        
    except Exception as e:
        print(f"Error in generate_synthetic_trades_with_real_prices: {e}")
        return generate_synthetic_trades(num_trades)


def generate_synthetic_balance():
    """Generate synthetic balance data"""
    return {
        'BTC': {'free': 1.5, 'used': 0, 'total': 1.5},
        'ETH': {'free': 15.3, 'used': 0, 'total': 15.3},
        'BNB': {'free': 25.5, 'used': 0, 'total': 25.5},
        'SOL': {'free': 100.2, 'used': 0, 'total': 100.2},
        'ADA': {'free': 5000, 'used': 0, 'total': 5000},
        'DOT': {'free': 200, 'used': 0, 'total': 200},
        'MATIC': {'free': 2000, 'used': 0, 'total': 2000},
        'USDT': {'free': 10000, 'used': 0, 'total': 10000},
        'LINK': {'free': 50, 'used': 0, 'total': 50},
        'AVAX': {'free': 30, 'used': 0, 'total': 30},
        'free': {},
        'used': {},
        'total': {},
        'info': {}
    }


def load_simulated_trades_from_file():
    """Load simulated trades from JSON file if it exists"""
    try:
        if os.path.exists('simulated_trades.json'):
            with open('simulated_trades.json', 'r') as f:
                trades = json.load(f)
                print(f"Loaded {len(trades)} trades from simulated_trades.json")
                return trades
        else:
            print("simulated_trades.json not found")
            return None
    except Exception as e:
        print(f"Error loading simulated trades: {e}")
        return None


def calculate_balance_from_trades():
    """Calculate current balance based on simulated trades"""
    try:
        trades = load_simulated_trades_from_file()
        if not trades:
            return generate_synthetic_balance()
        
        # Calculate BTC balance from trades
        btc_balance = 0
        usdt_spent = 0
        
        for trade in trades:
            if trade['symbol'] == 'BTC/USDT':
                if trade['side'] == 'buy':
                    btc_balance += trade['amount']
                    usdt_spent += trade['cost']
                else:  # sell
                    btc_balance -= trade['amount']
                    usdt_spent -= trade['cost']
        
        # Starting USDT balance
        initial_usdt = 50000  # Start with $50k
        usdt_balance = initial_usdt - usdt_spent
        
        # Create balance structure
        balance = {
            'BTC': {'free': btc_balance, 'used': 0, 'total': btc_balance},
            'USDT': {'free': usdt_balance, 'used': 0, 'total': usdt_balance},
            'ETH': {'free': 5, 'used': 0, 'total': 5},  # Some other holdings
            'BNB': {'free': 10, 'used': 0, 'total': 10},
            'SOL': {'free': 50, 'used': 0, 'total': 50},
            'free': {},
            'used': {},
            'total': {},
            'info': {'source': 'simulated_trades'}
        }
        
        print(f"Calculated balance - BTC: {btc_balance:.4f}, USDT: {usdt_balance:.2f}")
        return balance
        
    except Exception as e:
        print(f"Error calculating balance from trades: {e}")
        return generate_synthetic_balance()


def load_all_simulated_trades():
    with open('simulated_trades.json', 'r') as f:
        data = json.load(f)
    all_trades = data.get('trades', [])
    # Only keep trades that have a 'timestamp' key
    all_trades = [t for t in all_trades if isinstance(t, dict) and 'timestamp' in t]
    return all_trades
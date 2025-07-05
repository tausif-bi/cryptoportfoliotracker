from flask import Flask, request, jsonify
# from flask_cors import CORS  # Disabled to avoid duplicate headers
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import random
import ccxt
import ta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
from strategies.technical.trendline_breakout import TrendlineBreakoutStrategy
from strategies.technical.continuation_patterns import ContinuationPatternsStrategy
from strategies.technical.rsi_strategy import RSIStrategy, run_rsi_analysis
from strategies.technical.ma_crossover_strategy import MovingAverageCrossoverStrategy, run_ma_crossover_analysis
from strategies.technical.bollinger_bands_strategy import BollingerBandsStrategy, run_bollinger_bands_analysis
from strategies.technical.volume_spike_strategy import VolumeSpikeStrategy, run_volume_spike_analysis
from strategies.technical.reversal_patterns_strategy import ReversalPatternsStrategy, run_reversal_patterns_analysis
from config import config
from utils.security import get_limiter, add_security_headers, require_valid_request, validate_request_size
from utils.validators import (
    validate_json_input, ExchangeCredentialsSchema, TradeQuerySchema, 
    StrategyAnalysisSchema, PortfolioQuerySchema, sanitize_string,
    UserRegistrationSchema, UserLoginSchema, PasswordChangeSchema
)
from utils.logger import setup_logging, get_logger, log_api_call, log_exchange_operation, RequestIDMiddleware
from utils.exceptions import (
    handle_exceptions, handle_exchange_errors, CryptoPortfolioException,
    ExchangeConnectionError, InvalidCredentialsError, DataValidationError
)
from models.database import db, init_db, User, Portfolio, Trade, Holding, PriceHistory
from utils.migration import run_migration
from utils.auth import (
    init_jwt, UserManager, PasswordManager, create_tokens, 
    auth_required, admin_required, get_current_user
)
from services.websocket_service import init_websocket
from services.chart_service import chart_service
from utils.encryption import init_encryption, encryption_service
from utils.error_handlers import init_error_handlers
from utils.chart_data_formatter import ChartDataFormatter

# Initialize Flask app with configuration
app = Flask(__name__)

# Load configuration based on environment
env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[env])

# CORS handling based on environment configuration
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    allowed_origins = app.config.get('CORS_ORIGINS', [])
    
    # In production, only allow specific origins
    if app.config.get('ENV') == 'production':
        if origin and (origin in allowed_origins or '*' in allowed_origins):
            response.headers['Access-Control-Allow-Origin'] = origin
        elif allowed_origins and allowed_origins[0] != '*':
            # Set to first allowed origin if current origin not allowed
            response.headers['Access-Control-Allow-Origin'] = allowed_origins[0]
    else:
        # Development mode - be more permissive
        response.headers['Access-Control-Allow-Origin'] = origin or '*'
    
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,Accept,Origin,X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    # Add security headers
    return add_security_headers(response)

# Handle preflight OPTIONS requests
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'status': 'OK'})
        origin = request.headers.get('Origin')
        allowed_origins = app.config.get('CORS_ORIGINS', [])
        
        if app.config.get('ENV') == 'production':
            if origin and (origin in allowed_origins or '*' in allowed_origins):
                response.headers['Access-Control-Allow-Origin'] = origin
            elif allowed_origins and allowed_origins[0] != '*':
                response.headers['Access-Control-Allow-Origin'] = allowed_origins[0]
        else:
            response.headers['Access-Control-Allow-Origin'] = origin or '*'
            
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,Accept,Origin,X-Requested-With'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response

# Initialize database
init_db(app)

# Initialize JWT authentication
jwt, blacklisted_tokens = init_jwt(app)

# Initialize encryption service
init_encryption(app)

# Initialize WebSocket service
socketio, price_service = init_websocket(app)

# Setup logging
setup_logging(app)

# Add request ID middleware
app.wsgi_app = RequestIDMiddleware(app.wsgi_app)

# Initialize rate limiter
limiter = get_limiter()
limiter.init_app(app)

# Get application logger
logger = get_logger(__name__)

# Initialize error handlers
init_error_handlers(app)

# Security headers are now added in the main after_request handler above

# Error handlers are now initialized in init_error_handlers() above

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

# Initialize analyzer
analyzer = PortfolioAnalyzer()

@app.route('/api/analyze-portfolio', methods=['POST'])
@auth_required()
def analyze_portfolio():
    """Analyze portfolio endpoint"""
    try:
        data = request.json
        holdings = data.get('holdings', [])
        prices = data.get('prices', {})
        
        if not holdings:
            return jsonify({'error': 'No holdings provided'}), 400
        
        analysis = analyzer.analyze_portfolio(holdings, prices)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f'Error in analyze_portfolio: {str(e)}', exc_info=True)
        if app.config.get('ENV') == 'production':
            return jsonify({'error': 'Failed to analyze portfolio. Please try again.'}), 500
        else:
            return jsonify({'error': str(e)}), 500

@app.route('/api/predict-price', methods=['POST'])
@auth_required()
def predict_price():
    """Predict price movement endpoint"""
    try:
        data = request.json
        symbol = data.get('symbol')
        exchange = data.get('exchange', 'binance')
        
        if not symbol:
            return jsonify({'error': 'No symbol provided'}), 400
        
        # Initialize exchange if needed
        if analyzer.exchange is None:
            analyzer.initialize_exchange(exchange)
        
        prediction = analyzer.predict_price_movement(symbol)
        
        if prediction is None:
            return jsonify({'error': 'Could not generate prediction'}), 500
        
        return jsonify({
            'success': True,
            'prediction': prediction,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/market-analysis', methods=['GET'])
@limiter.limit("30 per minute")
@require_valid_request
def market_analysis():
    """Get overall market analysis"""
    try:
        # Initialize exchange if needed
        if analyzer.exchange is None:
            analyzer.initialize_exchange('binance')
        
        # Analyze major cryptocurrencies
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT']
        market_data = []
        
        for symbol in symbols:
            try:
                ticker = analyzer.exchange.fetch_ticker(symbol)
                market_data.append({
                    'symbol': symbol,
                    'price': ticker['last'],
                    'change24h': ticker['percentage'],
                    'volume': ticker['baseVolume']
                })
            except:
                continue
        
        # Calculate market sentiment
        avg_change = sum(d['change24h'] for d in market_data) / len(market_data)
        
        sentiment = 'bullish' if avg_change > 2 else 'bearish' if avg_change < -2 else 'neutral'
        
        return jsonify({
            'success': True,
            'market_data': market_data,
            'sentiment': sentiment,
            'average_change': avg_change,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rebalancing-suggestions', methods=['POST'])
def rebalancing_suggestions():
    """Get portfolio rebalancing suggestions"""
    try:
        data = request.json
        holdings = data.get('holdings', [])
        target_allocations = data.get('target_allocations', {})
        
        if not holdings:
            return jsonify({'error': 'No holdings provided'}), 400
        
        suggestions = []
        total_value = sum(h['usdValue'] for h in holdings)
        
        # Default target allocations if not provided
        if not target_allocations:
            target_allocations = {
                'BTC': 40,
                'ETH': 30,
                'others': 30
            }
        
        # Calculate current allocations
        current_allocations = {}
        for holding in holdings:
            coin = holding['coin']
            allocation = holding['allocation']
            current_allocations[coin] = allocation
        
        # Generate rebalancing suggestions
        for coin, target in target_allocations.items():
            current = current_allocations.get(coin, 0)
            diff = target - current
            
            if abs(diff) > 5:  # Only suggest if difference > 5%
                action = 'BUY' if diff > 0 else 'SELL'
                amount_usd = abs(diff) * total_value / 100
                
                suggestions.append({
                    'coin': coin,
                    'action': action,
                    'current_allocation': current,
                    'target_allocation': target,
                    'difference': diff,
                    'amount_usd': amount_usd
                })
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'total_portfolio_value': total_value,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-exchange', methods=['POST'])
@limiter.limit("5 per minute")
@auth_required()
@require_valid_request
@validate_request_size(1)  # 1MB limit
@validate_json_input(ExchangeCredentialsSchema)
@handle_exceptions(logger)
def verify_exchange():
    """Verify exchange credentials"""
    data = request.validated_json
    exchange_name = data.get('exchangeName')
    api_key = data.get('apiKey')
    api_secret = data.get('apiSecret')
    password = data.get('password')
    
    logger.info(f"Verifying exchange credentials", extra={
        'exchange': exchange_name,
        'api_key_length': len(api_key) if api_key else 0
    })
    
    # Handle demo mode
    if exchange_name == 'demo':
        log_exchange_operation(exchange_name, 'verify_credentials', success=True)
        return jsonify({'success': True, 'message': 'Demo mode - credentials accepted'})
    
    # Handle lbank2 -> lbank mapping
    actual_exchange_name = exchange_name
    if exchange_name == 'lbank2':
        actual_exchange_name = 'lbank'
    
    @handle_exchange_errors(actual_exchange_name)
    def _verify_credentials():
        # Initialize exchange
        exchange_class = getattr(ccxt, actual_exchange_name)
        config = {
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        }
        
        # Special handling for lbank
        if actual_exchange_name == 'lbank':
            config['sandbox'] = False
            # LBank v2 requires specific configuration
            config['version'] = 'v2'
            
            # Check if this might be an RSA key
            is_rsa_key = api_secret and ('-----BEGIN' in api_secret or len(api_secret) > 200)
            
            if is_rsa_key:
                print("WARNING: Detected possible RSA private key format")
                print("LBank CCXT expects a regular API secret for HMAC authentication, not an RSA private key")
                print("Please use the API Secret (not RSA private key) from LBank API settings")
                raise Exception("Invalid API Secret format. LBank requires the API Secret for HMAC authentication, not an RSA private key. Please check your LBank API settings.")
            
            config['options'] = {
                'defaultType': 'spot',
                'createMarketBuyOrderRequiresPrice': True
            }
            
            # Debug: Log credential format
            print(f"LBank API Key length: {len(api_key) if api_key else 0}")
            print(f"LBank API Secret length: {len(api_secret) if api_secret else 0}")
            
            # Additional validation
            if api_secret and len(api_secret) < 10:
                print("WARNING: API Secret seems too short")
            elif api_secret and not api_secret.replace('-', '').replace('_', '').isalnum():
                print("WARNING: API Secret contains special characters - this might cause issues")
        
        if password and actual_exchange_name not in ['lbank']:
            config['password'] = password
            
        exchange = exchange_class(config)
        
        # Load markets first
        exchange.load_markets()
        logger.info(f"Successfully loaded markets for {exchange_name}")
        
        # Try to fetch balance to verify credentials
        try:
            balance = exchange.fetch_balance()
            logger.info(f"Successfully verified credentials for {exchange_name}")
        except Exception as e:
            # Log the full error for debugging
            error_msg = str(e)
            print(f"LBank verification error details: {error_msg}")
            if "0" in error_msg:
                print("Error code 0 typically means authentication failed")
                print("Please check:")
                print("1. API key and secret are correct")
                print("2. API key has read permissions enabled")
                print("3. Your IP is whitelisted if required")
            raise
        
        log_exchange_operation(exchange_name, 'verify_credentials', success=True)
        return jsonify({'success': True})
    
    # Execute the verification
    return _verify_credentials()

@app.route('/api/fetch-balance', methods=['POST'])
@limiter.limit("10 per minute")
@auth_required()
@require_valid_request
@validate_request_size(1)
@validate_json_input(ExchangeCredentialsSchema)
@handle_exceptions(logger)
def fetch_balance():
    """Fetch exchange balance"""
    data = request.validated_json
    exchange_name = data.get('exchangeName')
    api_key = data.get('apiKey')
    api_secret = data.get('apiSecret')
    password = data.get('password')
    
    logger.info(f"Fetching balance from {exchange_name}")
    
    # Handle lbank2 -> lbank mapping
    actual_exchange_name = exchange_name
    if exchange_name == 'lbank2':
        actual_exchange_name = 'lbank'
    
    @handle_exchange_errors(actual_exchange_name)
    def _fetch_balance():
        # Initialize exchange
        exchange_class = getattr(ccxt, actual_exchange_name)
        config = {
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        }
        
        if actual_exchange_name == 'lbank':
            config['sandbox'] = False
            config['version'] = 'v2'
            config['options'] = {
                'defaultType': 'spot',
                'createMarketBuyOrderRequiresPrice': True
            }
            
        if password and actual_exchange_name not in ['lbank']:
            config['password'] = password
            
        exchange = exchange_class(config)
        
        # Fetch balance
        balance = exchange.fetch_balance()
        
        # Format balance
        formatted_balance = {}
        for coin, amounts in balance.items():
            if isinstance(amounts, dict) and amounts.get('total', 0) > 0:
                formatted_balance[coin] = amounts
                
        return jsonify({
            'success': True,
            'balance': formatted_balance
        })
    
    # Execute the balance fetch
    return _fetch_balance()

@app.route('/api/fetch-trades', methods=['POST'])
@auth_required()
def fetch_trades():
    """Fetch trading history"""
    try:
        data = request.json
        exchange_name = data.get('exchangeName')
        api_key = data.get('apiKey')
        api_secret = data.get('apiSecret')
        password = data.get('password')
        symbol = data.get('symbol')
        since = data.get('since')
        limit = data.get('limit', 50)
        
        logger.debug(f"Fetching trades for {exchange_name}")
        
        # Handle demo mode
        if exchange_name == 'demo':
            logger.debug("Demo mode: Loading trades...")
            
            # First try to load all simulated trades (BTC from file + synthetic altcoins)
            trades = load_all_simulated_trades()
            
            # If no trades loaded, generate synthetic trades
            if not trades:
                print("Generating synthetic trades...")
                trades = generate_synthetic_trades_with_real_prices(1000)
            
            # Filter by symbol if specified
            if symbol:
                trades = [t for t in trades if t['symbol'] == symbol]
                print(f"After filtering by {symbol}: {len(trades)} trades")
            
            # Sort by timestamp (newest first)
            trades.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Apply limit
            trades = trades[:min(limit, len(trades))]
            
            print(f"Returning {len(trades)} trades for demo mode (limit was {limit})")
            
            return jsonify({
                'success': True,
                'trades': trades,
                'totalTrades': len(trades),
                'returnedTrades': len(trades),
                'source': 'simulated_trades.json' if os.path.exists('simulated_trades.json') else 'synthetic'
            })
        
        # Handle real exchanges
        # Handle lbank2 -> lbank mapping
        actual_exchange_name = exchange_name
        if exchange_name == 'lbank2':
            actual_exchange_name = 'lbank'
            
        # Initialize exchange
        exchange_class = getattr(ccxt, actual_exchange_name)
        config = {
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        }
        
        if actual_exchange_name == 'lbank':
            config['sandbox'] = False
            config['version'] = 'v2'
            config['options'] = {
                'defaultType': 'spot',
                'createMarketBuyOrderRequiresPrice': True
            }
            
        if password and actual_exchange_name not in ['lbank']:
            config['password'] = password
            
        exchange = exchange_class(config)
        
        # Load markets first
        exchange.load_markets()
        
        # Fetch trades
        formatted_trades = []
        
        try:
            if symbol:
                trades = exchange.fetch_my_trades(symbol, since, limit)
            else:
                # For LBank, we might need to fetch trades per symbol
                # Get user's balance first to know which symbols to check
                balance = exchange.fetch_balance()
                symbols_to_check = []
                
                for coin in balance:
                    if isinstance(balance[coin], dict) and balance[coin].get('total', 0) > 0:
                        if coin not in ['USDT', 'USD', 'info', 'free', 'used', 'total']:
                            # Try common pairs
                            symbols_to_check.append(f"{coin}/USDT")
                
                # Fetch trades for each symbol
                all_trades = []
                for sym in symbols_to_check[:5]:  # Limit to 5 symbols to avoid rate limits
                    try:
                        symbol_trades = exchange.fetch_my_trades(sym, since, 10)
                        all_trades.extend(symbol_trades)
                    except Exception as e:
                        print(f"Could not fetch trades for {sym}: {e}")
                        continue
                
                trades = all_trades
                
            # Format trades
            for trade in trades:
                formatted_trades.append({
                    'id': trade.get('id', ''),
                    'symbol': trade.get('symbol', ''),
                    'side': trade.get('side', ''),
                    'price': trade.get('price', 0),
                    'amount': trade.get('amount', 0),
                    'cost': trade.get('cost', 0),
                    'fee': trade.get('fee', {}),
                    'timestamp': trade.get('timestamp', 0),
                    'datetime': trade.get('datetime', ''),
                })
                
        except Exception as e:
            error_msg = f"Error fetching trades: {str(e)}"
            print(f"\n{'='*60}")
            print(error_msg)
            print(f"Exchange name: {actual_exchange_name}")
            print(f"Symbol: {symbol}")
            # Return empty array instead of error if trades not supported
            if "not supported" in str(e).lower():
                print("Exchange doesn't support trade history")
            else:
                import traceback
                traceback.print_exc()
            print(f"{'='*60}\n")
                
        return jsonify({
            'success': True,
            'trades': formatted_trades
        })
        
    except Exception as e:
        print(f"Error in fetch_trades: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty trades array instead of error
        return jsonify({
            'success': True,
            'trades': []
        })

@app.route('/api/portfolio-stats', methods=['POST'])
@auth_required()
def portfolio_stats():
    """Calculate portfolio statistics"""
    try:
        data = request.json
        exchange_name = data.get('exchangeName')
        api_key = data.get('apiKey')
        api_secret = data.get('apiSecret')
        password = data.get('password')
        
        print(f"Fetching portfolio stats for {exchange_name}")
        
        # Handle demo mode
        if exchange_name == 'demo':
            # Use balance calculated from simulated trades
            balance = calculate_balance_from_trades()
            
            # Try to fetch real current prices
            try:
                exchange = ccxt.binance({'enableRateLimit': True})
                tickers = exchange.fetch_tickers(['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT'])
                
                # Add some additional estimated tickers for other coins
                all_tickers = {}
                for symbol, ticker in tickers.items():
                    all_tickers[symbol] = {
                        'last': ticker['last'],
                        'percentage': ticker['percentage'] or random.uniform(-5, 5)
                    }
                
                # Add estimated prices for coins without direct data
                if 'BTC/USDT' in tickers:
                    btc_change = tickers['BTC/USDT']['percentage'] or 0
                    # Correlate other altcoins with BTC
                    all_tickers['DOT/USDT'] = {'last': 7.5 * (1 + btc_change/100 * 0.8), 'percentage': btc_change * 0.8}
                    all_tickers['MATIC/USDT'] = {'last': 0.75 * (1 + btc_change/100 * 1.2), 'percentage': btc_change * 1.2}
                    all_tickers['LINK/USDT'] = {'last': 15 * (1 + btc_change/100 * 0.9), 'percentage': btc_change * 0.9}
                    all_tickers['AVAX/USDT'] = {'last': 40 * (1 + btc_change/100 * 1.1), 'percentage': btc_change * 1.1}
                    all_tickers['XRP/USDT'] = {'last': 0.52 * (1 + btc_change/100 * 0.7), 'percentage': btc_change * 0.7}
                
                print("Using real market prices for demo portfolio")
            except Exception as e:
                print(f"Could not fetch real prices, using defaults: {e}")
                # Fallback prices
                all_tickers = {
                    'BTC/USDT': {'last': 68000, 'percentage': 2.5},
                    'ETH/USDT': {'last': 3800, 'percentage': -1.2},
                    'BNB/USDT': {'last': 450, 'percentage': 0.8},
                    'SOL/USDT': {'last': 145, 'percentage': 5.4},
                    'ADA/USDT': {'last': 0.45, 'percentage': -3.2},
                    'DOT/USDT': {'last': 7.5, 'percentage': 1.5},
                    'MATIC/USDT': {'last': 0.75, 'percentage': -0.5},
                    'LINK/USDT': {'last': 15, 'percentage': 3.2},
                    'AVAX/USDT': {'last': 40, 'percentage': 4.1},
                }
            
            holdings = []
            total_value = 0
            
            for coin, amounts in balance.items():
                if isinstance(amounts, dict) and amounts.get('total', 0) > 0.0001:
                    amount = amounts['total']
                    
                    if coin in ['USDT', 'USD']:
                        usd_value = amount
                        price = 1
                        change_24h = 0
                    else:
                        symbol = f"{coin}/USDT"
                        if symbol in all_tickers:
                            ticker = all_tickers[symbol]
                            price = ticker['last']
                            change_24h = ticker['percentage']
                            usd_value = amount * price
                        else:
                            continue
                    
                    holdings.append({
                        'coin': coin,
                        'amount': amount,
                        'usdValue': usd_value,
                        'price': price,
                        'change24h': change_24h,
                    })
                    
                    total_value += usd_value
            
            # Calculate allocations
            for holding in holdings:
                holding['allocation'] = (holding['usdValue'] / total_value) * 100 if total_value > 0 else 0
            
            # Sort by value
            holdings.sort(key=lambda x: x['usdValue'], reverse=True)
            
            result = {
                'totalValue': total_value,
                'holdings': holdings,
                'numberOfAssets': len(holdings),
            }
            
            return jsonify({
                'success': True,
                'stats': result
            })
        
        # Handle real exchanges
        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_name)
        config = {
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        }
        
        # Special handling for lbank (lbank2 in frontend)
        if exchange_name in ['lbank', 'lbank2']:
            # CCXT uses 'lbank' as the exchange ID
            if exchange_name == 'lbank2':
                exchange_name = 'lbank'
                exchange_class = getattr(ccxt, 'lbank')
            config['sandbox'] = False
            config['version'] = 'v2'
            config['options'] = {
                'defaultType': 'spot',
                'createMarketBuyOrderRequiresPrice': True
            }
            print(f"LBank configuration: apiKey={api_key[:8] if api_key else 'None'}..., version=v2")
        
        if password and exchange_name not in ['lbank']:
            config['password'] = password
            
        exchange = exchange_class(config)
        
        # Load markets
        print(f"Loading markets for {exchange_name}...")
        exchange.load_markets()
        print(f"Markets loaded successfully for {exchange_name}")
        
        # Fetch balance
        print(f"Fetching balance for {exchange_name}...")
        balance = exchange.fetch_balance()
        print(f"Raw balance keys: {list(balance.keys())[:20]}")  # Show first 20 keys
        
        # Debug: Show non-zero balances
        non_zero_count = 0
        for coin, amounts in balance.items():
            if isinstance(amounts, dict) and amounts.get('total', 0) > 0:
                print(f"Found {coin}: {amounts['total']}")
                non_zero_count += 1
        print(f"Total non-zero balances: {non_zero_count}")
        
        # Get all tickers for price lookups (more efficient than individual calls)
        all_tickers = {}
        try:
            all_tickers = exchange.fetch_tickers()
            print(f"Fetched {len(all_tickers)} tickers")
        except Exception as e:
            print(f"Could not fetch all tickers: {e}")
        
        # Get current prices
        holdings = []
        total_value = 0
        
        for coin, amounts in balance.items():
            if isinstance(amounts, dict) and amounts.get('total', 0) > 0.0001:
                amount = amounts['total']
                
                # Get USD value
                try:
                    if coin in ['USDT', 'USD', 'BUSD', 'USDC']:
                        usd_value = amount
                        price = 1
                        change_24h = 0
                    else:
                        # Try different symbol formats for LBank
                        symbol = None
                        price = None
                        
                        # Check pre-fetched tickers
                        possible_symbols = [
                            f"{coin}/USDT",
                            f"{coin}_USDT",
                            f"{coin.lower()}_usdt",
                            f"{coin.upper()}_USDT"
                        ]
                        
                        for sym in possible_symbols:
                            if sym in all_tickers:
                                symbol = sym
                                ticker = all_tickers[sym]
                                price = ticker.get('last', 0)
                                change_24h = ticker.get('percentage', 0) or 0
                                break
                        
                        # If not found in tickers, try fetching individually
                        if price is None:
                            try:
                                symbol = f"{coin}/USDT"
                                ticker = exchange.fetch_ticker(symbol)
                                price = ticker['last']
                                change_24h = ticker.get('percentage', 0) or 0
                            except:
                                print(f"Could not get price for {coin}")
                                continue
                        
                        usd_value = amount * price if price else 0
                        
                    holdings.append({
                        'coin': coin,
                        'amount': amount,
                        'usdValue': usd_value,
                        'price': price,
                        'change24h': change_24h,
                    })
                    
                    total_value += usd_value
                    print(f"Added {coin}: {amount} @ ${price} = ${usd_value}")
                except Exception as e:
                    print(f"Error processing {coin}: {str(e)}")
                    continue
                    
        # Calculate allocations
        for holding in holdings:
            holding['allocation'] = (holding['usdValue'] / total_value) * 100 if total_value > 0 else 0
            
        # Sort by value
        holdings.sort(key=lambda x: x['usdValue'], reverse=True)
        
        result = {
            'totalValue': total_value,
            'holdings': holdings,
            'numberOfAssets': len(holdings),
        }
        
        print(f"Final portfolio stats: {len(holdings)} assets, total value: ${total_value}")
        
        return jsonify({
            'success': True,
            'stats': result
        })
        
    except Exception as e:
        error_msg = f"Error in portfolio_stats: {str(e)}"
        print(f"\n{'='*60}")
        print(error_msg)
        print(f"Exchange name received: {exchange_name}")
        print(f"API Key (first 8 chars): {api_key[:8] if api_key else 'None'}...")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        logger.error(error_msg, exc_info=True)
        return jsonify({
            'success': False, 
            'error': str(e),
            'exchange': exchange_name
        }), 500


@app.route('/api/test-lbank', methods=['POST'])
@auth_required()
def test_lbank():
    """Test LBank connection with detailed debugging"""
    try:
        data = request.json
        api_key = data.get('apiKey', '').strip()
        api_secret = data.get('apiSecret', '').strip()
        
        print(f"\n=== Testing LBank Connection ===")
        print(f"API Key length: {len(api_key)}")
        print(f"API Secret length: {len(api_secret)}")
        print(f"API Key (first 8 chars): {api_key[:8] if api_key else 'None'}...")
        print(f"API Secret (first 8 chars): {api_secret[:8] if api_secret else 'None'}...")
        
        # Check if credentials contain any special characters that might cause issues
        import re
        if api_secret and not re.match(r'^[a-zA-Z0-9+/=]+$', api_secret):
            print("WARNING: API Secret contains special characters that might cause issues")
        
        # Try different configurations for LBank
        configs_to_try = [
            {
                'name': 'Standard v2 config',
                'config': {
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'sandbox': False,
                    'version': 'v2',
                    'options': {
                        'defaultType': 'spot',
                    }
                }
            },
            {
                'name': 'Config without version',
                'config': {
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'sandbox': False,
                    'options': {
                        'defaultType': 'spot',
                    }
                }
            },
            {
                'name': 'Minimal config',
                'config': {
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                }
            }
        ]
        
        exchange = None
        successful_config = None
        
        for cfg in configs_to_try:
            try:
                print(f"\nTrying {cfg['name']}...")
                exchange = ccxt.lbank(cfg['config'])
                # Try to load markets as a test
                exchange.load_markets()
                print(f"✅ {cfg['name']} - Markets loaded successfully")
                successful_config = cfg['name']
                break
            except Exception as e:
                print(f"❌ {cfg['name']} failed: {str(e)}")
                continue
        
        if not exchange:
            raise Exception("All LBank configurations failed")
        
        print(f"\nUsing configuration: {successful_config}")
        
        # Check CCXT version
        print(f"CCXT Version: {ccxt.__version__}")
        print(f"LBank exchange ID: {exchange.id}")
        
        # Load markets
        print("Loading markets...")
        markets = exchange.load_markets()
        print(f"Loaded {len(markets)} markets")
        
        # Try to fetch balance
        print("Fetching balance...")
        balance = exchange.fetch_balance()
        
        # Process balance
        non_zero_balances = {}
        for coin, amounts in balance.items():
            if isinstance(amounts, dict) and 'total' in amounts:
                if amounts['total'] > 0:
                    non_zero_balances[coin] = {
                        'free': amounts.get('free', 0),
                        'used': amounts.get('used', 0),
                        'total': amounts.get('total', 0)
                    }
                    print(f"Found {coin}: {amounts['total']}")
        
        return jsonify({
            'success': True,
            'balance': non_zero_balances,
            'message': f'Found {len(non_zero_balances)} assets'
        })
        
    except Exception as e:
        print(f"Error in test_lbank: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


# Add these functions to your app.py file

# Add all these functions and endpoints to your existing app.py file

def calculate_pnl_from_trades():
    """Calculate P&L from simulated trades using FIFO matching"""
    try:
        # Debug information
        print("=== STARTING P&L CALCULATION ===")
        current_dir = os.getcwd()
        print(f"Current working directory: {current_dir}")
        print(f"Files in directory: {os.listdir('.')}")
        print(f"simulated_trades.json exists: {os.path.exists('simulated_trades.json')}")
        
        # Check if file exists
        if not os.path.exists('simulated_trades.json'):
            print("❌ simulated_trades.json not found - returning empty data")
            return {
                'success': True,
                'summary': {
                    'total_pnl': 0,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'average_win': 0,
                    'average_loss': 0,
                    'best_trade': None,
                    'worst_trade': None,
                },
                'trades': []
            }
        
        # Get file size for debugging
        file_size = os.path.getsize('simulated_trades.json')
        print(f"File size: {file_size} bytes")
        
        # Load the JSON file
        print("✅ File found, loading JSON data...")
        with open('simulated_trades.json', 'r') as f:
            data = json.load(f)
        
        print(f"Raw data type: {type(data)}")
        print(f"Raw data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        
        # Handle the structure from your file
        trades = data.get('trades', []) if isinstance(data, dict) else data
        
        print(f"📊 Loaded {len(trades)} trades from file")
        
        if not trades:
            print("❌ No trades found in the data")
            return {
                'success': True,
                'summary': {
                    'total_pnl': 0,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'average_win': 0,
                    'average_loss': 0,
                    'best_trade': None,
                    'worst_trade': None,
                },
                'trades': []
            }
        
        # Show sample trade for debugging
        print(f"First trade sample: {trades[0]}")
        
        # Group trades by symbol
        trades_by_symbol = {}
        
        for i, trade in enumerate(trades):
            # Debug first few trades
            if i < 3:
                print(f"Processing trade {i}: {trade}")
            
            # Extract symbol - your data structure uses 'symbol' directly
            symbol = trade.get('symbol', 'BTC/USDT')  # Default to BTC/USDT if missing
            
            if symbol not in trades_by_symbol:
                trades_by_symbol[symbol] = {'buys': [], 'sells': []}
            
            # In your JSON structure, 'side' field indicates the action
            # 'buy' means buying the crypto, 'sell' means selling the crypto
            side = trade.get('side', '').lower()
            
            if 'buy' in side:
                trades_by_symbol[symbol]['buys'].append(trade)
            elif 'sell' in side:
                trades_by_symbol[symbol]['sells'].append(trade)
            else:
                print(f"Unknown side for trade {i}: {side}")
        
        print(f"📈 Grouped trades into {len(trades_by_symbol)} symbols:")
        for symbol, symbol_trades in trades_by_symbol.items():
            print(f"  {symbol}: {len(symbol_trades['buys'])} buys, {len(symbol_trades['sells'])} sells")
        
        # Match trades using FIFO
        completed_trades = []
        
        for symbol, trades_dict in trades_by_symbol.items():
            buys = sorted(trades_dict['buys'], key=lambda x: x.get('timestamp', 0))
            sells = sorted(trades_dict['sells'], key=lambda x: x.get('timestamp', 0))
            
            print(f"\n🔄 Processing {symbol}: {len(buys)} buys, {len(sells)} sells")
            
            # Match buys with sells using FIFO
            buy_idx = 0
            sell_idx = 0
            
            # Create copies to avoid modifying original data
            remaining_buys = [dict(b) for b in buys]
            remaining_sells = [dict(s) for s in sells]
            
            while buy_idx < len(remaining_buys) and sell_idx < len(remaining_sells):
                buy = remaining_buys[buy_idx]
                sell = remaining_sells[sell_idx]
                
                # Get quantities
                buy_qty = buy.get('quantity', 0)
                sell_qty = sell.get('quantity', 0)
                
                if buy_qty <= 0:
                    buy_idx += 1
                    continue
                    
                if sell_qty <= 0:
                    sell_idx += 1
                    continue
                
                # Match quantity (take the smaller amount)
                matched_qty = min(buy_qty, sell_qty)
                
                # Get prices
                buy_price = buy.get('price', 0)
                sell_price = sell.get('price', 0)
                
                if buy_price > 0 and sell_price > 0 and matched_qty > 0:
                    # Calculate P&L
                    pnl = (sell_price - buy_price) * matched_qty
                    pnl_percentage = ((sell_price - buy_price) / buy_price) * 100
                    
                    # Calculate holding period
                    buy_time = buy.get('timestamp', 0)
                    sell_time = sell.get('timestamp', 0)
                    holding_hours = (sell_time - buy_time) / (1000 * 60 * 60) if sell_time > buy_time else 0
                    
                    completed_trade = {
                        'id': f"{buy.get('trade_id', f'buy_{buy_idx}')}_{sell.get('trade_id', f'sell_{sell_idx}')}",
                        'symbol': symbol,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'quantity': matched_qty,
                        'buy_timestamp': buy_time,
                        'sell_timestamp': sell_time,
                        'pnl': round(pnl, 2),
                        'pnl_percentage': round(pnl_percentage, 2),
                        'buy_value': round(buy_price * matched_qty, 2),
                        'sell_value': round(sell_price * matched_qty, 2),
                        'holding_period_hours': round(holding_hours, 1)
                    }
                    
                    completed_trades.append(completed_trade)
                    print(f"  ✅ Matched trade: {matched_qty:.4f} {symbol} | Buy: ${buy_price} | Sell: ${sell_price} | P&L: ${pnl:.2f}")
                
                # Update remaining quantities
                remaining_buys[buy_idx]['quantity'] = buy_qty - matched_qty
                remaining_sells[sell_idx]['quantity'] = sell_qty - matched_qty
                
                # Move to next trade if quantity is exhausted
                if remaining_buys[buy_idx]['quantity'] <= 0:
                    buy_idx += 1
                if remaining_sells[sell_idx]['quantity'] <= 0:
                    sell_idx += 1
        
        # Sort completed trades by sell timestamp (newest first)
        completed_trades.sort(key=lambda x: x.get('sell_timestamp', 0), reverse=True)
        
        # Calculate summary statistics
        total_pnl = sum(t['pnl'] for t in completed_trades)
        winning_trades = [t for t in completed_trades if t['pnl'] > 0]
        losing_trades = [t for t in completed_trades if t['pnl'] < 0]
        
        summary = {
            'total_pnl': round(total_pnl, 2),
            'total_trades': len(completed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(len(winning_trades) / len(completed_trades) * 100, 1) if completed_trades else 0,
            'average_win': round(sum(t['pnl'] for t in winning_trades) / len(winning_trades), 2) if winning_trades else 0,
            'average_loss': round(sum(t['pnl'] for t in losing_trades) / len(losing_trades), 2) if losing_trades else 0,
            'best_trade': max(completed_trades, key=lambda x: x['pnl']) if completed_trades else None,
            'worst_trade': min(completed_trades, key=lambda x: x['pnl']) if completed_trades else None,
        }
        
        print(f"\n📊 P&L CALCULATION COMPLETE:")
        print(f"  Total P&L: ${total_pnl:.2f}")
        print(f"  Completed Trades: {len(completed_trades)}")
        print(f"  Winning Trades: {len(winning_trades)} ({summary['win_rate']}%)")
        print(f"  Losing Trades: {len(losing_trades)}")
        
        return {
            'success': True,
            'summary': summary,
            'trades': completed_trades,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error in calculate_pnl_from_trades: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': True,
            'summary': {
                'total_pnl': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'average_win': 0,
                'average_loss': 0,
                'best_trade': None,
                'worst_trade': None,
            },
            'trades': []
        }

@app.route('/api/pnl/summary', methods=['GET'])
def get_pnl_summary():
    """Get P&L summary with all completed trades"""
    try:
        result = calculate_pnl_from_trades()
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_pnl_summary: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'summary': {
                'total_pnl': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'average_win': 0,
                'average_loss': 0,
                'best_trade': None,
                'worst_trade': None,
            },
            'trades': []
        })

@app.route('/api/pnl/daily', methods=['GET'])
def get_daily_pnl():
    """Get P&L grouped by day"""
    try:
        result = calculate_pnl_from_trades()
        
        if not result.get('success'):
            return jsonify({
                'success': True,
                'daily_pnl': [],
                'total_days': 0
            })
        
        trades = result.get('trades', [])
        
        # Group by day
        daily_pnl = {}
        for trade in trades:
            sell_timestamp = trade.get('sell_timestamp', 0)
            if sell_timestamp:
                date = datetime.fromtimestamp(sell_timestamp / 1000).date()
                date_str = str(date)
                
                if date_str not in daily_pnl:
                    daily_pnl[date_str] = {
                        'date': date_str,
                        'pnl': 0,
                        'trades': 0,
                        'winning_trades': 0,
                        'losing_trades': 0
                    }
                
                daily_pnl[date_str]['pnl'] += trade['pnl']
                daily_pnl[date_str]['trades'] += 1
                
                if trade['pnl'] > 0:
                    daily_pnl[date_str]['winning_trades'] += 1
                else:
                    daily_pnl[date_str]['losing_trades'] += 1
        
        # Convert to list and sort by date
        daily_list = list(daily_pnl.values())
        daily_list.sort(key=lambda x: x['date'], reverse=True)
        
        # Round values
        for day in daily_list:
            day['pnl'] = round(day['pnl'], 2)
        
        return jsonify({
            'success': True,
            'daily_pnl': daily_list,
            'total_days': len(daily_list)
        })
        
    except Exception as e:
        print(f"Error in get_daily_pnl: {str(e)}")
        return jsonify({
            'success': True,
            'daily_pnl': [],
            'total_days': 0
        })
    

@app.route('/api/strategies/list', methods=['GET'])
def get_available_strategies():
    """Get list of all available strategies - no auth required"""
    try:
        strategies = [
            {
                'id': 'trendline_breakout',
                'name': 'Trendline Breakout Strategy',
                'description': 'Combines trendline breakouts with rolling window analysis for local tops/bottoms',
                'category': 'technical',
                'parameters': {
                    'trendline_lookback': {'default': 30, 'min': 5, 'max': 100, 'type': 'int'},
                    'rolling_window_order': {'default': 4, 'min': 2, 'max': 10, 'type': 'int'}
                }
            },
            {
                'id': 'rsi_strategy',
                'name': 'RSI Strategy',
                'description': 'RSI-based strategy using overbought/oversold levels for entry/exit signals',
                'category': 'technical',
                'parameters': {
                    'rsi_period': {'default': 14, 'min': 5, 'max': 50, 'type': 'int'},
                    'overbought_level': {'default': 70, 'min': 60, 'max': 90, 'type': 'int'},
                    'oversold_level': {'default': 30, 'min': 10, 'max': 40, 'type': 'int'}
                }
            },
            {
                'id': 'ma_crossover',
                'name': 'Moving Average Crossover',
                'description': 'Moving Average crossover strategy using fast and slow MAs for trend following',
                'category': 'technical',
                'parameters': {
                    'fast_period': {'default': 10, 'min': 5, 'max': 30, 'type': 'int'},
                    'slow_period': {'default': 30, 'min': 20, 'max': 100, 'type': 'int'},
                    'ma_type': {'default': 'sma', 'options': ['sma', 'ema'], 'type': 'string'}
                }
            },
            {
                'id': 'bollinger_bands',
                'name': 'Bollinger Bands Strategy',
                'description': 'Bollinger Bands strategy using volatility bands for mean reversion trading',
                'category': 'technical',
                'parameters': {
                    'period': {'default': 20, 'min': 10, 'max': 50, 'type': 'int'},
                    'std_dev': {'default': 2.0, 'min': 1.5, 'max': 3.0, 'type': 'float'}
                }
            },
            {
                'id': 'volume_spike',
                'name': 'Volume Spike Strategy',
                'description': 'Volume spike strategy using unusual volume patterns with price confirmation',
                'category': 'technical',
                'parameters': {
                    'volume_period': {'default': 20, 'min': 10, 'max': 50, 'type': 'int'},
                    'spike_multiplier': {'default': 2.0, 'min': 1.5, 'max': 5.0, 'type': 'float'},
                    'price_change_threshold': {'default': 0.01, 'min': 0.005, 'max': 0.03, 'type': 'float'}
                }
            },
            {
                'id': 'reversal_patterns',
                'name': 'Major Reversal Patterns Strategy',
                'description': 'Identifies Head & Shoulders, Double Tops/Bottoms, and other major reversal patterns with volume confirmation',
                'category': 'technical',
                'parameters': {
                    'lookback_period': {'default': 40, 'min': 30, 'max': 100, 'type': 'int'},
                    'min_pattern_bars': {'default': 8, 'min': 5, 'max': 20, 'type': 'int'},
                    'volume_threshold': {'default': 1.15, 'min': 1.1, 'max': 2.0, 'type': 'float'}
                }
            },
            {
                'id': 'continuation_patterns',
                'name': 'Continuation Patterns Strategy',
                'description': 'Identifies and trades continuation patterns including triangles (ascending, descending, symmetrical), flags, pennants, and rectangles that signal trend continuation',
                'category': 'technical',
                'parameters': {
                    'min_pattern_bars': {'default': 10, 'min': 5, 'max': 30, 'type': 'int'},
                    'trend_strength': {'default': 1.5, 'min': 1.0, 'max': 3.0, 'type': 'float'},
                    'volume_multiplier': {'default': 1.3, 'min': 1.1, 'max': 2.0, 'type': 'float'}
                }
            }
        ]
        
        return jsonify({
            'success': True,
            'strategies': strategies
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategies/trendline_breakout/analyze', methods=['POST'])
@auth_required()
def analyze_trendline_breakout():
    """Run trendline breakout strategy analysis"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 500)
        trendline_lookback = data.get('trendline_lookback', 30)
        rolling_window_order = data.get('rolling_window_order', 4)
        
        print(f"Running trendline breakout analysis for {symbol}")
        
        # Create strategy instance
        strategy = TrendlineBreakoutStrategy(
            trendline_lookback=trendline_lookback,
            rolling_window_order=rolling_window_order
        )
        
        # Generate signals
        analysis_data = strategy.generate_signals(symbol, timeframe, limit)
        
        if analysis_data is None:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch data or generate signals'
            }), 500
        
        # Create chart
        chart_base64 = strategy.create_chart(analysis_data)
        
        # Get current signal and metrics
        current_signal = "HOLD"
        if analysis_data['buy_signal'].iloc[-1] == 1:
            current_signal = "BUY"
        elif analysis_data['sell_signal'].iloc[-1] == 1:
            current_signal = "SELL"
        elif analysis_data['position'].iloc[-1] == 1:
            current_signal = "HOLD LONG"
        else:
            current_signal = "HOLD CASH"
        
        # Calculate some basic metrics
        total_buy_signals = (analysis_data['buy_signal'] == 1).sum()
        total_sell_signals = (analysis_data['sell_signal'] == 1).sum()
        current_price = analysis_data['close'].iloc[-1]
        
        # Get recent signals (last 10)
        recent_signals = []
        buy_indices = analysis_data[analysis_data['buy_signal'] == 1].index[-5:]
        sell_indices = analysis_data[analysis_data['sell_signal'] == 1].index[-5:]
        
        for idx in buy_indices:
            recent_signals.append({
                'timestamp': idx.isoformat(),
                'type': 'BUY',
                'price': analysis_data.loc[idx, 'close']
            })
        
        for idx in sell_indices:
            recent_signals.append({
                'timestamp': idx.isoformat(),
                'type': 'SELL',
                'price': analysis_data.loc[idx, 'close']
            })
        
        # Sort by timestamp
        recent_signals.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_signals = recent_signals[:10]  # Keep only 10 most recent
        
        return jsonify({
            'success': True,
            'analysis': {
                'symbol': symbol,
                'timeframe': timeframe,
                'current_signal': current_signal,
                'current_price': current_price,
                'total_buy_signals': int(total_buy_signals),
                'total_sell_signals': int(total_sell_signals),
                'recent_signals': recent_signals,
                'chart_base64': chart_base64,
                'strategy_info': strategy.get_strategy_info(),
                'parameters_used': {
                    'trendline_lookback': trendline_lookback,
                    'rolling_window_order': rolling_window_order
                }
            },
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        print(f"Error in trendline breakout analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategies/trendline_breakout/signals', methods=['POST'])
@auth_required()
def get_trendline_signals_only():
    """Get only the buy/sell signals without chart"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 100)  # Smaller limit for just signals
        
        # Create strategy instance with default parameters
        strategy = TrendlineBreakoutStrategy()
        
        # Generate signals
        analysis_data = strategy.generate_signals(symbol, timeframe, limit)
        
        if analysis_data is None:
            return jsonify({
                'success': False,
                'error': 'Failed to generate signals'
            }), 500
        
        # Extract buy/sell points for overlay on existing charts
        buy_signals = []
        sell_signals = []
        
        buy_points = analysis_data[analysis_data['buy_signal'] == 1]
        for idx, row in buy_points.iterrows():
            buy_signals.append({
                'timestamp': idx.isoformat(),
                'price': row['close'],
                'type': 'AI_BUY'
            })
        
        sell_points = analysis_data[analysis_data['sell_signal'] == 1]
        for idx, row in sell_points.iterrows():
            sell_signals.append({
                'timestamp': idx.isoformat(),
                'price': row['close'],
                'type': 'AI_SELL'
            })
        
        # Current signal
        current_signal = "HOLD"
        if analysis_data['buy_signal'].iloc[-1] == 1:
            current_signal = "BUY"
        elif analysis_data['sell_signal'].iloc[-1] == 1:
            current_signal = "SELL"
        elif analysis_data['position'].iloc[-1] == 1:
            current_signal = "HOLD LONG"
        
        return jsonify({
            'success': True,
            'signals': {
                'symbol': symbol,
                'current_signal': current_signal,
                'current_price': analysis_data['close'].iloc[-1],
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'ai_predictions': {
                    'next_action': current_signal,
                    'confidence': 'Medium',  # You can calculate this based on signal strength
                    'timeframe': timeframe
                }
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategies/continuation_patterns/analyze', methods=['POST'])
@auth_required()
def analyze_continuation_patterns():
    """Run continuation patterns strategy analysis"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 500)
        min_pattern_bars = data.get('min_pattern_bars', 10)
        trend_strength = data.get('trend_strength', 1.5)
        volume_multiplier = data.get('volume_multiplier', 1.3)
        
        print(f"Running continuation patterns analysis for {symbol}")
        
        # Create strategy instance
        strategy = ContinuationPatternsStrategy(
            min_pattern_bars=min_pattern_bars,
            trend_strength=trend_strength,
            volume_multiplier=volume_multiplier
        )
        
        # Generate signals
        analysis_data = strategy.generate_signals(symbol, timeframe, limit)
        
        if analysis_data is None:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch data or generate signals'
            }), 500
        
        # Create chart
        chart_base64 = strategy.create_chart(analysis_data)
        
        # Get current signal and pattern
        current_signal = "HOLD"
        current_pattern = "None"
        
        if analysis_data['signal'].iloc[-1] == 1:
            current_signal = "BUY"
        elif analysis_data['signal'].iloc[-1] == -1:
            current_signal = "SELL"
        elif analysis_data['position'].iloc[-1] == 1:
            current_signal = "HOLD LONG"
        elif analysis_data['position'].iloc[-1] == -1:
            current_signal = "HOLD SHORT"
        
        if analysis_data['pattern_detected'].iloc[-1] != '':
            current_pattern = analysis_data['pattern_detected'].iloc[-1]
        
        # Calculate metrics
        total_buy_signals = (analysis_data['signal'] == 1).sum()
        total_sell_signals = (analysis_data['signal'] == -1).sum()
        current_price = analysis_data['close'].iloc[-1]
        
        # Get recent patterns
        recent_patterns = []
        pattern_df = analysis_data[analysis_data['pattern_detected'] != '']
        
        for idx in pattern_df.index[-10:]:
            recent_patterns.append({
                'timestamp': idx.isoformat(),
                'pattern': pattern_df.loc[idx, 'pattern_detected'],
                'signal': 'BUY' if pattern_df.loc[idx, 'signal'] == 1 else 'SELL',
                'price': pattern_df.loc[idx, 'close'],
                'stop_loss': pattern_df.loc[idx, 'stop_loss'],
                'take_profit': pattern_df.loc[idx, 'take_profit']
            })
        
        # Pattern statistics
        pattern_counts = analysis_data['pattern_detected'].value_counts()
        pattern_stats = {}
        for pattern, count in pattern_counts.items():
            if pattern != '':
                pattern_stats[pattern] = int(count)
        
        return jsonify({
            'success': True,
            'analysis': {
                'symbol': symbol,
                'timeframe': timeframe,
                'current_signal': current_signal,
                'current_pattern': current_pattern,
                'current_price': current_price,
                'total_buy_signals': int(total_buy_signals),
                'total_sell_signals': int(total_sell_signals),
                'recent_patterns': recent_patterns,
                'pattern_statistics': pattern_stats,
                'chart_base64': chart_base64,
                'strategy_info': {
                    'name': strategy.name,
                    'description': 'Identifies and trades continuation patterns including triangles, flags, pennants, and rectangles'
                },
                'parameters_used': {
                    'min_pattern_bars': min_pattern_bars,
                    'trend_strength': trend_strength,
                    'volume_multiplier': volume_multiplier
                }
            },
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        print(f"Error in continuation patterns analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# Replace your comparison endpoint in app.py with this fixed version:

# Replace your comparison endpoint in app.py with this enhanced version:

@app.route('/api/strategies/compare', methods=['POST'])
@auth_required()
def compare_actual_vs_ai():
    """Compare actual trades from JSON with AI predictions"""
    try:
        print("=== COMPARISON ENDPOINT CALLED ===")
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        
        # Get actual trades from your existing P&L calculation
        actual_pnl_data = calculate_pnl_from_trades()
        
        if not actual_pnl_data.get('success'):
            return jsonify({
                'success': False,
                'error': 'Could not load actual trades'
            }), 500
        
        # Filter actual trades for the requested symbol
        actual_trades = [
            trade for trade in actual_pnl_data.get('trades', [])
            if trade.get('symbol', 'BTC/USDT') == symbol
        ]
        
        # Get AI predictions
        try:
            from strategies.technical.trendline_breakout import TrendlineBreakoutStrategy
            strategy = TrendlineBreakoutStrategy()
            ai_data = strategy.generate_signals(symbol, timeframe, 500)
        except Exception as e:
            print(f"Error generating AI predictions: {e}")
            ai_data = None
        
        if ai_data is None:
            return jsonify({
                'success': False,
                'error': 'Could not generate AI predictions'
            }), 500
        
        # Calculate AI strategy performance using FIFO matching
        ai_trades = []
        ai_position = 0
        ai_entry_price = 0
        ai_entry_time = None
        
        for idx, row in ai_data.iterrows():
            if row['buy_signal'] == 1 and ai_position == 0:
                # Enter position
                ai_position = 1
                ai_entry_price = float(row['close'])
                ai_entry_time = idx
                
            elif row['sell_signal'] == 1 and ai_position == 1:
                # Exit position
                exit_price = float(row['close'])
                pnl = exit_price - ai_entry_price
                pnl_percentage = (pnl / ai_entry_price) * 100
                
                ai_trades.append({
                    'entry_time': ai_entry_time.isoformat(),
                    'exit_time': idx.isoformat(),
                    'entry_price': ai_entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'pnl_percentage': pnl_percentage,
                    'is_winning': pnl > 0
                })
                
                ai_position = 0
                ai_entry_price = 0
                ai_entry_time = None
        
        # Calculate AI performance metrics
        ai_total_trades = len(ai_trades)
        ai_winning_trades = len([t for t in ai_trades if t['is_winning']])
        ai_losing_trades = ai_total_trades - ai_winning_trades
        ai_win_rate = float(ai_winning_trades / max(ai_total_trades, 1) * 100)
        ai_total_pnl = float(sum(t['pnl'] for t in ai_trades))
        
        # Extract AI signals for timeline comparison
        ai_buy_signals = []
        ai_sell_signals = []
        
        buy_points = ai_data[ai_data['buy_signal'] == 1]
        for idx, row in buy_points.iterrows():
            ai_buy_signals.append({
                'timestamp': idx.isoformat(),
                'price': float(row['close'])
            })
        
        sell_points = ai_data[ai_data['sell_signal'] == 1]
        for idx, row in sell_points.iterrows():
            ai_sell_signals.append({
                'timestamp': idx.isoformat(),
                'price': float(row['close'])
            })
        
        # Extract actual buy/sell points
        actual_buy_signals = []
        actual_sell_signals = []
        
        for trade in actual_trades:
            if trade.get('buy_timestamp'):
                actual_buy_signals.append({
                    'timestamp': datetime.fromtimestamp(trade['buy_timestamp'] / 1000).isoformat(),
                    'price': float(trade.get('buy_price', 0))
                })
            
            if trade.get('sell_timestamp'):
                actual_sell_signals.append({
                    'timestamp': datetime.fromtimestamp(trade['sell_timestamp'] / 1000).isoformat(),
                    'price': float(trade.get('sell_price', 0))
                })
        
        # Calculate actual trading metrics
        total_actual_trades = int(len(actual_trades))
        actual_profit = float(sum(trade.get('pnl', 0) for trade in actual_trades))
        actual_winning_trades = [t for t in actual_trades if t.get('pnl', 0) > 0]
        actual_win_rate = float(len(actual_winning_trades) / max(total_actual_trades, 1) * 100)
        
        # Comparison metrics
        total_ai_signals = int(len(ai_buy_signals) + len(ai_sell_signals))
        signal_frequency_ratio = float(total_ai_signals / max(total_actual_trades, 1))
        
        # Performance comparison
        performance_comparison = "Similar"
        if ai_win_rate > actual_win_rate + 5:
            performance_comparison = "AI performs better"
        elif actual_win_rate > ai_win_rate + 5:
            performance_comparison = "Your trading performs better"
        
        # Get current AI recommendation
        current_ai_recommendation = 0
        if not ai_data.empty:
            current_ai_recommendation = int(ai_data['buy_signal'].iloc[-1])
        
        # Analysis period
        analysis_period = {
            'start': ai_data.index[0].isoformat() if not ai_data.empty else None,
            'end': ai_data.index[-1].isoformat() if not ai_data.empty else None
        }
        
        return jsonify({
            'success': True,
            'comparison': {
                'symbol': symbol,
                'timeframe': timeframe,
                'actual_trading': {
                    'total_trades': total_actual_trades,
                    'total_pnl': actual_profit,
                    'win_rate': actual_win_rate,
                    'winning_trades': len(actual_winning_trades),
                    'losing_trades': total_actual_trades - len(actual_winning_trades),
                    'buy_signals': actual_buy_signals,
                    'sell_signals': actual_sell_signals
                },
                'ai_predictions': {
                    'total_signals': total_ai_signals,
                    'total_trades': ai_total_trades,
                    'total_pnl': ai_total_pnl,
                    'win_rate': ai_win_rate,
                    'winning_trades': ai_winning_trades,
                    'losing_trades': ai_losing_trades,
                    'buy_signals': ai_buy_signals,
                    'sell_signals': ai_sell_signals,
                    'current_recommendation': current_ai_recommendation,
                    'completed_trades': ai_trades
                },
                'metrics': {
                    'signal_frequency_ratio': signal_frequency_ratio,
                    'actual_win_rate': actual_win_rate,
                    'ai_win_rate': ai_win_rate,
                    'performance_comparison': performance_comparison,
                    'analysis_period': analysis_period
                }
            }
        })
    
    except Exception as e:
        print(f"❌ Error in compare_actual_vs_ai: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# RSI Strategy endpoints
@app.route('/api/strategies/rsi_strategy/analyze', methods=['POST'])
@auth_required()
def analyze_rsi_strategy():
    """Run RSI strategy analysis"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 500)
        
        # Extract RSI parameters
        rsi_period = data.get('rsi_period', 14)
        overbought_level = data.get('overbought_level', 70)
        oversold_level = data.get('oversold_level', 30)
        
        # Run analysis
        result = run_rsi_analysis(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            rsi_period=rsi_period,
            overbought_level=overbought_level,
            oversold_level=oversold_level
        )
        
        if result and result.get('success'):
            return jsonify({
                'success': True,
                'analysis': result,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Analysis failed') if result else 'Analysis failed'}), 500
    
    except Exception as e:
        print(f"Error in RSI analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategies/rsi_strategy/signals', methods=['POST'])
@auth_required()
def get_rsi_signals_only():
    """Get only RSI signals without chart"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 100)
        
        # Create strategy instance
        strategy = RSIStrategy()
        analysis_data = strategy.generate_signals(symbol, timeframe, limit)
        
        if analysis_data is None:
            return jsonify({'success': False, 'error': 'No data available'})
        
        return jsonify({
            'success': True,
            'signals': {
                'buy_signals': analysis_data.get('recent_signals', []),
                'current_signal': analysis_data.get('current_signal'),
                'current_price': analysis_data.get('current_price'),
                'current_rsi': analysis_data.get('current_rsi')
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Moving Average Crossover endpoints
@app.route('/api/strategies/ma_crossover/analyze', methods=['POST'])
@auth_required()
def analyze_ma_crossover():
    """Run Moving Average Crossover analysis"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 500)
        
        # Extract MA parameters
        fast_period = data.get('fast_period', 10)
        slow_period = data.get('slow_period', 30)
        ma_type = data.get('ma_type', 'sma')
        
        # Run analysis
        result = run_ma_crossover_analysis(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            fast_period=fast_period,
            slow_period=slow_period,
            ma_type=ma_type
        )
        
        if result and result.get('success'):
            return jsonify({
                'success': True,
                'analysis': result,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Analysis failed') if result else 'Analysis failed'}), 500
    
    except Exception as e:
        print(f"Error in MA Crossover analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategies/ma_crossover/signals', methods=['POST'])
@auth_required()
def get_ma_crossover_signals_only():
    """Get only MA Crossover signals without chart"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 100)
        
        # Create strategy instance
        strategy = MovingAverageCrossoverStrategy()
        analysis_data = strategy.generate_signals(symbol, timeframe, limit)
        
        if analysis_data is None:
            return jsonify({'success': False, 'error': 'No data available'})
        
        return jsonify({
            'success': True,
            'signals': {
                'buy_signals': analysis_data.get('recent_signals', []),
                'current_signal': analysis_data.get('current_signal'),
                'current_price': analysis_data.get('current_price'),
                'current_fast_ma': analysis_data.get('current_fast_ma'),
                'current_slow_ma': analysis_data.get('current_slow_ma')
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Bollinger Bands endpoints
@app.route('/api/strategies/bollinger_bands/analyze', methods=['POST'])
@auth_required()
def analyze_bollinger_bands():
    """Run Bollinger Bands analysis"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 500)
        
        # Extract BB parameters
        period = data.get('period', 20)
        std_dev = data.get('std_dev', 2.0)
        
        # Run analysis
        result = run_bollinger_bands_analysis(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            period=period,
            std_dev=std_dev
        )
        
        if result and result.get('success'):
            return jsonify({
                'success': True,
                'analysis': result,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Analysis failed') if result else 'Analysis failed'}), 500
    
    except Exception as e:
        print(f"Error in Bollinger Bands analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategies/bollinger_bands/signals', methods=['POST'])
@auth_required()
def get_bollinger_bands_signals_only():
    """Get only Bollinger Bands signals without chart"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 100)
        
        # Create strategy instance
        strategy = BollingerBandsStrategy()
        analysis_data = strategy.generate_signals(symbol, timeframe, limit)
        
        if analysis_data is None:
            return jsonify({'success': False, 'error': 'No data available'})
        
        return jsonify({
            'success': True,
            'signals': {
                'buy_signals': analysis_data.get('recent_signals', []),
                'current_signal': analysis_data.get('current_signal'),
                'current_price': analysis_data.get('current_price'),
                'current_bb_upper': analysis_data.get('current_bb_upper'),
                'current_bb_middle': analysis_data.get('current_bb_middle'),
                'current_bb_lower': analysis_data.get('current_bb_lower'),
                'current_bb_percent': analysis_data.get('current_bb_percent')
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Volume Spike endpoints
@app.route('/api/strategies/volume_spike/analyze', methods=['POST'])
@auth_required()
def analyze_volume_spike():
    """Run Volume Spike analysis"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 500)
        
        # Extract Volume Spike parameters
        volume_period = data.get('volume_period', 20)
        spike_multiplier = data.get('spike_multiplier', 2.0)
        price_change_threshold = data.get('price_change_threshold', 0.01)
        
        # Run analysis
        result = run_volume_spike_analysis(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            volume_period=volume_period,
            spike_multiplier=spike_multiplier,
            price_change_threshold=price_change_threshold
        )
        
        if result and result.get('success'):
            return jsonify({
                'success': True,
                'analysis': result,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Analysis failed') if result else 'Analysis failed'}), 500
    
    except Exception as e:
        print(f"Error in Volume Spike analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategies/volume_spike/signals', methods=['POST'])
@auth_required()
def get_volume_spike_signals_only():
    """Get only Volume Spike signals without chart"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 100)
        
        # Create strategy instance
        strategy = VolumeSpikeStrategy()
        analysis_data = strategy.generate_signals(symbol, timeframe, limit)
        
        if analysis_data is None:
            return jsonify({'success': False, 'error': 'No data available'})
        
        return jsonify({
            'success': True,
            'signals': {
                'buy_signals': analysis_data.get('recent_signals', []),
                'current_signal': analysis_data.get('current_signal'),
                'current_price': analysis_data.get('current_price'),
                'current_volume_ratio': analysis_data.get('current_volume_ratio'),
                'total_volume_spikes': analysis_data.get('total_volume_spikes')
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Reversal Patterns Strategy endpoints
@app.route('/api/strategies/reversal_patterns/analyze', methods=['POST'])
@auth_required()
def analyze_reversal_patterns():
    """Run Reversal Patterns strategy analysis"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 500)
        
        # Extract Reversal Patterns parameters
        lookback_period = data.get('lookback_period', 40)
        min_pattern_bars = data.get('min_pattern_bars', 8)
        volume_threshold = data.get('volume_threshold', 1.15)
        
        # Run analysis
        result = run_reversal_patterns_analysis(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            lookback_period=lookback_period,
            min_pattern_bars=min_pattern_bars,
            volume_threshold=volume_threshold
        )
        
        if result and result.get('success'):
            return jsonify({
                'success': True,
                'analysis': result,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Analysis failed') if result else 'Analysis failed'}), 500
    
    except Exception as e:
        print(f"Error in Reversal Patterns analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategies/reversal_patterns/signals', methods=['POST'])
@auth_required()
def get_reversal_patterns_signals_only():
    """Get only Reversal Patterns signals without chart"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 100)
        
        # Create strategy instance
        strategy = ReversalPatternsStrategy()
        analysis_data = strategy.generate_signals(symbol, timeframe, limit)
        
        if analysis_data is None:
            return jsonify({'success': False, 'error': 'No data available'})
        
        return jsonify({
            'success': True,
            'signals': {
                'recent_signals': analysis_data.get('recent_signals', []),
                'current_signal': analysis_data.get('current_signal'),
                'current_price': analysis_data.get('current_price'),
                'total_patterns_detected': analysis_data.get('total_patterns_detected'),
                'patterns_breakdown': analysis_data.get('patterns_breakdown')
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Authentication endpoints
@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
@require_valid_request
@validate_request_size(1)
@validate_json_input(UserRegistrationSchema)
@handle_exceptions(logger)
def register():
    """Register a new user"""
    data = request.validated_json
    
    logger.info(f"User registration attempt: {data.get('username')}")
    
    # Create user
    user = UserManager.create_user(
        username=data['username'],
        email=data['email'],
        password=data['password']
    )
    
    # Create tokens
    access_token, refresh_token = create_tokens(user)
    
    return jsonify({
        'success': True,
        'message': 'User registered successfully',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 201

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
@require_valid_request
@validate_request_size(1)
@validate_json_input(UserLoginSchema)
@handle_exceptions(logger)
def login():
    """Authenticate user and return tokens"""
    data = request.validated_json
    
    logger.info(f"Login attempt: {data.get('username_or_email')}")
    
    # Authenticate user
    user = UserManager.authenticate_user(
        username_or_email=data['username_or_email'],
        password=data['password']
    )
    
    # Create tokens
    access_token, refresh_token = create_tokens(user)
    
    return jsonify({
        'success': True,
        'message': 'Login successful',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    })

@app.route('/api/auth/refresh', methods=['POST'])
@limiter.limit("20 per minute")
@require_valid_request
@handle_exceptions(logger)
def refresh_token():
    """Refresh access token using refresh token"""
    from flask_jwt_extended import jwt_required, get_jwt_identity
    
    @jwt_required(refresh=True)
    def _refresh():
        user_id = get_jwt_identity()
        user = UserManager.get_user_by_id(user_id)
        
        # Create new access token
        access_token, _ = create_tokens(user)
        
        return jsonify({
            'success': True,
            'access_token': access_token
        })
    
    return _refresh()

@app.route('/api/auth/logout', methods=['POST'])
@limiter.limit("20 per minute")
@require_valid_request
@auth_required()
@handle_exceptions(logger)
def logout():
    """Logout user and revoke token"""
    from flask_jwt_extended import get_jwt
    from utils.auth import revoke_token
    
    # Get JWT claims
    claims = get_jwt()
    jti = claims['jti']
    
    # Revoke token
    revoke_token(jti, blacklisted_tokens)
    
    logger.info(f"User logged out: {request.current_user.username}")
    
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })

@app.route('/api/auth/profile', methods=['GET'])
@limiter.limit("30 per minute")
@require_valid_request
@auth_required()
@handle_exceptions(logger)
def get_profile():
    """Get current user profile"""
    user = request.current_user
    
    # Get user's portfolios
    portfolios = Portfolio.query.filter_by(user_id=user.id, is_active=True).all()
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'portfolios': [p.to_dict() for p in portfolios]
    })

@app.route('/api/auth/change-password', methods=['POST'])
@limiter.limit("5 per minute")
@require_valid_request
@validate_request_size(1)
@validate_json_input(PasswordChangeSchema)
@auth_required()
@handle_exceptions(logger)
def change_password():
    """Change user password"""
    data = request.validated_json
    user = request.current_user
    
    # Verify current password
    if not PasswordManager.verify_password(data['current_password'], user.password_hash):
        logger.warning(f"Password change failed for user {user.username}: invalid current password")
        return jsonify({
            'success': False,
            'error': 'INVALID_PASSWORD',
            'message': 'Current password is incorrect'
        }), 400
    
    # Validate new password
    is_valid, message = PasswordManager.validate_password_strength(data['new_password'])
    if not is_valid:
        return jsonify({
            'success': False,
            'error': 'WEAK_PASSWORD',
            'message': message
        }), 400
    
    # Update password
    user.password_hash = PasswordManager.hash_password(data['new_password'])
    db.session.commit()
    
    logger.info(f"Password changed for user: {user.username}")
    
    return jsonify({
        'success': True,
        'message': 'Password changed successfully'
    })

# WebSocket endpoints
@app.route('/api/websocket/info', methods=['GET'])
@limiter.limit("30 per minute")
@require_valid_request
@auth_required()
@handle_exceptions(logger)
def websocket_info():
    """Get WebSocket connection information"""
    user = request.current_user
    
    # Create a temporary token for WebSocket authentication
    from flask_jwt_extended import create_access_token
    ws_token = create_access_token(
        identity=str(user.id),
        expires_delta=False  # No expiration for WebSocket token
    )
    
    return jsonify({
        'success': True,
        'websocket_url': f"ws://{app.config['HOST']}:{app.config['PORT']}",
        'token': ws_token,
        'user_id': str(user.id)
    })

@app.route('/api/websocket/price-history/<symbol>', methods=['GET'])
@limiter.limit("20 per minute")
@require_valid_request
@auth_required()
@handle_exceptions(logger)
def get_price_history(symbol):
    """Get historical price data for a symbol"""
    try:
        # Validate symbol
        if '/' not in symbol:
            return jsonify({
                'success': False,
                'error': 'Invalid symbol format'
            }), 400
        
        # Get timeframe from query params
        timeframe = request.args.get('timeframe', '1h')
        limit = min(int(request.args.get('limit', 100)), 1000)
        
        # Query price history
        price_history = PriceHistory.query.filter_by(
            symbol=symbol,
            timeframe=timeframe
        ).order_by(PriceHistory.timestamp.desc()).limit(limit).all()
        
        # Format data for charting
        chart_data = []
        for record in reversed(price_history):  # Reverse to get chronological order
            chart_data.append({
                'timestamp': record.timestamp.isoformat(),
                'open': float(record.open),
                'high': float(record.high),
                'low': float(record.low),
                'close': float(record.close),
                'volume': float(record.volume)
            })
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'timeframe': timeframe,
            'data': chart_data,
            'count': len(chart_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting price history for {symbol}: {str(e)}")
        raise e

# Chart data endpoints
@app.route('/api/charts/ohlcv/<symbol>', methods=['GET'])
@limiter.limit("30 per minute")
@require_valid_request
@auth_required()
@handle_exceptions(logger)
def get_chart_ohlcv(symbol):
    """Get OHLCV chart data for a symbol"""
    # Get query parameters
    timeframe = request.args.get('timeframe', '1h')
    limit = min(int(request.args.get('limit', 500)), 1000)
    
    # Validate symbol format
    if '/' not in symbol:
        return jsonify({
            'success': False,
            'error': 'Invalid symbol format. Use format: BTC/USDT'
        }), 400
    
    try:
        chart_data = chart_service.get_ohlcv_data(symbol, timeframe, limit)
        
        return jsonify({
            'success': True,
            **chart_data
        })
        
    except Exception as e:
        logger.error(f"Error getting OHLCV chart data for {symbol}: {str(e)}")
        raise e

@app.route('/api/charts/strategy/<symbol>', methods=['GET'])
@limiter.limit("20 per minute")
@require_valid_request
@auth_required()
@handle_exceptions(logger)
def get_strategy_chart(symbol):
    """Get chart data with strategy signals"""
    # Get query parameters
    timeframe = request.args.get('timeframe', '1h')
    limit = min(int(request.args.get('limit', 500)), 1000)
    strategy = request.args.get('strategy', 'trendline_breakout')
    
    # Validate symbol format
    if '/' not in symbol:
        return jsonify({
            'success': False,
            'error': 'Invalid symbol format. Use format: BTC/USDT'
        }), 400
    
    try:
        chart_data = chart_service.get_strategy_chart_data(symbol, timeframe, limit, strategy)
        
        return jsonify({
            'success': True,
            **chart_data
        })
        
    except Exception as e:
        logger.error(f"Error getting strategy chart data for {symbol}: {str(e)}")
        raise e

@app.route('/api/charts/portfolio/<portfolio_id>', methods=['GET'])
@limiter.limit("20 per minute")
@require_valid_request
@auth_required()
@handle_exceptions(logger)
def get_portfolio_chart(portfolio_id):
    """Get portfolio performance chart data"""
    user = request.current_user
    
    # Verify portfolio belongs to user
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user.id).first()
    if not portfolio:
        return jsonify({
            'success': False,
            'error': 'Portfolio not found or access denied'
        }), 404
    
    timeframe = request.args.get('timeframe', '1d')
    
    try:
        chart_data = chart_service.get_portfolio_chart_data(portfolio_id, timeframe)
        
        return jsonify({
            'success': True,
            **chart_data
        })
        
    except Exception as e:
        logger.error(f"Error getting portfolio chart data: {str(e)}")
        raise e

@app.route('/api/charts/supported-symbols', methods=['GET'])
@limiter.limit("10 per minute")
@require_valid_request
@auth_required()
@handle_exceptions(logger)
def get_supported_symbols():
    """Get list of supported trading symbols"""
    # Common cryptocurrency symbols
    symbols = [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT',
        'DOT/USDT', 'MATIC/USDT', 'LINK/USDT', 'AVAX/USDT', 'UNI/USDT',
        'LTC/USDT', 'BCH/USDT', 'XRP/USDT', 'DOGE/USDT', 'SHIB/USDT',
        'ATOM/USDT', 'FIL/USDT', 'TRX/USDT', 'ETC/USDT', 'XLM/USDT'
    ]
    
    # Get available timeframes
    timeframes = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '3d', '1w']
    
    # Get available strategies
    strategies = [
        {
            'name': 'trendline_breakout',
            'display_name': 'Trendline Breakout',
            'description': 'Identifies breakouts from support and resistance trendlines'
        }
    ]
    
    return jsonify({
        'success': True,
        'symbols': symbols,
        'timeframes': timeframes,
        'strategies': strategies,
        'chart_types': ['candlestick', 'line', 'area'],
        'indicators': ['volume', 'trendlines', 'signals']
    })

@app.route('/api/trading-pairs', methods=['GET'])
@limiter.limit("10 per minute")
@handle_exceptions(logger)
def get_trading_pairs():
    """Get available trading pairs from Binance"""
    try:
        exchange = ccxt.binance({'enableRateLimit': True})
        markets = exchange.load_markets()
        
        # Filter for USDT pairs and active markets
        usdt_pairs = []
        seen_symbols = set()  # Track unique symbols
        
        for symbol, market in markets.items():
            if market['quote'] == 'USDT' and market['active'] and market.get('spot', True):
                # Get additional info for popular pairs
                base = market['base']
                # Skip stablecoins paired with USDT
                if base not in ['USDT', 'BUSD', 'USDC', 'DAI', 'TUSD', 'PAX', 'GUSD']:
                    # Create a normalized symbol to check for duplicates
                    normalized_symbol = f"{base}/USDT"
                    
                    # Only add if we haven't seen this symbol before
                    if normalized_symbol not in seen_symbols:
                        seen_symbols.add(normalized_symbol)
                        usdt_pairs.append({
                            'symbol': normalized_symbol,
                            'base': base,
                            'quote': 'USDT',
                            'displayName': normalized_symbol
                        })
        
        # Sort by base currency name
        usdt_pairs.sort(key=lambda x: x['base'])
        
        # Add a "Popular" category at the beginning
        popular_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 
                          'ADA/USDT', 'DOGE/USDT', 'MATIC/USDT', 'DOT/USDT', 'AVAX/USDT']
        
        popular_pairs = [pair for pair in usdt_pairs if pair['symbol'] in popular_symbols]
        
        # Ensure popular pairs are unique
        unique_popular = []
        seen_popular = set()
        for pair in popular_pairs:
            if pair['symbol'] not in seen_popular:
                seen_popular.add(pair['symbol'])
                unique_popular.append(pair)
        
        # Final deduplication of all pairs
        unique_pairs = []
        final_seen = set()
        for pair in usdt_pairs:
            if pair['symbol'] not in final_seen:
                final_seen.add(pair['symbol'])
                unique_pairs.append(pair)
        
        logger.info(f"Returning {len(unique_pairs)} unique trading pairs, {len(unique_popular)} popular")
        
        return jsonify({
            'success': True,
            'pairs': unique_pairs,
            'popular': unique_popular,
            'total': len(unique_pairs)
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch trading pairs: {str(e)}")
        # Return some default pairs if API fails
        default_pairs = [
            {'symbol': 'BTC/USDT', 'base': 'BTC', 'quote': 'USDT', 'displayName': 'BTC/USDT'},
            {'symbol': 'ETH/USDT', 'base': 'ETH', 'quote': 'USDT', 'displayName': 'ETH/USDT'},
            {'symbol': 'BNB/USDT', 'base': 'BNB', 'quote': 'USDT', 'displayName': 'BNB/USDT'},
            {'symbol': 'SOL/USDT', 'base': 'SOL', 'quote': 'USDT', 'displayName': 'SOL/USDT'},
            {'symbol': 'XRP/USDT', 'base': 'XRP', 'quote': 'USDT', 'displayName': 'XRP/USDT'},
        ]
        return jsonify({
            'success': True,
            'pairs': default_pairs,
            'popular': default_pairs,
            'total': len(default_pairs),
            'cached': True
        })

# Database management endpoints
@app.route('/api/admin/migrate-data', methods=['POST'])
@limiter.limit("1 per minute")
@require_valid_request
@admin_required
@handle_exceptions(logger)
def migrate_data_endpoint():
    """Migrate data from JSON files to database"""
    logger.info("Starting data migration via API endpoint")
    
    try:
        result = run_migration(app)
        logger.info("Data migration completed successfully")
        return jsonify({
            'success': True,
            'message': 'Data migration completed successfully',
            'details': result
        })
    except Exception as e:
        logger.error(f"Data migration failed: {str(e)}")
        raise e

@app.route('/api/admin/db-status', methods=['GET'])
@limiter.limit("10 per minute")
@require_valid_request
@admin_required
@handle_exceptions(logger)
def database_status():
    """Get database status and statistics"""
    try:
        # Check database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        
        # Get table counts
        stats = {
            'users': User.query.count(),
            'portfolios': Portfolio.query.count(),
            'trades': Trade.query.count(),
            'holdings': Holding.query.count()
        }
        
        return jsonify({
            'success': True,
            'database_connected': True,
            'statistics': stats
        })
    except Exception as e:
        logger.error(f"Database status check failed: {str(e)}")
        return jsonify({
            'success': False,
            'database_connected': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Use SocketIO run instead of app.run for WebSocket support
    socketio.run(
        app,
        debug=app.config['DEBUG'],
        host=app.config['HOST'],
        port=app.config['PORT'],
        allow_unsafe_werkzeug=True
    )
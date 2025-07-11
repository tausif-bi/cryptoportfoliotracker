from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import ccxt
import random
from utils.auth import auth_required
from utils.security import get_limiter, require_valid_request, validate_request_size
from utils.validators import ExchangeCredentialsSchema, validate_json_input
from utils.exceptions import handle_exceptions, handle_exchange_errors
from utils.logger import get_logger, log_exchange_operation
from models.database import db, Portfolio
from services.portfolio_service import PortfolioService
from services.exchange_service import ExchangeService

logger = get_logger(__name__)
portfolio_bp = Blueprint('portfolio', __name__, url_prefix='/api')
limiter = get_limiter()

# Initialize services
portfolio_service = PortfolioService()
exchange_service = ExchangeService()

@portfolio_bp.route('/analyze-portfolio', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
def analyze_portfolio():
    """Analyze portfolio endpoint"""
    try:
        data = request.json
        holdings = data.get('holdings', [])
        prices = data.get('prices', {})
        
        if not holdings:
            return jsonify({'error': 'No holdings provided'}), 400
        
        # Get analyzer from app context
        analyzer = current_app.config.get('portfolio_analyzer')
        if not analyzer:
            return jsonify({'error': 'Portfolio analyzer not initialized'}), 500
            
        analysis = analyzer.analyze_portfolio(holdings, prices)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f'Error in analyze_portfolio: {str(e)}', exc_info=True)
        if current_app.config.get('ENV') == 'production':
            return jsonify({'error': 'Failed to analyze portfolio. Please try again.'}), 500
        else:
            return jsonify({'error': str(e)}), 500

@portfolio_bp.route('/predict-price', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
def predict_price():
    """Predict price movement endpoint"""
    try:
        data = request.json
        symbol = data.get('symbol')
        exchange = data.get('exchange', 'binance')
        
        if not symbol:
            return jsonify({'error': 'No symbol provided'}), 400
        
        # Get analyzer from app context
        analyzer = current_app.config.get('portfolio_analyzer')
        if not analyzer:
            return jsonify({'error': 'Portfolio analyzer not initialized'}), 500
        
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

@portfolio_bp.route('/market-analysis', methods=['GET'])
@limiter.limit("30 per minute")
@require_valid_request
@handle_exceptions(logger)
def market_analysis():
    """Get overall market analysis"""
    try:
        # Get analyzer from app context
        analyzer = current_app.config.get('portfolio_analyzer')
        if not analyzer:
            return jsonify({'error': 'Portfolio analyzer not initialized'}), 500
            
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
        avg_change = sum(d['change24h'] for d in market_data) / len(market_data) if market_data else 0
        
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

@portfolio_bp.route('/rebalancing-suggestions', methods=['POST'])
@handle_exceptions(logger)
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

@portfolio_bp.route('/verify-exchange', methods=['POST'])
@limiter.limit("5 per minute")
@auth_required()
@require_valid_request
@validate_request_size(1)
@validate_json_input(ExchangeCredentialsSchema)
@handle_exceptions(logger)
def verify_exchange():
    """Verify exchange credentials"""
    data = request.validated_json
    exchange_name = data.get('exchangeName')
    
    logger.info(f"Verifying exchange credentials", extra={
        'exchange': exchange_name,
        'api_key_length': len(data.get('apiKey', ''))
    })
    
    # Handle demo mode
    if exchange_name == 'demo':
        log_exchange_operation(exchange_name, 'verify_credentials', success=True)
        return jsonify({'success': True, 'message': 'Demo mode - credentials accepted'})
    
    try:
        # Use exchange service to verify
        result = exchange_service.verify_credentials(
            exchange_name=exchange_name,
            api_key=data.get('apiKey'),
            api_secret=data.get('apiSecret'),
            password=data.get('password')
        )
        
        log_exchange_operation(exchange_name, 'verify_credentials', success=True)
        return jsonify({'success': True})
        
    except Exception as e:
        log_exchange_operation(exchange_name, 'verify_credentials', success=False, error=str(e))
        raise

@portfolio_bp.route('/fetch-balance', methods=['POST'])
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
    
    logger.info(f"Fetching balance from {exchange_name}")
    
    try:
        # Use exchange service to fetch balance
        balance = exchange_service.fetch_balance(
            exchange_name=exchange_name,
            api_key=data.get('apiKey'),
            api_secret=data.get('apiSecret'),
            password=data.get('password')
        )
        
        log_exchange_operation(exchange_name, 'fetch_balance', success=True)
        return jsonify({
            'success': True,
            'balance': balance
        })
        
    except Exception as e:
        log_exchange_operation(exchange_name, 'fetch_balance', success=False, error=str(e))
        raise

@portfolio_bp.route('/fetch-trades', methods=['POST'])
@limiter.limit("10 per minute")
@auth_required()
@require_valid_request
@validate_request_size(1)
@validate_json_input(ExchangeCredentialsSchema)
@handle_exceptions(logger)
def fetch_trades():
    """Fetch exchange trades"""
    data = request.validated_json
    exchange_name = data.get('exchangeName')
    symbol = data.get('symbol', 'BTC/USDT')
    limit = data.get('limit', 50)
    
    logger.info(f"Fetching trades from {exchange_name} for {symbol}")
    
    try:
        # Use exchange service to fetch trades
        trades = exchange_service.fetch_trades(
            exchange_name=exchange_name,
            api_key=data.get('apiKey'),
            api_secret=data.get('apiSecret'),
            password=data.get('password'),
            symbol=symbol,
            limit=limit
        )
        
        log_exchange_operation(exchange_name, 'fetch_trades', success=True)
        return jsonify({
            'success': True,
            'trades': trades
        })
        
    except Exception as e:
        log_exchange_operation(exchange_name, 'fetch_trades', success=False, error=str(e))
        raise

@portfolio_bp.route('/portfolio-stats', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
def portfolio_stats():
    """Calculate portfolio statistics"""
    try:
        data = request.json
        exchange_name = data.get('exchangeName')
        
        logger.info(f"Fetching portfolio stats for {exchange_name}")
        
        # Use portfolio service to get stats
        stats = portfolio_service.get_portfolio_stats(
            exchange_name=exchange_name,
            api_key=data.get('apiKey'),
            api_secret=data.get('apiSecret'),
            password=data.get('password')
        )
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        error_msg = f"Error in portfolio_stats: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({
            'success': False, 
            'error': str(e),
            'exchange': data.get('exchangeName')
        }), 500
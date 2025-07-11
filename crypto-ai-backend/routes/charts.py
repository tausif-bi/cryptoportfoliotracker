from flask import Blueprint, request, jsonify
from utils.auth import auth_required
from utils.security import get_limiter, require_valid_request
from utils.exceptions import handle_exceptions
from utils.logger import get_logger
from models.database import Portfolio
from services.chart_service import chart_service

logger = get_logger(__name__)
charts_bp = Blueprint('charts', __name__, url_prefix='/api/charts')
limiter = get_limiter()

@charts_bp.route('/ohlcv/<symbol>', methods=['GET'])
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

@charts_bp.route('/strategy/<symbol>', methods=['GET'])
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

@charts_bp.route('/portfolio/<portfolio_id>', methods=['GET'])
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

@charts_bp.route('/supported-symbols', methods=['GET'])
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
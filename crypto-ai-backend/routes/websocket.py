from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token
from utils.auth import auth_required
from utils.security import get_limiter, require_valid_request
from utils.exceptions import handle_exceptions
from utils.logger import get_logger
from models.database import PriceHistory

logger = get_logger(__name__)
websocket_bp = Blueprint('websocket', __name__, url_prefix='/api/websocket')
limiter = get_limiter()

@websocket_bp.route('/info', methods=['GET'])
@limiter.limit("30 per minute")
@require_valid_request
@auth_required()
@handle_exceptions(logger)
def websocket_info():
    """Get WebSocket connection information"""
    user = request.current_user
    
    # Create a temporary token for WebSocket authentication
    ws_token = create_access_token(
        identity=str(user.id),
        expires_delta=False  # No expiration for WebSocket token
    )
    
    return jsonify({
        'success': True,
        'websocket_url': f"ws://{current_app.config['HOST']}:{current_app.config['PORT']}",
        'token': ws_token,
        'user_id': str(user.id)
    })

@websocket_bp.route('/price-history/<symbol>', methods=['GET'])
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
"""
WebSocket service for real-time price updates and notifications
"""
import threading
import time
import json
from datetime import datetime, timezone
from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token
import ccxt
import asyncio
from utils.logger import get_logger
from utils.auth import UserManager
from models.database import db, User, PriceHistory
from decimal import Decimal

logger = get_logger(__name__)

class PriceStreamService:
    """Service for streaming real-time cryptocurrency prices"""
    
    def __init__(self, socketio):
        self.socketio = socketio
        self.exchanges = {}
        self.price_cache = {}
        self.subscribers = {}  # {symbol: {user_id: socket_id}}
        self.update_thread = None
        self.running = False
        
        # Initialize exchanges
        self.init_exchanges()
    
    def init_exchanges(self):
        """Initialize exchange connections for price streaming"""
        try:
            # Initialize Binance for primary price feeds
            self.exchanges['binance'] = ccxt.binance({
                'enableRateLimit': True,
                'sandbox': False
            })
            
            # Initialize backup exchanges
            self.exchanges['coinbase'] = ccxt.coinbase({
                'enableRateLimit': True,
                'sandbox': False
            })
            
            logger.info("Initialized exchanges for price streaming")
            
        except Exception as e:
            logger.error(f"Failed to initialize exchanges: {str(e)}")
    
    def start_price_streaming(self):
        """Start the price streaming service"""
        if self.running:
            return
        
        self.running = True
        self.update_thread = threading.Thread(target=self._price_update_loop, daemon=True)
        self.update_thread.start()
        
        logger.info("Price streaming service started")
    
    def stop_price_streaming(self):
        """Stop the price streaming service"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        
        logger.info("Price streaming service stopped")
    
    def _price_update_loop(self):
        """Main loop for fetching and broadcasting price updates"""
        while self.running:
            try:
                # Get list of symbols that have subscribers
                symbols_to_update = list(self.subscribers.keys())
                
                if symbols_to_update:
                    # Fetch prices for subscribed symbols
                    price_updates = self._fetch_current_prices(symbols_to_update)
                    
                    # Broadcast updates to subscribers
                    for symbol, price_data in price_updates.items():
                        self._broadcast_price_update(symbol, price_data)
                        
                        # Cache price data
                        self.price_cache[symbol] = price_data
                        
                        # Store in database for history
                        self._store_price_history(symbol, price_data)
                
                # Sleep for next update (every 30 seconds)
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in price update loop: {str(e)}")
                time.sleep(10)  # Wait before retrying
    
    def _fetch_current_prices(self, symbols):
        """Fetch current prices for given symbols"""
        price_updates = {}
        
        for symbol in symbols:
            try:
                # Try primary exchange first (Binance)
                exchange = self.exchanges.get('binance')
                if exchange:
                    ticker = exchange.fetch_ticker(symbol)
                    
                    price_updates[symbol] = {
                        'symbol': symbol,
                        'price': float(ticker['last']),
                        'change_24h': float(ticker['percentage']) if ticker['percentage'] else 0,
                        'volume_24h': float(ticker['quoteVolume']) if ticker['quoteVolume'] else 0,
                        'high_24h': float(ticker['high']) if ticker['high'] else 0,
                        'low_24h': float(ticker['low']) if ticker['low'] else 0,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'source': 'binance'
                    }
                    
            except Exception as e:
                logger.warning(f"Failed to fetch price for {symbol} from primary exchange: {str(e)}")
                
                # Try backup exchange
                try:
                    exchange = self.exchanges.get('coinbase')
                    if exchange and symbol.replace('/', '-') in ['BTC-USD', 'ETH-USD']:
                        # Coinbase uses different symbol format
                        cb_symbol = symbol.replace('/', '-')
                        ticker = exchange.fetch_ticker(cb_symbol)
                        
                        price_updates[symbol] = {
                            'symbol': symbol,
                            'price': float(ticker['last']),
                            'change_24h': float(ticker['percentage']) if ticker['percentage'] else 0,
                            'volume_24h': float(ticker['quoteVolume']) if ticker['quoteVolume'] else 0,
                            'high_24h': float(ticker['high']) if ticker['high'] else 0,
                            'low_24h': float(ticker['low']) if ticker['low'] else 0,
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'source': 'coinbase'
                        }
                        
                except Exception as e2:
                    logger.error(f"Failed to fetch price for {symbol} from backup exchange: {str(e2)}")
        
        return price_updates
    
    def _broadcast_price_update(self, symbol, price_data):
        """Broadcast price update to all subscribers of a symbol"""
        if symbol in self.subscribers:
            room = f"price_{symbol.replace('/', '_')}"
            self.socketio.emit('price_update', price_data, room=room)
            
            logger.debug(f"Broadcasted price update for {symbol} to {len(self.subscribers[symbol])} subscribers")
    
    def _store_price_history(self, symbol, price_data):
        """Store price data in database for historical analysis"""
        try:
            # Only store every 5th update to avoid too much data
            current_time = datetime.now(timezone.utc)
            if current_time.minute % 5 == 0:
                
                price_history = PriceHistory(
                    symbol=symbol,
                    timeframe='1m',
                    timestamp=current_time,
                    open=Decimal(str(price_data['price'])),
                    high=Decimal(str(price_data['high_24h'])),
                    low=Decimal(str(price_data['low_24h'])),
                    close=Decimal(str(price_data['price'])),
                    volume=Decimal(str(price_data['volume_24h']))
                )
                
                db.session.add(price_history)
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Failed to store price history for {symbol}: {str(e)}")
    
    def subscribe_to_symbol(self, user_id, socket_id, symbol):
        """Subscribe user to price updates for a symbol"""
        if symbol not in self.subscribers:
            self.subscribers[symbol] = {}
        
        self.subscribers[symbol][user_id] = socket_id
        
        # Send current cached price if available
        if symbol in self.price_cache:
            room = f"price_{symbol.replace('/', '_')}"
            self.socketio.emit('price_update', self.price_cache[symbol], room=room)
        
        logger.info(f"User {user_id} subscribed to {symbol} price updates")
    
    def unsubscribe_from_symbol(self, user_id, symbol):
        """Unsubscribe user from price updates for a symbol"""
        if symbol in self.subscribers and user_id in self.subscribers[symbol]:
            del self.subscribers[symbol][user_id]
            
            # Clean up empty symbol subscriptions
            if not self.subscribers[symbol]:
                del self.subscribers[symbol]
        
        logger.info(f"User {user_id} unsubscribed from {symbol} price updates")
    
    def unsubscribe_user_all(self, user_id):
        """Unsubscribe user from all symbols"""
        symbols_to_remove = []
        for symbol in self.subscribers:
            if user_id in self.subscribers[symbol]:
                del self.subscribers[symbol][user_id]
                
                # Mark for cleanup if empty
                if not self.subscribers[symbol]:
                    symbols_to_remove.append(symbol)
        
        # Clean up empty subscriptions
        for symbol in symbols_to_remove:
            del self.subscribers[symbol]
        
        logger.info(f"User {user_id} unsubscribed from all price updates")

def init_websocket(app):
    """Initialize WebSocket service with Flask app"""
    
    # Configure SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",  # Configure appropriately for production
        logger=False,
        engineio_logger=False,
        async_mode='threading'
    )
    
    # Initialize price streaming service
    price_service = PriceStreamService(socketio)
    
    # Start price streaming
    price_service.start_price_streaming()
    
    # Authentication middleware for WebSocket
    def authenticate_socket():
        """Authenticate WebSocket connection using JWT token"""
        try:
            token = request.args.get('token')
            if not token:
                logger.warning("WebSocket connection attempted without token")
                return False
            
            # Decode JWT token
            decoded_token = decode_token(token)
            user_id = decoded_token['sub']
            
            # Verify user exists and is active
            user = UserManager.get_user_by_id(user_id)
            if not user:
                logger.warning(f"WebSocket connection attempted with invalid user: {user_id}")
                return False
            
            # Store user info in session
            request.current_user = user
            return True
            
        except Exception as e:
            logger.warning(f"WebSocket authentication failed: {str(e)}")
            return False
    
    # WebSocket event handlers
    @socketio.on('connect')
    def handle_connect():
        """Handle new WebSocket connection"""
        if not authenticate_socket():
            disconnect()
            return False
        
        user = request.current_user
        logger.info(f"WebSocket connected: {user.username}")
        
        emit('connected', {
            'status': 'connected',
            'user': user.to_dict(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle WebSocket disconnection"""
        if hasattr(request, 'current_user'):
            user = request.current_user
            
            # Unsubscribe user from all price updates
            price_service.unsubscribe_user_all(str(user.id))
            
            logger.info(f"WebSocket disconnected: {user.username}")
    
    @socketio.on('subscribe_prices')
    def handle_subscribe_prices(data):
        """Handle subscription to price updates"""
        if not hasattr(request, 'current_user'):
            emit('error', {'message': 'Authentication required'})
            return
        
        user = request.current_user
        symbols = data.get('symbols', [])
        
        for symbol in symbols:
            # Validate symbol format
            if '/' not in symbol or len(symbol.split('/')) != 2:
                emit('error', {'message': f'Invalid symbol format: {symbol}'})
                continue
            
            # Join price room
            room = f"price_{symbol.replace('/', '_')}"
            join_room(room)
            
            # Subscribe to price service
            price_service.subscribe_to_symbol(str(user.id), request.sid, symbol)
        
        emit('subscribed', {
            'symbols': symbols,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    @socketio.on('unsubscribe_prices')
    def handle_unsubscribe_prices(data):
        """Handle unsubscription from price updates"""
        if not hasattr(request, 'current_user'):
            return
        
        user = request.current_user
        symbols = data.get('symbols', [])
        
        for symbol in symbols:
            # Leave price room
            room = f"price_{symbol.replace('/', '_')}"
            leave_room(room)
            
            # Unsubscribe from price service
            price_service.unsubscribe_from_symbol(str(user.id), symbol)
        
        emit('unsubscribed', {
            'symbols': symbols,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    @socketio.on('get_portfolio_summary')
    def handle_get_portfolio_summary():
        """Get real-time portfolio summary"""
        if not hasattr(request, 'current_user'):
            emit('error', {'message': 'Authentication required'})
            return
        
        user = request.current_user
        
        try:
            # Get user's default portfolio
            from models.database import Portfolio, Holding
            portfolio = Portfolio.query.filter_by(
                user_id=user.id, 
                is_default=True, 
                is_active=True
            ).first()
            
            if not portfolio:
                emit('portfolio_summary', {
                    'total_value': 0,
                    'holdings': [],
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                return
            
            # Get holdings with current prices
            holdings = Holding.query.filter_by(portfolio_id=portfolio.id).all()
            
            total_value = 0
            holdings_data = []
            
            for holding in holdings:
                # Get current price from cache
                symbol = f"{holding.asset}/USDT"
                current_price = 0
                
                if symbol in price_service.price_cache:
                    current_price = price_service.price_cache[symbol]['price']
                
                current_value = float(holding.total_quantity) * current_price
                total_value += current_value
                
                holdings_data.append({
                    'asset': holding.asset,
                    'quantity': float(holding.total_quantity),
                    'current_price': current_price,
                    'current_value': current_value,
                    'allocation': (current_value / total_value * 100) if total_value > 0 else 0
                })
            
            emit('portfolio_summary', {
                'total_value': total_value,
                'holdings': holdings_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {str(e)}")
            emit('error', {'message': 'Failed to get portfolio summary'})
    
    return socketio, price_service
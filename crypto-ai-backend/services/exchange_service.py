import ccxt
from utils.logger import get_logger
from utils.exceptions import ExchangeConnectionError, InvalidCredentialsError
from models.portfolio_analyzer import generate_synthetic_trades_with_real_prices

logger = get_logger(__name__)


class ExchangeService:
    """Service class for exchange-related operations"""
    
    def verify_credentials(self, exchange_name, api_key, api_secret, password=None):
        """Verify exchange credentials"""
        try:
            exchange = self._create_exchange(exchange_name, api_key, api_secret, password)
            
            # Load markets first
            exchange.load_markets()
            logger.info(f"Successfully loaded markets for {exchange_name}")
            
            # Try to fetch balance to verify credentials
            balance = exchange.fetch_balance()
            logger.info(f"Successfully verified credentials for {exchange_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Exchange verification error: {str(e)}")
            raise ExchangeConnectionError(f"Failed to verify {exchange_name} credentials: {str(e)}")
    
    def fetch_balance(self, exchange_name, api_key, api_secret, password=None):
        """Fetch exchange balance"""
        if exchange_name == 'demo':
            return self._get_demo_balance()
        
        try:
            exchange = self._create_exchange(exchange_name, api_key, api_secret, password)
            balance = exchange.fetch_balance()
            return self._format_balance(balance)
            
        except Exception as e:
            logger.error(f"Error fetching balance: {str(e)}")
            raise ExchangeConnectionError(f"Failed to fetch balance: {str(e)}")
    
    def fetch_trades(self, exchange_name, api_key, api_secret, password=None, symbol='BTC/USDT', limit=50):
        """Fetch exchange trades"""
        if exchange_name == 'demo':
            return self._get_demo_trades(limit)
        
        try:
            exchange = self._create_exchange(exchange_name, api_key, api_secret, password)
            trades = exchange.fetch_my_trades(symbol, limit=limit)
            return trades
            
        except Exception as e:
            logger.error(f"Error fetching trades: {str(e)}")
            raise ExchangeConnectionError(f"Failed to fetch trades: {str(e)}")
    
    def _create_exchange(self, exchange_name, api_key, api_secret, password=None):
        """Create and configure exchange instance"""
        # Handle lbank2 -> lbank mapping
        actual_exchange_name = exchange_name
        if exchange_name == 'lbank2':
            actual_exchange_name = 'lbank'
        
        # Validate exchange exists
        if not hasattr(ccxt, actual_exchange_name):
            raise InvalidCredentialsError(f"Exchange {actual_exchange_name} not supported")
        
        exchange_class = getattr(ccxt, actual_exchange_name)
        config = {
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        }
        
        # Special handling for lbank
        if actual_exchange_name == 'lbank':
            config['sandbox'] = False
            config['version'] = 'v2'
            config['options'] = {
                'defaultType': 'spot',
                'createMarketBuyOrderRequiresPrice': True
            }
            
            # Check if this might be an RSA key
            is_rsa_key = api_secret and ('-----BEGIN' in api_secret or len(api_secret) > 200)
            
            if is_rsa_key:
                logger.warning("Detected possible RSA private key format")
                raise InvalidCredentialsError(
                    "Invalid API Secret format. LBank requires the API Secret for HMAC authentication, "
                    "not an RSA private key. Please check your LBank API settings."
                )
        
        if password and actual_exchange_name not in ['lbank']:
            config['password'] = password
        
        exchange = exchange_class(config)
        exchange.load_markets()
        
        return exchange
    
    def _format_balance(self, balance):
        """Format balance data consistently"""
        formatted = {}
        
        for currency, amounts in balance.items():
            if isinstance(amounts, dict) and 'total' in amounts:
                formatted[currency] = {
                    'free': amounts.get('free', 0),
                    'used': amounts.get('used', 0),
                    'total': amounts.get('total', 0)
                }
        
        return formatted
    
    def _get_demo_balance(self):
        """Get demo balance"""
        from models.portfolio_analyzer import calculate_balance_from_trades
        return calculate_balance_from_trades()
    
    def _get_demo_trades(self, limit):
        """Get demo trades"""
        trades = generate_synthetic_trades_with_real_prices(limit)
        return trades[:limit] if trades else []
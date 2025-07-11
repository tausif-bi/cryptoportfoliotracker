import ccxt
import random
from datetime import datetime
from models.portfolio_analyzer import (
    PortfolioAnalyzer, calculate_balance_from_trades,
    generate_synthetic_balance
)
from utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioService:
    """Service class for portfolio-related business logic"""
    
    def __init__(self):
        self.analyzer = PortfolioAnalyzer()
    
    def get_portfolio_stats(self, exchange_name, api_key, api_secret, password=None):
        """Calculate portfolio statistics"""
        logger.info(f"Fetching portfolio stats for {exchange_name}")
        
        # Handle demo mode
        if exchange_name == 'demo':
            return self._get_demo_portfolio_stats()
        
        # Handle real exchanges
        try:
            exchange = self._initialize_exchange(exchange_name, api_key, api_secret, password)
            balance = exchange.fetch_balance()
            
            # Get all tickers for price lookups
            all_tickers = self._fetch_tickers(exchange)
            
            # Process holdings
            holdings = self._process_balance_to_holdings(balance, all_tickers)
            
            # Calculate statistics
            total_value = sum(h['usdValue'] for h in holdings)
            
            # Calculate allocations
            for holding in holdings:
                holding['allocation'] = (holding['usdValue'] / total_value) * 100 if total_value > 0 else 0
            
            # Sort by value
            holdings.sort(key=lambda x: x['usdValue'], reverse=True)
            
            return {
                'totalValue': total_value,
                'holdings': holdings,
                'numberOfAssets': len(holdings),
            }
            
        except Exception as e:
            logger.error(f"Error in portfolio_stats: {str(e)}", exc_info=True)
            raise
    
    def _get_demo_portfolio_stats(self):
        """Get portfolio stats for demo mode"""
        balance = calculate_balance_from_trades()
        
        # Try to fetch real current prices
        try:
            exchange = ccxt.binance({'enableRateLimit': True})
            tickers = exchange.fetch_tickers(['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT'])
            
            all_tickers = {}
            for symbol, ticker in tickers.items():
                all_tickers[symbol] = {
                    'last': ticker['last'],
                    'percentage': ticker['percentage'] or random.uniform(-5, 5)
                }
            
            # Add estimated prices for other coins
            if 'BTC/USDT' in tickers:
                btc_change = tickers['BTC/USDT']['percentage'] or 0
                all_tickers['DOT/USDT'] = {'last': 7.5 * (1 + btc_change/100 * 0.8), 'percentage': btc_change * 0.8}
                all_tickers['MATIC/USDT'] = {'last': 0.75 * (1 + btc_change/100 * 1.2), 'percentage': btc_change * 1.2}
                all_tickers['LINK/USDT'] = {'last': 15 * (1 + btc_change/100 * 0.9), 'percentage': btc_change * 0.9}
                all_tickers['AVAX/USDT'] = {'last': 40 * (1 + btc_change/100 * 1.1), 'percentage': btc_change * 1.1}
                all_tickers['XRP/USDT'] = {'last': 0.52 * (1 + btc_change/100 * 0.7), 'percentage': btc_change * 0.7}
            
        except Exception as e:
            logger.warning(f"Could not fetch real prices, using defaults: {e}")
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
        
        return {
            'totalValue': total_value,
            'holdings': holdings,
            'numberOfAssets': len(holdings),
        }
    
    def _initialize_exchange(self, exchange_name, api_key, api_secret, password=None):
        """Initialize CCXT exchange instance"""
        # Handle lbank2 -> lbank mapping
        actual_exchange_name = exchange_name
        if exchange_name == 'lbank2':
            actual_exchange_name = 'lbank'
        
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
        
        if password and actual_exchange_name not in ['lbank']:
            config['password'] = password
        
        exchange = exchange_class(config)
        exchange.load_markets()
        
        return exchange
    
    def _fetch_tickers(self, exchange):
        """Fetch all tickers from exchange"""
        try:
            return exchange.fetch_tickers()
        except Exception as e:
            logger.warning(f"Could not fetch all tickers: {e}")
            return {}
    
    def _process_balance_to_holdings(self, balance, all_tickers):
        """Process balance data into holdings format"""
        holdings = []
        
        for coin, amounts in balance.items():
            if isinstance(amounts, dict) and amounts.get('total', 0) > 0.0001:
                amount = amounts['total']
                
                # Get USD value
                if coin in ['USDT', 'USD', 'BUSD', 'USDC']:
                    usd_value = amount
                    price = 1
                    change_24h = 0
                else:
                    # Try different symbol formats
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
                    
                    if price is None:
                        logger.warning(f"Could not get price for {coin}")
                        continue
                    
                    usd_value = amount * price
                
                holdings.append({
                    'coin': coin,
                    'amount': amount,
                    'usdValue': usd_value,
                    'price': price,
                    'change24h': change_24h,
                })
        
        return holdings
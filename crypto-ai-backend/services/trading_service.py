import json
import os
from datetime import datetime
from collections import defaultdict
from utils.logger import get_logger

logger = get_logger(__name__)


class TradingService:
    """Service class for trading-related operations"""
    
    def calculate_pnl_from_trades(self):
        """Calculate P&L from trades using FIFO matching"""
        try:
            trades = self._load_trades_from_file()
            
            if not trades:
                return {
                    'success': True,
                    'summary': self._empty_summary(),
                    'trades': []
                }
            
            # Process trades using FIFO
            completed_trades = self._match_trades_fifo(trades)
            
            # Calculate summary statistics
            summary = self._calculate_summary(completed_trades)
            
            return {
                'success': True,
                'summary': summary,
                'trades': completed_trades
            }
            
        except Exception as e:
            logger.error(f"Error calculating P&L: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'summary': self._empty_summary(),
                'trades': []
            }
    
    def get_supported_trading_pairs(self):
        """Get list of supported trading pairs"""
        major_pairs = [
            {'symbol': 'BTC/USDT', 'name': 'Bitcoin', 'volume': 'high'},
            {'symbol': 'ETH/USDT', 'name': 'Ethereum', 'volume': 'high'},
            {'symbol': 'BNB/USDT', 'name': 'Binance Coin', 'volume': 'high'},
            {'symbol': 'SOL/USDT', 'name': 'Solana', 'volume': 'high'},
            {'symbol': 'ADA/USDT', 'name': 'Cardano', 'volume': 'medium'},
        ]
        
        altcoins = [
            {'symbol': 'DOT/USDT', 'name': 'Polkadot', 'volume': 'medium'},
            {'symbol': 'MATIC/USDT', 'name': 'Polygon', 'volume': 'medium'},
            {'symbol': 'LINK/USDT', 'name': 'Chainlink', 'volume': 'medium'},
            {'symbol': 'AVAX/USDT', 'name': 'Avalanche', 'volume': 'medium'},
            {'symbol': 'UNI/USDT', 'name': 'Uniswap', 'volume': 'medium'},
        ]
        
        stablecoins = [
            {'symbol': 'USDC/USDT', 'name': 'USD Coin', 'volume': 'low'},
            {'symbol': 'BUSD/USDT', 'name': 'Binance USD', 'volume': 'low'},
            {'symbol': 'DAI/USDT', 'name': 'DAI', 'volume': 'low'},
        ]
        
        return {
            'major': major_pairs,
            'altcoins': altcoins,
            'stablecoins': stablecoins,
            'all': major_pairs + altcoins + stablecoins
        }
    
    def _load_trades_from_file(self):
        """Load trades from JSON file"""
        try:
            if os.path.exists('simulated_trades.json'):
                with open('simulated_trades.json', 'r') as f:
                    data = json.load(f)
                    
                if isinstance(data, dict) and 'trades' in data:
                    return data['trades']
                elif isinstance(data, list):
                    return data
                else:
                    logger.warning("Unexpected data format in simulated_trades.json")
                    return []
            else:
                logger.info("simulated_trades.json not found")
                return []
                
        except Exception as e:
            logger.error(f"Error loading trades from file: {str(e)}")
            return []
    
    def _match_trades_fifo(self, trades):
        """Match buy and sell trades using FIFO"""
        # Group trades by symbol
        trades_by_symbol = defaultdict(lambda: {'buys': [], 'sells': []})
        
        for trade in trades:
            if not isinstance(trade, dict) or 'symbol' not in trade:
                continue
                
            symbol = trade['symbol']
            side = trade.get('side', '').lower()
            
            if side == 'buy':
                trades_by_symbol[symbol]['buys'].append(trade)
            elif side == 'sell':
                trades_by_symbol[symbol]['sells'].append(trade)
        
        completed_trades = []
        
        # Process each symbol
        for symbol, symbol_trades in trades_by_symbol.items():
            buys = sorted(symbol_trades['buys'], key=lambda x: x.get('timestamp', 0))
            sells = sorted(symbol_trades['sells'], key=lambda x: x.get('timestamp', 0))
            
            # FIFO matching
            buy_queue = []
            
            for trade in sorted(buys + sells, key=lambda x: x.get('timestamp', 0)):
                if trade.get('side') == 'buy':
                    buy_queue.append({
                        'amount': trade.get('amount', 0),
                        'price': trade.get('price', 0),
                        'timestamp': trade.get('timestamp', 0),
                        'id': trade.get('id', '')
                    })
                elif trade.get('side') == 'sell' and buy_queue:
                    sell_amount = trade.get('amount', 0)
                    sell_price = trade.get('price', 0)
                    sell_timestamp = trade.get('timestamp', 0)
                    
                    while sell_amount > 0 and buy_queue:
                        buy = buy_queue[0]
                        
                        # Calculate match amount
                        match_amount = min(sell_amount, buy['amount'])
                        
                        # Calculate P&L
                        pnl = (sell_price - buy['price']) * match_amount
                        pnl_percentage = ((sell_price - buy['price']) / buy['price']) * 100
                        
                        # Create completed trade
                        completed_trade = {
                            'symbol': symbol,
                            'buy_price': buy['price'],
                            'sell_price': sell_price,
                            'amount': match_amount,
                            'buy_timestamp': buy['timestamp'],
                            'sell_timestamp': sell_timestamp,
                            'pnl': pnl,
                            'pnl_percentage': pnl_percentage,
                            'is_winning': pnl > 0
                        }
                        
                        completed_trades.append(completed_trade)
                        
                        # Update amounts
                        sell_amount -= match_amount
                        buy['amount'] -= match_amount
                        
                        # Remove exhausted buy
                        if buy['amount'] <= 0:
                            buy_queue.pop(0)
        
        return completed_trades
    
    def _calculate_summary(self, completed_trades):
        """Calculate summary statistics"""
        if not completed_trades:
            return self._empty_summary()
        
        total_pnl = sum(t['pnl'] for t in completed_trades)
        winning_trades = [t for t in completed_trades if t['is_winning']]
        losing_trades = [t for t in completed_trades if not t['is_winning']]
        
        summary = {
            'total_pnl': round(total_pnl, 2),
            'total_trades': len(completed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(len(winning_trades) / len(completed_trades) * 100, 2) if completed_trades else 0,
            'average_win': round(sum(t['pnl'] for t in winning_trades) / len(winning_trades), 2) if winning_trades else 0,
            'average_loss': round(sum(t['pnl'] for t in losing_trades) / len(losing_trades), 2) if losing_trades else 0,
            'best_trade': max(completed_trades, key=lambda x: x['pnl']) if completed_trades else None,
            'worst_trade': min(completed_trades, key=lambda x: x['pnl']) if completed_trades else None,
        }
        
        return summary
    
    def _empty_summary(self):
        """Return empty summary structure"""
        return {
            'total_pnl': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'average_win': 0,
            'average_loss': 0,
            'best_trade': None,
            'worst_trade': None,
        }
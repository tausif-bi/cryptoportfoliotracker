from datetime import datetime
from utils.logger import get_logger
from strategies.technical.trendline_breakout import TrendlineBreakoutStrategy
from services.trading_service import TradingService

logger = get_logger(__name__)


class StrategyService:
    """Service class for strategy-related operations"""
    
    def __init__(self):
        self.trading_service = TradingService()
    
    def get_available_strategies(self):
        """Get list of all available strategies"""
        return [
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
    
    def get_current_signal(self, analysis_data):
        """Get current signal from analysis data"""
        current_signal = "HOLD"
        
        if 'buy_signal' in analysis_data.columns and 'sell_signal' in analysis_data.columns:
            if analysis_data['buy_signal'].iloc[-1] == 1:
                current_signal = "BUY"
            elif analysis_data['sell_signal'].iloc[-1] == 1:
                current_signal = "SELL"
            elif 'position' in analysis_data.columns:
                if analysis_data['position'].iloc[-1] == 1:
                    current_signal = "HOLD LONG"
                else:
                    current_signal = "HOLD CASH"
        elif 'signal' in analysis_data.columns:
            signal_value = analysis_data['signal'].iloc[-1]
            if signal_value == 1:
                current_signal = "BUY"
            elif signal_value == -1:
                current_signal = "SELL"
            elif 'position' in analysis_data.columns:
                if analysis_data['position'].iloc[-1] == 1:
                    current_signal = "HOLD LONG"
                elif analysis_data['position'].iloc[-1] == -1:
                    current_signal = "HOLD SHORT"
        
        return current_signal
    
    def calculate_strategy_metrics(self, analysis_data):
        """Calculate metrics from strategy analysis data"""
        metrics = {
            'total_buy_signals': 0,
            'total_sell_signals': 0
        }
        
        if 'buy_signal' in analysis_data.columns:
            metrics['total_buy_signals'] = int((analysis_data['buy_signal'] == 1).sum())
        
        if 'sell_signal' in analysis_data.columns:
            metrics['total_sell_signals'] = int((analysis_data['sell_signal'] == 1).sum())
        
        if 'signal' in analysis_data.columns:
            metrics['total_buy_signals'] = int((analysis_data['signal'] == 1).sum())
            metrics['total_sell_signals'] = int((analysis_data['signal'] == -1).sum())
        
        return metrics
    
    def get_recent_signals(self, analysis_data, limit=10):
        """Get recent trading signals from analysis data"""
        recent_signals = []
        
        if 'buy_signal' in analysis_data.columns and 'sell_signal' in analysis_data.columns:
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
        return recent_signals[:limit]
    
    def extract_signals_for_overlay(self, analysis_data):
        """Extract buy/sell signals for chart overlay"""
        buy_signals = []
        sell_signals = []
        
        if 'buy_signal' in analysis_data.columns:
            buy_points = analysis_data[analysis_data['buy_signal'] == 1]
            for idx, row in buy_points.iterrows():
                buy_signals.append({
                    'timestamp': idx.isoformat(),
                    'price': row['close'],
                    'type': 'AI_BUY'
                })
        
        if 'sell_signal' in analysis_data.columns:
            sell_points = analysis_data[analysis_data['sell_signal'] == 1]
            for idx, row in sell_points.iterrows():
                sell_signals.append({
                    'timestamp': idx.isoformat(),
                    'price': row['close'],
                    'type': 'AI_SELL'
                })
        
        # Current signal
        current_signal = self.get_current_signal(analysis_data)
        
        return {
            'symbol': analysis_data.attrs.get('symbol', 'Unknown'),
            'current_signal': current_signal,
            'current_price': analysis_data['close'].iloc[-1],
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'ai_predictions': {
                'next_action': current_signal,
                'confidence': 'Medium',
                'timeframe': analysis_data.attrs.get('timeframe', '1h')
            }
        }
    
    def analyze_continuation_patterns(self, analysis_data, min_pattern_bars, trend_strength, volume_multiplier):
        """Analyze continuation patterns from data"""
        current_signal = self.get_current_signal(analysis_data)
        current_pattern = "None"
        
        if 'pattern_detected' in analysis_data.columns and analysis_data['pattern_detected'].iloc[-1] != '':
            current_pattern = analysis_data['pattern_detected'].iloc[-1]
        
        # Calculate metrics
        metrics = self.calculate_strategy_metrics(analysis_data)
        current_price = analysis_data['close'].iloc[-1]
        
        # Get recent patterns
        recent_patterns = []
        if 'pattern_detected' in analysis_data.columns:
            pattern_df = analysis_data[analysis_data['pattern_detected'] != '']
            
            for idx in pattern_df.index[-10:]:
                recent_patterns.append({
                    'timestamp': idx.isoformat(),
                    'pattern': pattern_df.loc[idx, 'pattern_detected'],
                    'signal': 'BUY' if pattern_df.loc[idx, 'signal'] == 1 else 'SELL',
                    'price': pattern_df.loc[idx, 'close'],
                    'stop_loss': pattern_df.loc[idx, 'stop_loss'] if 'stop_loss' in pattern_df.columns else None,
                    'take_profit': pattern_df.loc[idx, 'take_profit'] if 'take_profit' in pattern_df.columns else None
                })
        
        # Pattern statistics
        pattern_stats = {}
        if 'pattern_detected' in analysis_data.columns:
            pattern_counts = analysis_data['pattern_detected'].value_counts()
            for pattern, count in pattern_counts.items():
                if pattern != '':
                    pattern_stats[pattern] = int(count)
        
        return {
            'symbol': analysis_data.attrs.get('symbol', 'Unknown'),
            'timeframe': analysis_data.attrs.get('timeframe', '1h'),
            'current_signal': current_signal,
            'current_pattern': current_pattern,
            'current_price': current_price,
            'total_buy_signals': metrics['total_buy_signals'],
            'total_sell_signals': metrics['total_sell_signals'],
            'recent_patterns': recent_patterns,
            'pattern_statistics': pattern_stats,
            'strategy_info': {
                'name': 'Continuation Patterns Strategy',
                'description': 'Identifies and trades continuation patterns including triangles, flags, pennants, and rectangles'
            },
            'parameters_used': {
                'min_pattern_bars': min_pattern_bars,
                'trend_strength': trend_strength,
                'volume_multiplier': volume_multiplier
            }
        }
    
    def compare_actual_vs_ai_trades(self, symbol='BTC/USDT', timeframe='1h'):
        """Compare actual trades with AI predictions"""
        logger.info(f"Comparing actual vs AI trades for {symbol}")
        
        # Get actual trades from P&L calculation
        actual_pnl_data = self.trading_service.calculate_pnl_from_trades()
        
        if not actual_pnl_data.get('success'):
            return {
                'success': False,
                'error': 'Could not load actual trades'
            }
        
        # Filter actual trades for the requested symbol
        actual_trades = [
            trade for trade in actual_pnl_data.get('trades', [])
            if trade.get('symbol', 'BTC/USDT') == symbol
        ]
        
        # Get AI predictions
        try:
            strategy = TrendlineBreakoutStrategy()
            ai_data = strategy.generate_signals(symbol, timeframe, 500)
        except Exception as e:
            logger.error(f"Error generating AI predictions: {e}")
            ai_data = None
        
        if ai_data is None:
            return {
                'success': False,
                'error': 'Could not generate AI predictions'
            }
        
        # Calculate AI strategy performance
        ai_trades = self._calculate_ai_trades(ai_data)
        
        # Extract signals for comparison
        ai_signals = self._extract_ai_signals(ai_data)
        actual_signals = self._extract_actual_signals(actual_trades)
        
        # Calculate comparison metrics
        comparison_result = self._calculate_comparison_metrics(
            actual_trades, ai_trades, actual_signals, ai_signals, ai_data
        )
        
        return {
            'success': True,
            'comparison': comparison_result
        }
    
    def _calculate_ai_trades(self, ai_data):
        """Calculate AI trades from signals using FIFO matching"""
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
        
        return ai_trades
    
    def _extract_ai_signals(self, ai_data):
        """Extract AI buy/sell signals"""
        buy_signals = []
        sell_signals = []
        
        buy_points = ai_data[ai_data['buy_signal'] == 1]
        for idx, row in buy_points.iterrows():
            buy_signals.append({
                'timestamp': idx.isoformat(),
                'price': float(row['close'])
            })
        
        sell_points = ai_data[ai_data['sell_signal'] == 1]
        for idx, row in sell_points.iterrows():
            sell_signals.append({
                'timestamp': idx.isoformat(),
                'price': float(row['close'])
            })
        
        return {'buy_signals': buy_signals, 'sell_signals': sell_signals}
    
    def _extract_actual_signals(self, actual_trades):
        """Extract actual buy/sell signals from trades"""
        buy_signals = []
        sell_signals = []
        
        for trade in actual_trades:
            if trade.get('buy_timestamp'):
                buy_signals.append({
                    'timestamp': datetime.fromtimestamp(trade['buy_timestamp'] / 1000).isoformat(),
                    'price': float(trade.get('buy_price', 0))
                })
            
            if trade.get('sell_timestamp'):
                sell_signals.append({
                    'timestamp': datetime.fromtimestamp(trade['sell_timestamp'] / 1000).isoformat(),
                    'price': float(trade.get('sell_price', 0))
                })
        
        return {'buy_signals': buy_signals, 'sell_signals': sell_signals}
    
    def _calculate_comparison_metrics(self, actual_trades, ai_trades, actual_signals, ai_signals, ai_data):
        """Calculate comparison metrics between actual and AI trading"""
        # Actual trading metrics
        total_actual_trades = len(actual_trades)
        actual_profit = sum(trade.get('pnl', 0) for trade in actual_trades)
        actual_winning_trades = [t for t in actual_trades if t.get('pnl', 0) > 0]
        actual_win_rate = len(actual_winning_trades) / max(total_actual_trades, 1) * 100
        
        # AI trading metrics
        ai_total_trades = len(ai_trades)
        ai_winning_trades = len([t for t in ai_trades if t['is_winning']])
        ai_losing_trades = ai_total_trades - ai_winning_trades
        ai_win_rate = float(ai_winning_trades / max(ai_total_trades, 1) * 100)
        ai_total_pnl = float(sum(t['pnl'] for t in ai_trades))
        
        # Signal frequency
        total_ai_signals = len(ai_signals['buy_signals']) + len(ai_signals['sell_signals'])
        signal_frequency_ratio = float(total_ai_signals / max(total_actual_trades, 1))
        
        # Performance comparison
        performance_comparison = "Similar"
        if ai_win_rate > actual_win_rate + 5:
            performance_comparison = "AI performs better"
        elif actual_win_rate > ai_win_rate + 5:
            performance_comparison = "Your trading performs better"
        
        # Current AI recommendation
        current_ai_recommendation = 0
        if not ai_data.empty:
            current_ai_recommendation = int(ai_data['buy_signal'].iloc[-1])
        
        # Analysis period
        analysis_period = {
            'start': ai_data.index[0].isoformat() if not ai_data.empty else None,
            'end': ai_data.index[-1].isoformat() if not ai_data.empty else None
        }
        
        return {
            'symbol': ai_data.attrs.get('symbol', 'BTC/USDT'),
            'timeframe': ai_data.attrs.get('timeframe', '1h'),
            'actual_trading': {
                'total_trades': int(total_actual_trades),
                'total_pnl': float(actual_profit),
                'win_rate': float(actual_win_rate),
                'winning_trades': len(actual_winning_trades),
                'losing_trades': total_actual_trades - len(actual_winning_trades),
                'buy_signals': actual_signals['buy_signals'],
                'sell_signals': actual_signals['sell_signals']
            },
            'ai_predictions': {
                'total_signals': int(total_ai_signals),
                'total_trades': int(ai_total_trades),
                'total_pnl': ai_total_pnl,
                'win_rate': ai_win_rate,
                'winning_trades': int(ai_winning_trades),
                'losing_trades': int(ai_losing_trades),
                'buy_signals': ai_signals['buy_signals'],
                'sell_signals': ai_signals['sell_signals'],
                'current_recommendation': int(current_ai_recommendation),
                'completed_trades': ai_trades
            },
            'metrics': {
                'signal_frequency_ratio': signal_frequency_ratio,
                'actual_win_rate': float(actual_win_rate),
                'ai_win_rate': ai_win_rate,
                'performance_comparison': performance_comparison,
                'analysis_period': analysis_period
            }
        }
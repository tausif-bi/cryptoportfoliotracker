from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from utils.auth import auth_required
from utils.security import get_limiter, require_valid_request
from utils.exceptions import handle_exceptions
from utils.logger import get_logger
from services.trading_service import TradingService
from services.strategy_service import StrategyService
from strategies.technical.trendline_breakout import TrendlineBreakoutStrategy
from strategies.technical.continuation_patterns import ContinuationPatternsStrategy
from strategies.technical.rsi_strategy import RSIStrategy, run_rsi_analysis
from strategies.technical.ma_crossover_strategy import MovingAverageCrossoverStrategy, run_ma_crossover_analysis
from strategies.technical.bollinger_bands_strategy import BollingerBandsStrategy, run_bollinger_bands_analysis
from strategies.technical.volume_spike_strategy import VolumeSpikeStrategy, run_volume_spike_analysis
from strategies.technical.reversal_patterns_strategy import ReversalPatternsStrategy, run_reversal_patterns_analysis

logger = get_logger(__name__)
trading_bp = Blueprint('trading', __name__, url_prefix='/api')
limiter = get_limiter()

# Initialize services
trading_service = TradingService()
strategy_service = StrategyService()

@trading_bp.route('/pnl/summary', methods=['GET'])
@handle_exceptions(logger)
def get_pnl_summary():
    """Get P&L summary with all completed trades"""
    try:
        result = trading_service.calculate_pnl_from_trades()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_pnl_summary: {str(e)}")
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

@trading_bp.route('/pnl/daily', methods=['GET'])
@handle_exceptions(logger)
def get_daily_pnl():
    """Get P&L grouped by day"""
    try:
        result = trading_service.calculate_pnl_from_trades()
        
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
        logger.error(f"Error in get_daily_pnl: {str(e)}")
        return jsonify({
            'success': True,
            'daily_pnl': [],
            'total_days': 0
        })

@trading_bp.route('/strategies/list', methods=['GET'])
@handle_exceptions(logger)
def get_available_strategies():
    """Get list of all available strategies - no auth required"""
    try:
        strategies = strategy_service.get_available_strategies()
        
        return jsonify({
            'success': True,
            'strategies': strategies
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/strategies/trendline_breakout/analyze', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
def analyze_trendline_breakout():
    """Run trendline breakout strategy analysis"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 500)
        trendline_lookback = data.get('trendline_lookback', 30)
        rolling_window_order = data.get('rolling_window_order', 4)
        
        logger.info(f"Running trendline breakout analysis for {symbol}")
        
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
        current_signal = strategy_service.get_current_signal(analysis_data)
        metrics = strategy_service.calculate_strategy_metrics(analysis_data)
        
        # Get recent signals
        recent_signals = strategy_service.get_recent_signals(analysis_data, limit=10)
        
        return jsonify({
            'success': True,
            'analysis': {
                'symbol': symbol,
                'timeframe': timeframe,
                'current_signal': current_signal,
                'current_price': analysis_data['close'].iloc[-1],
                'total_buy_signals': metrics['total_buy_signals'],
                'total_sell_signals': metrics['total_sell_signals'],
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
        logger.error(f"Error in trendline breakout analysis: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/strategies/trendline_breakout/signals', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
def get_trendline_signals_only():
    """Get only the buy/sell signals without chart"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        limit = data.get('limit', 100)
        
        # Create strategy instance with default parameters
        strategy = TrendlineBreakoutStrategy()
        
        # Generate signals
        analysis_data = strategy.generate_signals(symbol, timeframe, limit)
        
        if analysis_data is None:
            return jsonify({
                'success': False,
                'error': 'Failed to generate signals'
            }), 500
        
        # Extract signals
        signals = strategy_service.extract_signals_for_overlay(analysis_data)
        
        return jsonify({
            'success': True,
            'signals': signals
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/strategies/continuation_patterns/analyze', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
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
        
        logger.info(f"Running continuation patterns analysis for {symbol}")
        
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
        
        # Get analysis results
        analysis_results = strategy_service.analyze_continuation_patterns(
            analysis_data,
            min_pattern_bars,
            trend_strength,
            volume_multiplier
        )
        
        return jsonify({
            'success': True,
            'analysis': analysis_results,
            'chart_base64': chart_base64,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error in continuation patterns analysis: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/strategies/compare', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
def compare_actual_vs_ai():
    """Compare actual trades from JSON with AI predictions"""
    try:
        logger.info("=== COMPARISON ENDPOINT CALLED ===")
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        
        # Use strategy service to perform comparison
        comparison_result = strategy_service.compare_actual_vs_ai_trades(
            symbol=symbol,
            timeframe=timeframe
        )
        
        return jsonify(comparison_result)
    
    except Exception as e:
        logger.error(f"❌ Error in compare_actual_vs_ai: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# RSI Strategy endpoints
@trading_bp.route('/strategies/rsi_strategy/analyze', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
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
        logger.error(f"Error in RSI analysis: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/strategies/rsi_strategy/signals', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
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
@trading_bp.route('/strategies/ma_crossover/analyze', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
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
        logger.error(f"Error in MA Crossover analysis: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/strategies/ma_crossover/signals', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
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
@trading_bp.route('/strategies/bollinger_bands/analyze', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
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
        logger.error(f"Error in Bollinger Bands analysis: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/strategies/bollinger_bands/signals', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
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
@trading_bp.route('/strategies/volume_spike/analyze', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
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
        logger.error(f"Error in Volume Spike analysis: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/strategies/volume_spike/signals', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
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
@trading_bp.route('/strategies/reversal_patterns/analyze', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
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
        logger.error(f"Error in Reversal Patterns analysis: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/strategies/reversal_patterns/signals', methods=['POST'])
@auth_required()
@handle_exceptions(logger)
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

@trading_bp.route('/trading-pairs', methods=['GET'])
@limiter.limit("30 per minute")
@require_valid_request
@handle_exceptions(logger)
def get_trading_pairs():
    """Get list of supported trading pairs"""
    try:
        # Get trading pairs from trading service
        pairs = trading_service.get_supported_trading_pairs()
        
        return jsonify({
            'success': True,
            'pairs': pairs
        })
    
    except Exception as e:
        logger.error(f"Error fetching trading pairs: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
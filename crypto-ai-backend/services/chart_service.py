"""
Chart service for generating interactive chart data instead of static images
"""
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import ccxt
from models.database import db, PriceHistory, Trade
from utils.logger import get_logger
from utils.exceptions import StrategyAnalysisError, InsufficientDataError

logger = get_logger(__name__)

class ChartDataService:
    """Service for generating chart data for interactive frontend charts"""
    
    def __init__(self):
        self.exchange = None
    
    def initialize_exchange(self, exchange_name='binance'):
        """Initialize exchange for data fetching"""
        try:
            self.exchange = getattr(ccxt, exchange_name)({
                'enableRateLimit': True,
                'sandbox': False
            })
            logger.info(f"Initialized {exchange_name} exchange for chart data")
        except Exception as e:
            logger.error(f"Failed to initialize exchange {exchange_name}: {str(e)}")
            raise StrategyAnalysisError(exchange_name, f"Exchange initialization failed: {str(e)}")
    
    def get_ohlcv_data(self, symbol: str, timeframe: str = '1h', limit: int = 500) -> Dict[str, Any]:
        """Get OHLCV data for charting"""
        try:
            # Try to get data from database first
            db_data = self._get_ohlcv_from_db(symbol, timeframe, limit)
            
            if db_data and len(db_data) >= limit * 0.8:  # Use DB data if we have 80% of requested data
                logger.info(f"Using database data for {symbol} {timeframe}")
                return self._format_ohlcv_data(db_data, symbol, timeframe, 'database')
            
            # Fallback to exchange API
            if not self.exchange:
                self.initialize_exchange()
            
            logger.info(f"Fetching OHLCV data from exchange for {symbol} {timeframe}")
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                raise InsufficientDataError(f"No OHLCV data available for {symbol}")
            
            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Store in database for future use
            self._store_ohlcv_data(df, symbol, timeframe)
            
            return self._format_ohlcv_data(df, symbol, timeframe, 'exchange')
            
        except Exception as e:
            logger.error(f"Error getting OHLCV data for {symbol}: {str(e)}")
            raise StrategyAnalysisError(symbol, f"Failed to fetch OHLCV data: {str(e)}")
    
    def _get_ohlcv_from_db(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """Get OHLCV data from database"""
        try:
            # Calculate time range based on timeframe and limit
            now = datetime.now(timezone.utc)
            
            # Convert timeframe to timedelta
            timeframe_map = {
                '1m': timedelta(minutes=1),
                '5m': timedelta(minutes=5),
                '15m': timedelta(minutes=15),
                '30m': timedelta(minutes=30),
                '1h': timedelta(hours=1),
                '2h': timedelta(hours=2),
                '4h': timedelta(hours=4),
                '6h': timedelta(hours=6),
                '12h': timedelta(hours=12),
                '1d': timedelta(days=1),
                '3d': timedelta(days=3),
                '1w': timedelta(weeks=1)
            }
            
            if timeframe not in timeframe_map:
                return None
            
            time_delta = timeframe_map[timeframe]
            start_time = now - (time_delta * limit)
            
            # Query database
            records = PriceHistory.query.filter(
                PriceHistory.symbol == symbol,
                PriceHistory.timeframe == timeframe,
                PriceHistory.timestamp >= start_time
            ).order_by(PriceHistory.timestamp.asc()).all()
            
            if not records:
                return None
            
            # Convert to DataFrame
            data = []
            for record in records:
                data.append({
                    'timestamp': int(record.timestamp.timestamp() * 1000),
                    'open': float(record.open),
                    'high': float(record.high),
                    'low': float(record.low),
                    'close': float(record.close),
                    'volume': float(record.volume),
                    'datetime': record.timestamp
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.warning(f"Error getting OHLCV from database: {str(e)}")
            return None
    
    def _store_ohlcv_data(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Store OHLCV data in database"""
        try:
            for _, row in df.iterrows():
                # Check if record already exists
                existing = PriceHistory.query.filter_by(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=row['datetime']
                ).first()
                
                if not existing:
                    record = PriceHistory(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=row['datetime'],
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume']
                    )
                    db.session.add(record)
            
            db.session.commit()
            logger.debug(f"Stored {len(df)} OHLCV records for {symbol} {timeframe}")
            
        except Exception as e:
            logger.warning(f"Failed to store OHLCV data: {str(e)}")
            db.session.rollback()
    
    def _format_ohlcv_data(self, df: pd.DataFrame, symbol: str, timeframe: str, source: str) -> Dict[str, Any]:
        """Format OHLCV data for frontend charts"""
        # Convert DataFrame to list of dictionaries
        candlestick_data = []
        volume_data = []
        
        for _, row in df.iterrows():
            timestamp = int(row['timestamp'])
            
            candlestick_data.append({
                'x': timestamp,
                'o': float(row['open']),
                'h': float(row['high']),
                'l': float(row['low']),
                'c': float(row['close'])
            })
            
            volume_data.append({
                'x': timestamp,
                'y': float(row['volume'])
            })
        
        # Calculate basic statistics
        close_prices = df['close'].astype(float)
        current_price = float(close_prices.iloc[-1]) if len(close_prices) > 0 else 0
        price_change = float(close_prices.iloc[-1] - close_prices.iloc[0]) if len(close_prices) > 1 else 0
        price_change_pct = (price_change / close_prices.iloc[0] * 100) if len(close_prices) > 1 and close_prices.iloc[0] != 0 else 0
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'source': source,
            'data': {
                'candlestick': candlestick_data,
                'volume': volume_data
            },
            'statistics': {
                'current_price': current_price,
                'price_change': price_change,
                'price_change_percent': price_change_pct,
                'high_24h': float(close_prices.max()) if len(close_prices) > 0 else 0,
                'low_24h': float(close_prices.min()) if len(close_prices) > 0 else 0,
                'volume_24h': float(df['volume'].sum()) if len(df) > 0 else 0,
                'data_points': len(df)
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_strategy_chart_data(self, symbol: str, timeframe: str = '1h', limit: int = 500, 
                              strategy_name: str = 'trendline_breakout') -> Dict[str, Any]:
        """Get chart data with strategy signals overlaid"""
        try:
            # Get base OHLCV data
            chart_data = self.get_ohlcv_data(symbol, timeframe, limit)
            
            # Apply strategy analysis
            if strategy_name == 'trendline_breakout':
                signals = self._calculate_trendline_signals(chart_data['data']['candlestick'])
            else:
                signals = {'buy_signals': [], 'sell_signals': [], 'trendlines': []}
            
            # Add strategy data to chart
            chart_data['strategy'] = {
                'name': strategy_name,
                'signals': signals
            }
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Error getting strategy chart data: {str(e)}")
            raise StrategyAnalysisError(strategy_name, f"Strategy chart generation failed: {str(e)}")
    
    def _calculate_trendline_signals(self, candlestick_data: List[Dict]) -> Dict[str, List]:
        """Calculate trendline breakout signals for chart display"""
        try:
            if len(candlestick_data) < 50:
                return {'buy_signals': [], 'sell_signals': [], 'trendlines': []}
            
            # Convert to numpy arrays for calculation
            timestamps = np.array([candle['x'] for candle in candlestick_data])
            highs = np.array([candle['h'] for candle in candlestick_data])
            lows = np.array([candle['l'] for candle in candlestick_data])
            closes = np.array([candle['c'] for candle in candlestick_data])
            
            # Find local peaks and troughs for trendlines
            peaks = self._find_local_extrema(highs, order=5, find_peaks=True)
            troughs = self._find_local_extrema(lows, order=5, find_peaks=False)
            
            # Calculate trendlines
            resistance_lines = self._calculate_trendlines(timestamps, highs, peaks)
            support_lines = self._calculate_trendlines(timestamps, lows, troughs)
            
            # Find breakout signals
            buy_signals = []
            sell_signals = []
            
            # Simple breakout detection
            for i in range(20, len(closes)):
                current_price = closes[i]
                prev_price = closes[i-1]
                
                # Check for support breakout (bullish)
                for line in support_lines:
                    support_price = self._get_trendline_price(line, timestamps[i])
                    prev_support = self._get_trendline_price(line, timestamps[i-1])
                    
                    if prev_price <= prev_support and current_price > support_price:
                        buy_signals.append({
                            'x': int(timestamps[i]),
                            'y': current_price,
                            'type': 'support_breakout'
                        })
                        break
                
                # Check for resistance breakout (bearish if rejection)
                for line in resistance_lines:
                    resistance_price = self._get_trendline_price(line, timestamps[i])
                    prev_resistance = self._get_trendline_price(line, timestamps[i-1])
                    
                    if prev_price >= prev_resistance and current_price < resistance_price:
                        sell_signals.append({
                            'x': int(timestamps[i]),
                            'y': current_price,
                            'type': 'resistance_rejection'
                        })
                        break
            
            # Format trendlines for frontend
            trendlines = []
            
            for line in resistance_lines[:3]:  # Limit to 3 most recent lines
                trendlines.append({
                    'type': 'resistance',
                    'points': [
                        {'x': int(line['start_time']), 'y': line['start_price']},
                        {'x': int(line['end_time']), 'y': line['end_price']}
                    ],
                    'color': '#ff4444'
                })
            
            for line in support_lines[:3]:  # Limit to 3 most recent lines
                trendlines.append({
                    'type': 'support',
                    'points': [
                        {'x': int(line['start_time']), 'y': line['start_price']},
                        {'x': int(line['end_time']), 'y': line['end_price']}
                    ],
                    'color': '#44ff44'
                })
            
            return {
                'buy_signals': buy_signals[-20:],  # Limit to last 20 signals
                'sell_signals': sell_signals[-20:],
                'trendlines': trendlines
            }
            
        except Exception as e:
            logger.warning(f"Error calculating trendline signals: {str(e)}")
            return {'buy_signals': [], 'sell_signals': [], 'trendlines': []}
    
    def _find_local_extrema(self, data: np.ndarray, order: int = 5, find_peaks: bool = True) -> List[int]:
        """Find local peaks or troughs in price data"""
        from scipy.signal import find_peaks as scipy_find_peaks
        
        try:
            if find_peaks:
                peaks, _ = scipy_find_peaks(data, distance=order)
                return peaks.tolist()
            else:
                troughs, _ = scipy_find_peaks(-data, distance=order)
                return troughs.tolist()
        except ImportError:
            # Fallback implementation without scipy
            extrema = []
            for i in range(order, len(data) - order):
                if find_peaks:
                    if all(data[i] >= data[i-j] for j in range(1, order+1)) and \
                       all(data[i] >= data[i+j] for j in range(1, order+1)):
                        extrema.append(i)
                else:
                    if all(data[i] <= data[i-j] for j in range(1, order+1)) and \
                       all(data[i] <= data[i+j] for j in range(1, order+1)):
                        extrema.append(i)
            return extrema
    
    def _calculate_trendlines(self, timestamps: np.ndarray, prices: np.ndarray, 
                            extrema_indices: List[int]) -> List[Dict]:
        """Calculate trendlines connecting extrema points"""
        trendlines = []
        
        if len(extrema_indices) < 2:
            return trendlines
        
        # Connect recent extrema points to form trendlines
        for i in range(len(extrema_indices) - 1):
            start_idx = extrema_indices[i]
            end_idx = extrema_indices[i + 1]
            
            # Only consider recent trendlines (last 100 data points)
            if start_idx < len(timestamps) - 100:
                continue
            
            trendlines.append({
                'start_time': timestamps[start_idx],
                'start_price': prices[start_idx],
                'end_time': timestamps[end_idx],
                'end_price': prices[end_idx],
                'slope': (prices[end_idx] - prices[start_idx]) / (timestamps[end_idx] - timestamps[start_idx])
            })
        
        return trendlines[-5:]  # Return only the 5 most recent trendlines
    
    def _get_trendline_price(self, trendline: Dict, timestamp: float) -> float:
        """Calculate price at given timestamp for a trendline"""
        slope = trendline['slope']
        start_time = trendline['start_time']
        start_price = trendline['start_price']
        
        return start_price + slope * (timestamp - start_time)
    
    def get_portfolio_chart_data(self, portfolio_id: str, timeframe: str = '1d') -> Dict[str, Any]:
        """Get portfolio performance chart data"""
        try:
            # Get trades for the portfolio
            trades = Trade.query.filter_by(portfolio_id=portfolio_id).order_by(Trade.executed_at.asc()).all()
            
            if not trades:
                return {
                    'portfolio_id': portfolio_id,
                    'data': [],
                    'statistics': {
                        'total_value': 0,
                        'total_return': 0,
                        'total_return_percent': 0
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Calculate portfolio value over time
            portfolio_data = []
            running_value = 0
            initial_investment = 0
            
            for trade in trades:
                trade_value = float(trade.total_value)
                
                if trade.side == 'buy':
                    running_value += trade_value
                    initial_investment += trade_value
                else:
                    running_value -= trade_value
                
                portfolio_data.append({
                    'x': int(trade.executed_at.timestamp() * 1000),
                    'y': running_value,
                    'trade_type': trade.side,
                    'symbol': trade.symbol,
                    'amount': float(trade.quantity),
                    'price': float(trade.price)
                })
            
            # Calculate statistics
            final_value = running_value
            total_return = final_value - initial_investment
            total_return_percent = (total_return / initial_investment * 100) if initial_investment > 0 else 0
            
            return {
                'portfolio_id': portfolio_id,
                'timeframe': timeframe,
                'data': portfolio_data,
                'statistics': {
                    'initial_investment': initial_investment,
                    'current_value': final_value,
                    'total_return': total_return,
                    'total_return_percent': total_return_percent,
                    'total_trades': len(trades)
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio chart data: {str(e)}")
            raise StrategyAnalysisError('portfolio', f"Portfolio chart generation failed: {str(e)}")

# Global chart service instance
chart_service = ChartDataService()
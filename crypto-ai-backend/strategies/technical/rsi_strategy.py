# strategies/technical/rsi_strategy.py

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timedelta
import traceback
import time
import os
from io import BytesIO
import base64

# Fix matplotlib backend for Flask/threading issues
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D

class RSIStrategy:
    """
    Trendline Breakout Strategy with RSI Display
    
    This strategy uses:
    1. Trendline breakout detection (support/resistance)
    2. Rolling window analysis for local tops/bottoms
    3. Level break detection for exit signals
    4. RSI indicator displayed for reference only (no signals)
    """
    
    def __init__(self, rsi_period=14, overbought_level=70, oversold_level=30, 
                 trendline_lookback=30, rolling_window_order=4):
        self.name = "Trendline Breakout Strategy (with RSI)"
        self.rsi_period = rsi_period
        self.overbought_level = overbought_level
        self.oversold_level = oversold_level
        self.trendline_lookback = trendline_lookback
        self.rolling_window_order = rolling_window_order
        self.signals = []
        self.performance = {}
        
    def fetch_data(self, symbol='BTC/USDT', timeframe='1h', limit=500):
        """Fetch OHLCV data from exchange"""
        try:
            exchange = ccxt.binance({'enableRateLimit': True})
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv or len(ohlcv) == 0:
                print(f"No data returned for {symbol}")
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('date')
            df = df.drop('timestamp', axis=1)
            
            print(f"Successfully fetched {len(df)} candles for {symbol}")
            return df
            
        except Exception as e:
            print(f"Error fetching data: {str(e)}")
            return None
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def check_trend_line(self, support: bool, pivot: int, slope: float, y: np.array):
        """Compute sum of differences between line and prices"""
        if pivot < 0 or pivot >= len(y):
            return -1.0
        
        intercept = -slope * pivot + y[pivot]
        line_vals = slope * np.arange(len(y)) + intercept
        diffs = line_vals - y
        
        if support and diffs.max() > 1e-5:
            return -1.0
        elif not support and diffs.min() < -1e-5:
            return -1.0

        err = (diffs ** 2.0).sum()
        return err

    def optimize_slope(self, support: bool, pivot: int, init_slope: float, y: np.array):
        """Optimize the slope of a trendline to minimize error"""
        if pivot < 0 or pivot >= len(y):
            return (init_slope, -init_slope * pivot + y[pivot])
        
        slope_unit = (y.max() - y.min()) / len(y) 
        opt_step = 1.0
        min_step = 0.0001
        curr_step = opt_step
        
        best_slope = init_slope
        best_err = self.check_trend_line(support, pivot, init_slope, y)
        
        if best_err < 0.0:
            return (init_slope, -init_slope * pivot + y[pivot])
            
        get_derivative = True
        derivative = None
        
        while curr_step > min_step:
            try:
                if get_derivative:
                    slope_change = best_slope + slope_unit * min_step
                    test_err = self.check_trend_line(support, pivot, slope_change, y)
                    derivative = test_err - best_err
                    
                    if test_err < 0.0:
                        slope_change = best_slope - slope_unit * min_step
                        test_err = self.check_trend_line(support, pivot, slope_change, y)
                        derivative = best_err - test_err

                    if test_err < 0.0:
                        return (best_slope, -best_slope * pivot + y[pivot])

                    get_derivative = False

                if derivative > 0.0:
                    test_slope = best_slope - slope_unit * curr_step
                else:
                    test_slope = best_slope + slope_unit * curr_step
                
                test_err = self.check_trend_line(support, pivot, test_slope, y)
                if test_err < 0 or test_err >= best_err: 
                    curr_step *= 0.5
                else:
                    best_err = test_err 
                    best_slope = test_slope
                    get_derivative = True
                    
            except Exception as e:
                return (best_slope, -best_slope * pivot + y[pivot])
        
        return (best_slope, -best_slope * pivot + y[pivot])

    def fit_trendlines_single(self, data: np.array):
        """Fit support and resistance trendlines to a price series"""
        if len(data) < 3:
            return ((0, np.mean(data)), (0, np.mean(data)))
        
        try:
            x = np.arange(len(data))
            coefs = np.polyfit(x, data, 1)
            line_points = coefs[0] * x + coefs[1]
            
            upper_pivot = (data - line_points).argmax() 
            lower_pivot = (data - line_points).argmin() 
           
            support_coefs = self.optimize_slope(True, lower_pivot, coefs[0], data)
            resist_coefs = self.optimize_slope(False, upper_pivot, coefs[0], data)

            return (support_coefs, resist_coefs)
            
        except Exception as e:
            return ((0, np.mean(data)), (0, np.mean(data)))

    def trendline_breakout(self, close: np.array, lookback: int):
        """Compute support and resistance trendlines and generate trading signals"""
        if lookback < 3:
            lookback = 3
            
        if len(close) <= lookback:
            return np.full(len(close), np.nan), np.full(len(close), np.nan), np.zeros(len(close)), np.zeros(len(close)), np.zeros(len(close))
        
        s_tl = np.full(len(close), np.nan)
        r_tl = np.full(len(close), np.nan)
        sig = np.zeros(len(close))
        prev_day_s_cross = np.zeros(len(close))
        prev_day_r_cross = np.zeros(len(close))

        for i in range(lookback, len(close)):
            try:
                window = close[i - lookback: i]
                s_coefs, r_coefs = self.fit_trendlines_single(window)
                
                s_val = s_coefs[1] + lookback * s_coefs[0]
                r_val = r_coefs[1] + lookback * r_coefs[0]

                s_tl[i] = s_val
                r_tl[i] = r_val

                if i > 0:
                    # Support trendline crossover detection
                    if close[i-1] < s_tl[i-1] and close[i] > s_tl[i]:
                        prev_day_s_cross[i] = 1
                    elif close[i-1] > s_tl[i-1] and close[i] < s_tl[i]:
                        prev_day_s_cross[i] = -1
                    
                    # Resistance trendline crossover detection
                    if close[i-1] < r_tl[i-1] and close[i] > r_tl[i]:
                        prev_day_r_cross[i] = 1
                    elif close[i-1] > r_tl[i-1] and close[i] < r_tl[i]:
                        prev_day_r_cross[i] = -1
                    
            except Exception as e:
                if i > 0:
                    s_tl[i] = s_tl[i-1]
                    r_tl[i] = r_tl[i-1]
        
        # Create signals based on crossovers
        for i in range(1, len(close)):
            if prev_day_s_cross[i] == 1 or prev_day_r_cross[i] == 1:
                sig[i] = 1
            elif prev_day_s_cross[i] == -1 or prev_day_r_cross[i] == -1:
                sig[i] = -1
            else:
                sig[i] = sig[i-1]
        
        return s_tl, r_tl, sig, prev_day_s_cross, prev_day_r_cross

    def rw_top(self, data: np.array, curr_index: int, order: int) -> bool:
        """Check if there is a local top at the current index"""
        if curr_index < order * 2 + 1 or curr_index >= len(data):
            return False

        k = curr_index - order
        if k < 0 or k >= len(data):
            return False
            
        v = data[k]
        
        top = True
        for i in range(1, order + 1):
            if k + i >= len(data) or k - i < 0:
                top = False
                break
            if data[k + i] > v or data[k - i] > v:
                top = False
                break
        
        return top

    def rw_bottom(self, data: np.array, curr_index: int, order: int) -> bool:
        """Check if there is a local bottom at the current index"""
        if curr_index < order * 2 + 1 or curr_index >= len(data):
            return False

        k = curr_index - order
        if k < 0 or k >= len(data):
            return False
            
        v = data[k]
        
        bottom = True
        for i in range(1, order + 1):
            if k + i >= len(data) or k - i < 0:
                bottom = False
                break
            if data[k + i] < v or data[k - i] < v:
                bottom = False
                break
        
        return bottom

    def rw_extremes(self, data: np.array, order: int):
        """Find local tops and bottoms using the rolling window method"""
        if len(data) < order * 2 + 2:
            return [], []
        
        tops = []
        bottoms = []
        
        for i in range(len(data)):
            try:
                if self.rw_top(data, i, order):
                    extreme_index = i - order
                    if extreme_index >= 0 and extreme_index < len(data):
                        top = [i, extreme_index, data[extreme_index]]
                        tops.append(top)
                
                if self.rw_bottom(data, i, order):
                    extreme_index = i - order
                    if extreme_index >= 0 and extreme_index < len(data):
                        bottom = [i, extreme_index, data[extreme_index]]
                        bottoms.append(bottom)
            
            except Exception as e:
                continue
        
        return tops, bottoms

    def detect_local_level_breaks(self, data, tops, bottoms):
        """Detect when price crosses below previous local tops or bottoms"""
        level_signals = np.zeros(len(data))
        
        if len(data) < 2:
            return level_signals
            
        if len(tops) <= 1 and len(bottoms) <= 1:
            return level_signals
        
        # Find the most recent top and bottom
        most_recent_top_idx = -1
        most_recent_bottom_idx = -1
        
        if len(tops) > 0:
            most_recent_top_idx = max(tops, key=lambda x: x[1])[1]
        
        if len(bottoms) > 0:
            most_recent_bottom_idx = max(bottoms, key=lambda x: x[1])[1]
        
        # Create lists of valid levels (excluding most recent)
        top_levels = []
        for top in tops:
            if top[1] < len(data) and top[1] != most_recent_top_idx:
                top_levels.append((top[1], top[2]))
        
        bottom_levels = []
        for bottom in bottoms:
            if bottom[1] < len(data) and bottom[1] != most_recent_bottom_idx:
                bottom_levels.append((bottom[1], bottom[2]))
        
        # Check for crosses at each candle
        for i in range(1, len(data)):
            try:
                current_price = data[i]
                previous_price = data[i-1]
                
                # Check for crossing below local tops
                for idx, level in top_levels:
                    if previous_price >= level and current_price < level:
                        level_signals[i] = -1
                        break
                
                # Check for crossing below local bottoms
                if level_signals[i] == 0:
                    for idx, level in bottom_levels:
                        if previous_price >= level and current_price < level:
                            level_signals[i] = -1
                            break
                            
            except Exception as e:
                continue
        
        return level_signals
    
    def generate_signals(self, symbol='BTC/USDT', timeframe='1h', limit=500):
        """Generate Trendline Breakout trading signals"""
        try:
            print(f"Analyzing {symbol} with Trendline Breakout Strategy...")
            
            df = self.fetch_data(symbol, timeframe, limit)
            if df is None or len(df) == 0:
                return None
            
            # Calculate RSI
            df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
            
            # Run trendline breakout analysis
            support, resist, signal, s_cross, r_cross = self.trendline_breakout(
                df['close'].to_numpy(), self.trendline_lookback
            )
            
            df['trendline_support'] = support
            df['trendline_resist'] = resist
            df['support_cross'] = s_cross
            df['resist_cross'] = r_cross
            
            # Run rolling window analysis
            tops, bottoms = self.rw_extremes(df['close'].to_numpy(), self.rolling_window_order)
            
            # Detect local level breaks
            level_breaks = self.detect_local_level_breaks(df['close'].to_numpy(), tops, bottoms)
            df['level_breaks'] = level_breaks
            
            # Initialize signal columns
            df['buy_signal'] = 0
            df['sell_signal'] = 0
            df['position'] = 0
            
            # Generate signals based on trendline breakouts only
            current_position = 0
            last_signal_index = 0  # Track last signal to avoid too frequent trades
            min_candles_between_signals = 3  # Minimum candles between signals
            
            for i in range(1, len(df)):
                # Carry forward previous position state
                df.iloc[i, df.columns.get_loc('position')] = current_position
                
                # Check if enough candles have passed since last signal
                candles_since_last_signal = i - last_signal_index
                
                # Buy conditions (when not in position)
                if (current_position == 0 and
                    candles_since_last_signal >= min_candles_between_signals and
                    (df['support_cross'].iloc[i] == 1 or 
                     (df['resist_cross'].iloc[i] == 1 and df['close'].iloc[i] > df['trendline_support'].iloc[i]))):
                    df.iloc[i, df.columns.get_loc('buy_signal')] = 1
                    df.iloc[i, df.columns.get_loc('position')] = 1
                    current_position = 1
                    last_signal_index = i
                
                # Additional buy condition: Price bounces off support
                elif (current_position == 0 and 
                      candles_since_last_signal >= min_candles_between_signals and
                      i > 2 and  # Need at least 3 candles
                      pd.notna(df['trendline_support'].iloc[i]) and
                      df['low'].iloc[i-1] <= df['trendline_support'].iloc[i-1] * 1.001 and  # Previous candle touched support
                      df['close'].iloc[i] > df['trendline_support'].iloc[i]):  # Current candle closes above support
                    df.iloc[i, df.columns.get_loc('buy_signal')] = 1
                    df.iloc[i, df.columns.get_loc('position')] = 1
                    current_position = 1
                    last_signal_index = i
                
                # Sell conditions (when in position)
                elif (current_position == 1 and
                     candles_since_last_signal >= min_candles_between_signals and
                     (df['support_cross'].iloc[i] == -1 or 
                      df['resist_cross'].iloc[i] == -1 or 
                      df['level_breaks'].iloc[i] == -1)):
                    df.iloc[i, df.columns.get_loc('sell_signal')] = 1
                    df.iloc[i, df.columns.get_loc('position')] = 0
                    current_position = 0
                    last_signal_index = i
            
            # Store additional data for chart generation
            df.attrs['tops'] = tops
            df.attrs['bottoms'] = bottoms
            df.attrs['symbol'] = symbol
            df.attrs['timeframe'] = timeframe
            
            # Calculate some performance metrics
            buy_signals = df[df['buy_signal'] == 1]
            sell_signals = df[df['sell_signal'] == 1]
            
            print(f"Total buy signals generated: {len(buy_signals)}")
            print(f"Total sell signals generated: {len(sell_signals)}")
            
            # Get current signal
            current_signal = "HOLD"
            if df['buy_signal'].iloc[-1] == 1:
                current_signal = "BUY"
            elif df['sell_signal'].iloc[-1] == 1:
                current_signal = "SELL"
            elif df['position'].iloc[-1] == 1:
                current_signal = "HOLD LONG"
            else:
                current_signal = "HOLD CASH"
            
            print(f"Current signal for {symbol}: {current_signal}")
            
            self.signals = df
            
            result = {
                'success': True,
                'symbol': symbol,
                'timeframe': timeframe,
                'current_signal': current_signal,
                'current_price': float(df.iloc[-1]['close']) if len(df) > 0 else 0,
                'current_rsi': float(df.iloc[-1]['rsi']) if len(df) > 0 and pd.notna(df.iloc[-1]['rsi']) else 0,
                'total_buy_signals': len(buy_signals),
                'total_sell_signals': len(sell_signals),
                'recent_signals': self._get_recent_signals(df),
                'analysis_data': df,
                'parameters_used': {
                    'rsi_period': self.rsi_period,
                    'overbought_level': self.overbought_level,
                    'oversold_level': self.oversold_level,
                    'trendline_lookback': self.trendline_lookback,
                    'rolling_window_order': self.rolling_window_order,
                    'timeframe': timeframe,
                    'limit': limit
                }
            }
            
            return result
            
        except Exception as e:
            print(f"Error generating RSI signals: {str(e)}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def _get_recent_signals(self, df, num_signals=10):
        """Get recent buy/sell signals"""
        signals = []
        
        # Get buy signals
        buy_signals = df[df['buy_signal'] == 1].tail(num_signals//2)
        for idx, row in buy_signals.iterrows():
            signals.append({
                'type': 'BUY',
                'timestamp': idx.isoformat(),
                'price': float(row['close']),
                'rsi': float(row['rsi']) if pd.notna(row['rsi']) else None
            })
        
        # Get sell signals
        sell_signals = df[df['sell_signal'] == 1].tail(num_signals//2)
        for idx, row in sell_signals.iterrows():
            signals.append({
                'type': 'SELL',
                'timestamp': idx.isoformat(),
                'price': float(row['close']),
                'rsi': float(row['rsi']) if pd.notna(row['rsi']) else None
            })
        
        # Sort by timestamp
        signals.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return signals[:num_signals]
    
    def create_chart(self, analysis_data, symbol='BTC/USDT'):
        """Create Trendline Breakout strategy chart with RSI indicator"""
        try:
            if analysis_data is None or len(analysis_data) == 0:
                return None
                
            df = analysis_data.copy()
            tops = df.attrs.get('tops', [])
            bottoms = df.attrs.get('bottoms', [])
            
            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), 
                                         gridspec_kw={'height_ratios': [2, 1]},
                                         facecolor='#0D0E11')
            
            # Plot 1: Price, trendlines and signals
            ax1.set_facecolor('#0D0E11')
            
            # Plot price
            ax1.plot(df.index, df['close'], color='#FFFFFF', linewidth=1.5, label='Price')
            
            # Plot trendlines
            trendlines = df[['trendline_resist', 'trendline_support']].dropna()
            if not trendlines.empty:
                ax1.plot(trendlines.index, trendlines['trendline_resist'], 
                        color='#FF6666', alpha=0.7, linestyle='-', linewidth=2, label='Resistance')
                ax1.plot(trendlines.index, trendlines['trendline_support'], 
                        color='#66FF66', alpha=0.7, linestyle='-', linewidth=2, label='Support')
            
            # Plot tops and bottoms as horizontal lines
            for top in tops:
                if top[1] < len(df.index):
                    ax1.hlines(y=top[2], xmin=df.index[top[1]], xmax=df.index[-1], 
                            colors='#FFA500', linestyles='dashed', alpha=0.5, linewidth=1)
            
            for bottom in bottoms:
                if bottom[1] < len(df.index):
                    ax1.hlines(y=bottom[2], xmin=df.index[bottom[1]], xmax=df.index[-1], 
                            colors='#9370DB', linestyles='dashed', alpha=0.5, linewidth=1)
            
            # Plot buy signals
            buy_signals = df[df['buy_signal'] == 1]
            if len(buy_signals) > 0:
                ax1.scatter(buy_signals.index, buy_signals['close'], 
                           color='#00FF88', marker='^', s=100, 
                           label=f'Buy Signals ({len(buy_signals)})', zorder=5)
            
            # Plot sell signals
            sell_signals = df[df['sell_signal'] == 1]
            if len(sell_signals) > 0:
                ax1.scatter(sell_signals.index, sell_signals['close'], 
                           color='#FF4444', marker='v', s=100, 
                           label=f'Sell Signals ({len(sell_signals)})', zorder=5)
            
            ax1.set_title(f'{symbol} - Trendline Breakout Strategy', 
                         color='#FFFFFF', fontsize=16, fontweight='bold')
            ax1.set_ylabel('Price (USDT)', color='#FFFFFF', fontweight='bold')
            ax1.tick_params(colors='#FFFFFF')
            ax1.grid(True, alpha=0.3, color='#444444')
            ax1.legend(facecolor='#1A1A1A', edgecolor='#444444', 
                      labelcolor='#FFFFFF', framealpha=0.9, loc='upper left')
            
            # Plot 2: RSI indicator
            ax2.set_facecolor('#0D0E11')
            
            # Plot RSI line
            ax2.plot(df.index, df['rsi'], color='#00D4FF', linewidth=2, label='RSI')
            
            # Plot overbought/oversold levels
            ax2.axhline(y=self.overbought_level, color='#FF4444', linestyle='--', 
                       alpha=0.7, label=f'Overbought ({self.overbought_level})')
            ax2.axhline(y=self.oversold_level, color='#00FF88', linestyle='--', 
                       alpha=0.7, label=f'Oversold ({self.oversold_level})')
            ax2.axhline(y=50, color='#FFAA00', linestyle=':', alpha=0.5, label='Midline (50)')
            
            # Fill overbought/oversold areas
            ax2.fill_between(df.index, self.overbought_level, 100, 
                            color='#FF4444', alpha=0.1)
            ax2.fill_between(df.index, 0, self.oversold_level, 
                            color='#00FF88', alpha=0.1)
            
            ax2.set_title('RSI Indicator', color='#FFFFFF', fontsize=14, fontweight='bold')
            ax2.set_ylabel('RSI', color='#FFFFFF', fontweight='bold')
            ax2.set_xlabel('Time', color='#FFFFFF', fontweight='bold')
            ax2.set_ylim(0, 100)
            ax2.tick_params(colors='#FFFFFF')
            ax2.grid(True, alpha=0.3, color='#444444')
            ax2.legend(facecolor='#1A1A1A', edgecolor='#444444', 
                      labelcolor='#FFFFFF', framealpha=0.9)
            
            # Format x-axis
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            ax2.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, len(df)//10)))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', facecolor='#0D0E11', 
                       edgecolor='none', bbox_inches='tight', dpi=100)
            buffer.seek(0)
            
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            buffer.close()
            plt.close()
            
            return image_base64
            
        except Exception as e:
            print(f"Error creating RSI chart: {str(e)}")
            traceback.print_exc()
            if 'plt' in locals():
                plt.close()
            return None
    
    def get_chart_data(self, analysis_data, symbol='BTC/USDT'):
        """Return chart data in JSON format for interactive charts"""
        try:
            if analysis_data is None or len(analysis_data) == 0:
                return None
                
            df = analysis_data.copy()
            tops = df.attrs.get('tops', [])
            bottoms = df.attrs.get('bottoms', [])
            
            # Prepare candlestick data
            candlestick_data = []
            for idx, row in df.iterrows():
                candlestick_data.append({
                    'time': int(idx.timestamp()),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close'])
                })
            
            # Prepare trendline data
            trendline_data = []
            support_data = []
            resistance_data = []
            
            for idx, row in df.iterrows():
                timestamp = int(idx.timestamp())
                if pd.notna(row['trendline_support']):
                    support_data.append({
                        'time': timestamp,
                        'value': float(row['trendline_support'])
                    })
                if pd.notna(row['trendline_resist']):
                    resistance_data.append({
                        'time': timestamp,
                        'value': float(row['trendline_resist'])
                    })
            
            # Prepare buy/sell signals
            buy_signals = []
            sell_signals = []
            
            for idx, row in df[df['buy_signal'] == 1].iterrows():
                buy_signals.append({
                    'time': int(idx.timestamp()),
                    'position': 'belowBar',
                    'color': '#00FF88',
                    'shape': 'arrowUp',
                    'text': 'BUY',
                    'size': 2
                })
            
            for idx, row in df[df['sell_signal'] == 1].iterrows():
                sell_signals.append({
                    'time': int(idx.timestamp()),
                    'position': 'aboveBar',
                    'color': '#FF4444',
                    'shape': 'arrowDown',
                    'text': 'SELL',
                    'size': 2
                })
            
            # Prepare RSI data
            rsi_data = []
            for idx, row in df.iterrows():
                if pd.notna(row['rsi']):
                    rsi_data.append({
                        'time': int(idx.timestamp()),
                        'value': float(row['rsi'])
                    })
            
            # Prepare horizontal levels (tops and bottoms)
            horizontal_levels = []
            for top in tops:
                if top[1] < len(df):
                    horizontal_levels.append({
                        'price': float(top[2]),
                        'color': '#FFA500',
                        'lineWidth': 1,
                        'lineStyle': 2,  # Dashed
                        'title': 'Resistance'
                    })
            
            for bottom in bottoms:
                if bottom[1] < len(df):
                    horizontal_levels.append({
                        'price': float(bottom[2]),
                        'color': '#9370DB',
                        'lineWidth': 1,
                        'lineStyle': 2,  # Dashed
                        'title': 'Support'
                    })
            
            return {
                'candlestickData': candlestick_data,
                'supportLine': support_data,
                'resistanceLine': resistance_data,
                'buySignals': buy_signals,
                'sellSignals': sell_signals,
                'rsiData': rsi_data,
                'horizontalLevels': horizontal_levels,
                'currentPrice': float(df.iloc[-1]['close']),
                'currentRSI': float(df.iloc[-1]['rsi']) if pd.notna(df.iloc[-1]['rsi']) else None
            }
            
        except Exception as e:
            print(f"Error creating chart data: {str(e)}")
            traceback.print_exc()
            return None
    
    def get_strategy_info(self):
        """Get strategy information"""
        return {
            'name': self.name,
            'description': 'Trendline breakout strategy with support/resistance detection and RSI display',
            'parameters': {
                'rsi_period': {
                    'description': 'Number of periods for RSI calculation',
                    'default': 14,
                    'range': '5-50'
                },
                'overbought_level': {
                    'description': 'RSI level considered overbought (sell signal)',
                    'default': 70,
                    'range': '60-90'
                },
                'oversold_level': {
                    'description': 'RSI level considered oversold (buy signal)',
                    'default': 30,
                    'range': '10-40'
                },
                'trendline_lookback': {
                    'description': 'Number of periods for trendline calculation',
                    'default': 30,
                    'range': '10-100'
                },
                'rolling_window_order': {
                    'description': 'Order for rolling window extremes detection',
                    'default': 4,
                    'range': '2-10'
                }
            },
            'category': 'technical',
            'risk_level': 'medium',
            'best_timeframes': ['1h', '4h', '1d'],
            'signals': ['BUY', 'SELL', 'HOLD LONG', 'HOLD CASH'],
            'features': [
                'Dynamic trendline support/resistance breakout',
                'Local tops/bottoms detection',
                'Level break detection for exits',
                'RSI indicator for trend reference',
                'Clear position tracking'
            ]
        }

def run_rsi_analysis(symbol='BTC/USDT', timeframe='1h', limit=500, **kwargs):
    """Standalone function to run Trendline Breakout analysis with RSI display"""
    try:
        # Extract parameters
        rsi_period = kwargs.get('rsi_period', 14)
        overbought_level = kwargs.get('overbought_level', 70)
        oversold_level = kwargs.get('oversold_level', 30)
        trendline_lookback = kwargs.get('trendline_lookback', 30)
        rolling_window_order = kwargs.get('rolling_window_order', 4)
        
        # Create strategy instance
        strategy = RSIStrategy(
            rsi_period=rsi_period,
            overbought_level=overbought_level,
            oversold_level=oversold_level,
            trendline_lookback=trendline_lookback,
            rolling_window_order=rolling_window_order
        )
        
        # Generate signals
        result = strategy.generate_signals(symbol, timeframe, limit)
        
        if result and result.get('success'):
            # Generate chart
            chart_base64 = strategy.create_chart(result['analysis_data'], symbol)
            result['chart_base64'] = chart_base64
            
            # Remove the large DataFrame from the response
            del result['analysis_data']
        
        return result
        
    except Exception as e:
        print(f"Error in RSI analysis: {str(e)}")
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
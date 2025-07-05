# strategies/technical/trendline_breakout.py

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

class TrendlineBreakoutStrategy:
    """
    Trendline Breakout Strategy with Rolling Window Analysis
    
    This strategy combines:
    1. Trendline breakout detection (support/resistance)
    2. Rolling window analysis for local tops/bottoms
    3. Position tracking with clear buy/sell signals
    """
    
    def __init__(self, trendline_lookback=30, rolling_window_order=4):
        self.name = "Trendline Breakout Strategy"
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
            
            return df
        
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
    
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
        """
        Main function to generate trading signals
        Returns: DataFrame with all analysis data and signals
        """
        try:
            print(f"Analyzing {symbol} with Trendline Breakout Strategy...")
            
            # Fetch data
            data = self.fetch_data(symbol, timeframe, limit)
            if data is None:
                return None
            
            # Run trendline breakout analysis
            support, resist, signal, s_cross, r_cross = self.trendline_breakout(
                data['close'].to_numpy(), self.trendline_lookback
            )
            
            data['trendline_support'] = support
            data['trendline_resist'] = resist
            data['support_cross'] = s_cross
            data['resist_cross'] = r_cross
            
            # Run rolling window analysis
            tops, bottoms = self.rw_extremes(data['close'].to_numpy(), self.rolling_window_order)
            
            # Detect local level breaks
            level_breaks = self.detect_local_level_breaks(data['close'].to_numpy(), tops, bottoms)
            data['level_breaks'] = level_breaks
            
            # Generate buy/sell signals and track positions
            data['position'] = 0
            data['buy_signal'] = 0
            data['sell_signal'] = 0
            
            # Process signals with position tracking
            for i in range(1, len(data)):
                # Carry forward previous position state
                data.loc[data.index[i], 'position'] = data['position'].iloc[i-1]
                
                # Buy conditions (when not in position)
                if (data['position'].iloc[i] == 0 and
                    (data['support_cross'].iloc[i] == 1 or data['resist_cross'].iloc[i] == 1)):
                    data.loc[data.index[i], 'buy_signal'] = 1
                    data.loc[data.index[i], 'position'] = 1
                
                # Sell conditions (when in position)
                elif (data['position'].iloc[i] == 1 and
                     (data['support_cross'].iloc[i] == -1 or 
                      data['resist_cross'].iloc[i] == -1 or 
                      data['level_breaks'].iloc[i] == -1)):
                    data.loc[data.index[i], 'sell_signal'] = 1
                    data.loc[data.index[i], 'position'] = 0
            
            # Store additional data for chart generation
            data.attrs['tops'] = tops
            data.attrs['bottoms'] = bottoms
            data.attrs['symbol'] = symbol
            data.attrs['timeframe'] = timeframe
            
            # Get current signal
            current_signal = "HOLD"
            if data['buy_signal'].iloc[-1] == 1:
                current_signal = "BUY"
            elif data['sell_signal'].iloc[-1] == 1:
                current_signal = "SELL"
            elif data['position'].iloc[-1] == 1:
                current_signal = "HOLD LONG"
            else:
                current_signal = "HOLD CASH"
            
            print(f"Current signal for {symbol}: {current_signal}")
            return data
            
        except Exception as e:
            print(f"Error generating signals for {symbol}: {e}")
            traceback.print_exc()
            return None

    def create_chart(self, data, save_path=None):
        """Create a chart showing the strategy analysis"""
        try:
            if data is None:
                return None
                
            symbol = data.attrs.get('symbol', 'Unknown')
            tops = data.attrs.get('tops', [])
            bottoms = data.attrs.get('bottoms', [])
            
            # Ensure we're using the non-interactive backend
            plt.ioff()  # Turn off interactive mode
            
            fig, ax = plt.subplots(figsize=(15, 8))
            
            # Plot price
            ax.plot(data.index, data['close'], linewidth=2, color='black', label='Price')
            
            # Plot trendlines
            trendlines = data[['trendline_resist', 'trendline_support']].dropna()
            if not trendlines.empty:
                ax.plot(trendlines.index, trendlines['trendline_resist'], 
                        color='red', alpha=0.7, linestyle='-', linewidth=2, label='Resistance')
                ax.plot(trendlines.index, trendlines['trendline_support'], 
                        color='green', alpha=0.7, linestyle='-', linewidth=2, label='Support')
            
            # Plot tops and bottoms as horizontal lines
            for top in tops:
                if top[1] < len(data.index):
                    ax.hlines(y=top[2], xmin=data.index[top[1]], xmax=data.index[-1], 
                            colors='orange', linestyles='dashed', alpha=0.5, linewidth=1)
            
            for bottom in bottoms:
                if bottom[1] < len(data.index):
                    ax.hlines(y=bottom[2], xmin=data.index[bottom[1]], xmax=data.index[-1], 
                            colors='purple', linestyles='dashed', alpha=0.5, linewidth=1)
            
            # Plot buy signals
            buy_points = data[data['buy_signal'] == 1]
            if not buy_points.empty:
                ax.scatter(buy_points.index, buy_points['close'], 
                          color='green', marker='^', s=100, zorder=5, label='BUY')
            
            # Plot sell signals
            sell_points = data[data['sell_signal'] == 1]
            if not sell_points.empty:
                ax.scatter(sell_points.index, sell_points['close'], 
                          color='red', marker='v', s=100, zorder=5, label='SELL')
            
            # Current signal
            current_signal = "HOLD"
            if data['buy_signal'].iloc[-1] == 1:
                current_signal = "BUY"
            elif data['sell_signal'].iloc[-1] == 1:
                current_signal = "SELL"
            elif data['position'].iloc[-1] == 1:
                current_signal = "HOLD LONG"
            
            ax.set_title(f'{symbol} - Trendline Breakout Strategy\nCurrent Signal: {current_signal}', 
                        fontsize=16, fontweight='bold')
            ax.set_ylabel('Price', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Format dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Chart saved to {save_path}")
            
            # Convert to base64 for web display
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            chart_base64 = base64.b64encode(buffer.getvalue()).decode()
            buffer.close()
            
            plt.close(fig)  # Important: close the figure to free memory
            
            return chart_base64
            
        except Exception as e:
            print(f"Error creating chart: {e}")
            traceback.print_exc()
            return None

    def get_strategy_info(self):
        """Return strategy information"""
        return {
            'name': self.name,
            'description': 'Combines trendline breakouts with rolling window analysis for local tops/bottoms',
            'parameters': {
                'trendline_lookback': self.trendline_lookback,
                'rolling_window_order': self.rolling_window_order
            },
            'signals': ['BUY', 'SELL', 'HOLD LONG', 'HOLD CASH']
        }

# Example usage function
def run_strategy_analysis(symbol='BTC/USDT', timeframe='1h', limit=500):
    """Helper function to run the strategy"""
    strategy = TrendlineBreakoutStrategy(trendline_lookback=30, rolling_window_order=4)
    data = strategy.generate_signals(symbol, timeframe, limit)
    
    if data is not None:
        # Create chart
        chart_base64 = strategy.create_chart(data)
        
        # Get current signal
        current_signal = "HOLD"
        if data['buy_signal'].iloc[-1] == 1:
            current_signal = "BUY"
        elif data['sell_signal'].iloc[-1] == 1:
            current_signal = "SELL"
        elif data['position'].iloc[-1] == 1:
            current_signal = "HOLD LONG"
        
        return {
            'symbol': symbol,
            'current_signal': current_signal,
            'current_price': data['close'].iloc[-1],
            'chart_base64': chart_base64,
            'data': data,
            'strategy_info': strategy.get_strategy_info()
        }
    
    return None
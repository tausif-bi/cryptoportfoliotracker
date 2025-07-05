"""
Continuation Patterns Trading Strategy

This strategy identifies and trades continuation patterns including:
- Triangles (Symmetrical, Ascending, Descending)
- Flags and Pennants
- Rectangles (Trading Ranges)

These patterns represent temporary pauses in a trend before continuation.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxt
from ta.trend import SMAIndicator, EMAIndicator
from ta.volatility import AverageTrueRange
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class ContinuationPatternsStrategy:
    def __init__(self, min_pattern_bars=10, trend_strength=1.5, volume_multiplier=1.3):
        """
        Initialize the Continuation Patterns Strategy
        
        Args:
            min_pattern_bars: Minimum bars to form a valid pattern
            trend_strength: Minimum trend strength before pattern (1.5 = 50% move)
            volume_multiplier: Volume increase required on breakout
        """
        self.name = "Continuation Patterns Strategy"
        self.min_pattern_bars = min_pattern_bars
        self.trend_strength = trend_strength
        self.volume_multiplier = volume_multiplier
        
    def fetch_data(self, symbol, timeframe='1h', limit=500):
        """Fetch OHLCV data from exchange"""
        try:
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
    
    def identify_trend(self, df, lookback=50):
        """Identify the prevailing trend before pattern formation"""
        df['sma20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
        df['sma50'] = SMAIndicator(close=df['close'], window=50).sma_indicator()
        df['ema20'] = EMAIndicator(close=df['close'], window=20).ema_indicator()
        
        # Calculate trend strength
        df['trend_strength'] = 0.0
        
        for i in range(lookback, len(df)):
            # Look back to find trend
            recent_prices = df['close'].iloc[i-lookback:i]
            
            # Linear regression for trend
            x = np.arange(len(recent_prices))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, recent_prices)
            
            # Trend direction and strength
            price_change = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
            
            if slope > 0 and df['close'].iloc[i] > df['sma50'].iloc[i]:
                df.loc[df.index[i], 'trend'] = 1  # Uptrend
                df.loc[df.index[i], 'trend_strength'] = abs(price_change)
            elif slope < 0 and df['close'].iloc[i] < df['sma50'].iloc[i]:
                df.loc[df.index[i], 'trend'] = -1  # Downtrend
                df.loc[df.index[i], 'trend_strength'] = abs(price_change)
            else:
                df.loc[df.index[i], 'trend'] = 0  # No clear trend
                
        return df
    
    def identify_triangles(self, df, window=30):
        """Identify triangle patterns (symmetrical, ascending, descending)"""
        df['triangle_type'] = 'none'
        df['triangle_breakout'] = 0
        
        for i in range(window, len(df) - 5):
            # Get recent price data
            recent_highs = df['high'].iloc[i-window:i]
            recent_lows = df['low'].iloc[i-window:i]
            
            # Calculate trendlines
            x = np.arange(len(recent_highs))
            
            # Upper trendline
            upper_slope, upper_intercept, _, _, _ = stats.linregress(x, recent_highs)
            upper_line = upper_slope * x + upper_intercept
            
            # Lower trendline
            lower_slope, lower_intercept, _, _, _ = stats.linregress(x, recent_lows)
            lower_line = lower_slope * x + lower_intercept
            
            # Classify triangle type
            if abs(upper_slope) < 0.0001 and lower_slope > 0:
                # Ascending triangle (flat top, rising bottom)
                df.loc[df.index[i], 'triangle_type'] = 'ascending'
                
                # Check for breakout
                if df['close'].iloc[i] > upper_line[-1] * 1.02:
                    df.loc[df.index[i], 'triangle_breakout'] = 1
                    
            elif upper_slope < 0 and abs(lower_slope) < 0.0001:
                # Descending triangle (falling top, flat bottom)
                df.loc[df.index[i], 'triangle_type'] = 'descending'
                
                # Check for breakout
                if df['close'].iloc[i] < lower_line[-1] * 0.98:
                    df.loc[df.index[i], 'triangle_breakout'] = -1
                    
            elif abs(upper_slope + lower_slope) < 0.0002 and upper_slope < 0 and lower_slope > 0:
                # Symmetrical triangle (converging lines)
                df.loc[df.index[i], 'triangle_type'] = 'symmetrical'
                
                # Check for breakout based on trend
                if df['trend'].iloc[i] == 1 and df['close'].iloc[i] > upper_line[-1]:
                    df.loc[df.index[i], 'triangle_breakout'] = 1
                elif df['trend'].iloc[i] == -1 and df['close'].iloc[i] < lower_line[-1]:
                    df.loc[df.index[i], 'triangle_breakout'] = -1
                    
        return df
    
    def identify_flags_pennants(self, df, flagpole_min=5):
        """Identify flag and pennant patterns"""
        df['flag_pattern'] = 'none'
        df['flag_breakout'] = 0
        
        for i in range(flagpole_min + 10, len(df) - 5):
            # Look for flagpole (sharp move)
            flagpole_start = i - flagpole_min - 10
            flagpole_end = i - 10
            
            price_move = (df['close'].iloc[flagpole_end] - df['close'].iloc[flagpole_start]) / df['close'].iloc[flagpole_start]
            
            # Check if there was a sharp move (flagpole)
            if abs(price_move) > 0.1:  # 10% move
                # Analyze consolidation after flagpole
                consolidation = df.iloc[flagpole_end:i]
                
                # Calculate consolidation characteristics
                high_range = consolidation['high'].max() - consolidation['high'].min()
                low_range = consolidation['low'].max() - consolidation['low'].min()
                avg_range = (high_range + low_range) / 2
                
                # Flag: rectangular consolidation
                if avg_range < abs(price_move) * 0.3:  # Tight consolidation
                    if price_move > 0:  # Bull flag
                        df.loc[df.index[i], 'flag_pattern'] = 'bull_flag'
                        if df['close'].iloc[i] > consolidation['high'].max():
                            df.loc[df.index[i], 'flag_breakout'] = 1
                    else:  # Bear flag
                        df.loc[df.index[i], 'flag_pattern'] = 'bear_flag'
                        if df['close'].iloc[i] < consolidation['low'].min():
                            df.loc[df.index[i], 'flag_breakout'] = -1
                            
        return df
    
    def identify_rectangles(self, df, window=20, tolerance=0.02):
        """Identify rectangle (trading range) patterns"""
        df['rectangle_pattern'] = False
        df['rectangle_breakout'] = 0
        
        for i in range(window, len(df) - 5):
            recent_highs = df['high'].iloc[i-window:i]
            recent_lows = df['low'].iloc[i-window:i]
            
            # Check if highs and lows are relatively flat
            high_std = recent_highs.std() / recent_highs.mean()
            low_std = recent_lows.std() / recent_lows.mean()
            
            if high_std < tolerance and low_std < tolerance:
                df.loc[df.index[i], 'rectangle_pattern'] = True
                
                # Check for breakout
                resistance = recent_highs.mean()
                support = recent_lows.mean()
                
                if df['close'].iloc[i] > resistance * 1.02:
                    df.loc[df.index[i], 'rectangle_breakout'] = 1
                elif df['close'].iloc[i] < support * 0.98:
                    df.loc[df.index[i], 'rectangle_breakout'] = -1
                    
        return df
    
    def calculate_measured_move(self, df, pattern_type, breakout_index):
        """Calculate price target using measured move concept"""
        if pattern_type in ['bull_flag', 'bear_flag']:
            # Find flagpole height
            lookback = 20
            start_idx = max(0, breakout_index - lookback)
            
            prices = df['close'].iloc[start_idx:breakout_index]
            flagpole_height = prices.max() - prices.min()
            
            if df['flag_breakout'].iloc[breakout_index] == 1:
                target = df['close'].iloc[breakout_index] + flagpole_height
            else:
                target = df['close'].iloc[breakout_index] - flagpole_height
                
        elif 'triangle' in pattern_type:
            # Triangle height at widest point
            lookback = 30
            start_idx = max(0, breakout_index - lookback)
            
            highs = df['high'].iloc[start_idx:breakout_index]
            lows = df['low'].iloc[start_idx:breakout_index]
            triangle_height = highs.max() - lows.min()
            
            if df['triangle_breakout'].iloc[breakout_index] == 1:
                target = df['close'].iloc[breakout_index] + triangle_height
            else:
                target = df['close'].iloc[breakout_index] - triangle_height
                
        else:  # Rectangle
            lookback = 20
            start_idx = max(0, breakout_index - lookback)
            
            range_height = df['high'].iloc[start_idx:breakout_index].mean() - df['low'].iloc[start_idx:breakout_index].mean()
            
            if df['rectangle_breakout'].iloc[breakout_index] == 1:
                target = df['close'].iloc[breakout_index] + range_height
            else:
                target = df['close'].iloc[breakout_index] - range_height
                
        return target
    
    def generate_signals(self, symbol='BTC/USDT', timeframe='1h', limit=500):
        """Generate trading signals based on continuation patterns"""
        # Fetch and prepare data
        df = self.fetch_data(symbol, timeframe, limit)
        if df is None:
            return None
            
        # Identify trend
        df = self.identify_trend(df)
        
        # Identify patterns
        df = self.identify_triangles(df)
        df = self.identify_flags_pennants(df)
        df = self.identify_rectangles(df)
        
        # Initialize signal columns
        df['signal'] = 0
        df['pattern_detected'] = ''
        df['stop_loss'] = 0.0
        df['take_profit'] = 0.0
        
        # Generate signals based on pattern breakouts
        for i in range(1, len(df)):
            # Skip if no clear trend
            if abs(df['trend'].iloc[i]) != 1:
                continue
                
            # Check volume confirmation
            volume_increase = df['volume'].iloc[i] / df['volume'].iloc[i-20:i].mean()
            
            # Triangle breakouts
            if df['triangle_breakout'].iloc[i] != 0 and volume_increase > self.volume_multiplier:
                if df['triangle_breakout'].iloc[i] == 1 and df['trend'].iloc[i] == 1:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'pattern_detected'] = f"{df['triangle_type'].iloc[i]}_triangle"
                    df.loc[df.index[i], 'stop_loss'] = df['low'].iloc[i-20:i].min()
                    df.loc[df.index[i], 'take_profit'] = self.calculate_measured_move(df, 'triangle', i)
                    
                elif df['triangle_breakout'].iloc[i] == -1 and df['trend'].iloc[i] == -1:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'pattern_detected'] = f"{df['triangle_type'].iloc[i]}_triangle"
                    df.loc[df.index[i], 'stop_loss'] = df['high'].iloc[i-20:i].max()
                    df.loc[df.index[i], 'take_profit'] = self.calculate_measured_move(df, 'triangle', i)
                    
            # Flag breakouts
            elif df['flag_breakout'].iloc[i] != 0 and volume_increase > self.volume_multiplier:
                if df['flag_breakout'].iloc[i] == 1:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'pattern_detected'] = df['flag_pattern'].iloc[i]
                    df.loc[df.index[i], 'stop_loss'] = df['low'].iloc[i-10:i].min()
                    df.loc[df.index[i], 'take_profit'] = self.calculate_measured_move(df, df['flag_pattern'].iloc[i], i)
                    
                elif df['flag_breakout'].iloc[i] == -1:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'pattern_detected'] = df['flag_pattern'].iloc[i]
                    df.loc[df.index[i], 'stop_loss'] = df['high'].iloc[i-10:i].max()
                    df.loc[df.index[i], 'take_profit'] = self.calculate_measured_move(df, df['flag_pattern'].iloc[i], i)
                    
            # Rectangle breakouts
            elif df['rectangle_breakout'].iloc[i] != 0 and volume_increase > self.volume_multiplier:
                if df['rectangle_breakout'].iloc[i] == 1 and df['trend'].iloc[i] == 1:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'pattern_detected'] = 'rectangle'
                    df.loc[df.index[i], 'stop_loss'] = df['low'].iloc[i-20:i].min()
                    df.loc[df.index[i], 'take_profit'] = self.calculate_measured_move(df, 'rectangle', i)
                    
                elif df['rectangle_breakout'].iloc[i] == -1 and df['trend'].iloc[i] == -1:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'pattern_detected'] = 'rectangle'
                    df.loc[df.index[i], 'stop_loss'] = df['high'].iloc[i-20:i].max()
                    df.loc[df.index[i], 'take_profit'] = self.calculate_measured_move(df, 'rectangle', i)
        
        # Add position tracking
        df['position'] = 0
        position = 0
        
        for i in range(len(df)):
            if df['signal'].iloc[i] == 1 and position <= 0:
                position = 1
            elif df['signal'].iloc[i] == -1 and position >= 0:
                position = -1
            elif position == 1:
                # Check stop loss or take profit
                if df['low'].iloc[i] <= df['stop_loss'].iloc[i] or df['high'].iloc[i] >= df['take_profit'].iloc[i]:
                    position = 0
            elif position == -1:
                # Check stop loss or take profit
                if df['high'].iloc[i] >= df['stop_loss'].iloc[i] or df['low'].iloc[i] <= df['take_profit'].iloc[i]:
                    position = 0
                    
            df.loc[df.index[i], 'position'] = position
            
        return df
    
    def create_chart(self, df):
        """Create a chart showing continuation patterns"""
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        from matplotlib.patches import Rectangle as RectPatch
        import io
        import base64
        
        plt.style.use('dark_background')
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
        
        # Price chart with patterns
        ax1.plot(df.index, df['close'], label='Close Price', color='white', linewidth=1)
        ax1.plot(df.index, df['sma20'], label='SMA 20', color='yellow', alpha=0.7)
        ax1.plot(df.index, df['sma50'], label='SMA 50', color='orange', alpha=0.7)
        
        # Highlight patterns
        for i in range(len(df)):
            if df['pattern_detected'].iloc[i] != '':
                pattern = df['pattern_detected'].iloc[i]
                color = 'green' if df['signal'].iloc[i] == 1 else 'red'
                ax1.axvline(x=df.index[i], color=color, alpha=0.3, linewidth=2)
                ax1.annotate(pattern, xy=(df.index[i], df['close'].iloc[i]),
                           xytext=(10, 10), textcoords='offset points',
                           fontsize=8, color=color,
                           bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.2))
        
        # Mark signals
        buy_signals = df[df['signal'] == 1]
        sell_signals = df[df['signal'] == -1]
        
        ax1.scatter(buy_signals.index, buy_signals['close'], color='green', marker='^', 
                   s=100, label='Buy Signal', zorder=5)
        ax1.scatter(sell_signals.index, sell_signals['close'], color='red', marker='v', 
                   s=100, label='Sell Signal', zorder=5)
        
        ax1.set_ylabel('Price (USDT)')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        ax1.set_title('Continuation Patterns Strategy')
        
        # Volume chart
        colors = ['green' if df['close'].iloc[i] > df['open'].iloc[i] else 'red' 
                 for i in range(len(df))]
        ax2.bar(df.index, df['volume'], color=colors, alpha=0.5)
        ax2.set_ylabel('Volume')
        ax2.grid(True, alpha=0.3)
        
        # Pattern indicators
        pattern_values = []
        for i in range(len(df)):
            if 'triangle' in df['triangle_type'].iloc[i]:
                pattern_values.append(3)
            elif df['flag_pattern'].iloc[i] != 'none':
                pattern_values.append(2)
            elif df['rectangle_pattern'].iloc[i]:
                pattern_values.append(1)
            else:
                pattern_values.append(0)
                
        ax3.plot(df.index, pattern_values, label='Pattern Type', color='cyan', linewidth=2)
        ax3.fill_between(df.index, 0, pattern_values, alpha=0.3, color='cyan')
        ax3.set_ylabel('Pattern')
        ax3.set_xlabel('Date')
        ax3.set_ylim(-0.5, 3.5)
        ax3.set_yticks([0, 1, 2, 3])
        ax3.set_yticklabels(['None', 'Rectangle', 'Flag/Pennant', 'Triangle'])
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        chart_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return chart_base64


# Example usage
if __name__ == "__main__":
    strategy = ContinuationPatternsStrategy()
    df = strategy.generate_signals('BTC/USDT', '1h', 500)
    
    if df is not None:
        # Count signals
        buy_signals = len(df[df['signal'] == 1])
        sell_signals = len(df[df['signal'] == -1])
        
        print(f"Total Buy Signals: {buy_signals}")
        print(f"Total Sell Signals: {sell_signals}")
        
        # Show recent patterns
        recent_patterns = df[df['pattern_detected'] != ''].tail(10)
        print("\nRecent Patterns Detected:")
        for idx, row in recent_patterns.iterrows():
            print(f"{idx}: {row['pattern_detected']} - Signal: {row['signal']}")
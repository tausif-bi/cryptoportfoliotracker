# strategies/technical/reversal_patterns_strategy.py

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timedelta
import traceback
import time
import os
from io import BytesIO
import base64
from scipy.signal import find_peaks, argrelextrema

# Fix matplotlib backend for Flask/threading issues
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D

class ReversalPatternsStrategy:
    """
    Major Reversal Patterns Strategy
    
    Based on Chapter 5 principles, this strategy identifies:
    1. Head and Shoulders (Top & Bottom)
    2. Double Tops and Double Bottoms
    3. Triple Tops and Triple Bottoms
    4. Rounding Bottoms (Saucers)
    
    Entry Rules:
    - Bearish: Enter short when price breaks below neckline on volume
    - Bullish: Enter long when price breaks above neckline on volume
    
    Risk Management:
    - Stop-loss above/below pattern extremes
    - Price targets based on pattern height measurement
    """
    
    def __init__(self, lookback_period=40, min_pattern_bars=8, volume_threshold=1.15):
        self.name = "Major Reversal Patterns Strategy"
        self.lookback_period = lookback_period
        self.min_pattern_bars = min_pattern_bars
        self.volume_threshold = volume_threshold  # Volume surge threshold for confirmation
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
    
    def identify_peaks_and_troughs(self, df, prominence=0.02):
        """Identify significant peaks and troughs in price data"""
        prices = df['close'].values
        price_range = prices.max() - prices.min()
        min_prominence = price_range * prominence
        
        # Find peaks (local maxima)
        peaks, peak_properties = find_peaks(prices, prominence=min_prominence, distance=self.min_pattern_bars)
        
        # Find troughs (local minima) by inverting the price series
        troughs, trough_properties = find_peaks(-prices, prominence=min_prominence, distance=self.min_pattern_bars)
        
        return peaks, troughs
    
    def detect_head_and_shoulders(self, df, peaks, troughs):
        """Detect Head and Shoulders Top patterns"""
        patterns = []
        
        if len(peaks) < 3 or len(troughs) < 2:
            return patterns
        
        for i in range(len(peaks) - 2):
            left_shoulder_idx = peaks[i]
            head_idx = peaks[i + 1]
            right_shoulder_idx = peaks[i + 2]
            
            left_shoulder_price = df['close'].iloc[left_shoulder_idx]
            head_price = df['close'].iloc[head_idx]
            right_shoulder_price = df['close'].iloc[right_shoulder_idx]
            
            # Head should be higher than both shoulders
            if head_price > left_shoulder_price and head_price > right_shoulder_price:
                # Shoulders should be roughly equal (within 3% tolerance)
                shoulder_diff = abs(left_shoulder_price - right_shoulder_price) / left_shoulder_price
                
                if shoulder_diff <= 0.03:
                    # Find the troughs between peaks for neckline
                    relevant_troughs = [t for t in troughs if left_shoulder_idx < t < right_shoulder_idx]
                    
                    if len(relevant_troughs) >= 1:
                        # Find the lowest trough between left shoulder and head
                        left_trough_idx = None
                        for t in troughs:
                            if left_shoulder_idx < t < head_idx:
                                left_trough_idx = t
                                break
                        
                        # Find the lowest trough between head and right shoulder
                        right_trough_idx = None
                        for t in troughs:
                            if head_idx < t < right_shoulder_idx:
                                right_trough_idx = t
                                break
                        
                        if left_trough_idx is not None and right_trough_idx is not None:
                            left_trough_price = df['close'].iloc[left_trough_idx]
                            right_trough_price = df['close'].iloc[right_trough_idx]
                            neckline_price = max(left_trough_price, right_trough_price)
                            
                            pattern = {
                                'type': 'head_and_shoulders_top',
                                'left_shoulder': {'index': left_shoulder_idx, 'price': left_shoulder_price},
                                'head': {'index': head_idx, 'price': head_price},
                                'right_shoulder': {'index': right_shoulder_idx, 'price': right_shoulder_price},
                                'neckline_price': neckline_price,
                                'pattern_height': head_price - neckline_price,
                                'target_price': neckline_price - (head_price - neckline_price),
                                'direction': 'bearish'
                            }
                            patterns.append(pattern)
        
        return patterns
    
    def detect_inverse_head_and_shoulders(self, df, peaks, troughs):
        """Detect Inverse Head and Shoulders (Bottom) patterns"""
        patterns = []
        
        if len(troughs) < 3 or len(peaks) < 2:
            return patterns
        
        for i in range(len(troughs) - 2):
            left_shoulder_idx = troughs[i]
            head_idx = troughs[i + 1]
            right_shoulder_idx = troughs[i + 2]
            
            left_shoulder_price = df['close'].iloc[left_shoulder_idx]
            head_price = df['close'].iloc[head_idx]
            right_shoulder_price = df['close'].iloc[right_shoulder_idx]
            
            # Head should be lower than both shoulders
            if head_price < left_shoulder_price and head_price < right_shoulder_price:
                # Shoulders should be roughly equal (within 3% tolerance)
                shoulder_diff = abs(left_shoulder_price - right_shoulder_price) / left_shoulder_price
                
                if shoulder_diff <= 0.03:
                    # Find the peaks between troughs for neckline
                    relevant_peaks = [p for p in peaks if left_shoulder_idx < p < right_shoulder_idx]
                    
                    if len(relevant_peaks) >= 1:
                        # Find the highest peak between left shoulder and head
                        left_peak_idx = None
                        for p in peaks:
                            if left_shoulder_idx < p < head_idx:
                                left_peak_idx = p
                                break
                        
                        # Find the highest peak between head and right shoulder
                        right_peak_idx = None
                        for p in peaks:
                            if head_idx < p < right_shoulder_idx:
                                right_peak_idx = p
                                break
                        
                        if left_peak_idx is not None and right_peak_idx is not None:
                            left_peak_price = df['close'].iloc[left_peak_idx]
                            right_peak_price = df['close'].iloc[right_peak_idx]
                            neckline_price = min(left_peak_price, right_peak_price)
                            
                            pattern = {
                                'type': 'inverse_head_and_shoulders',
                                'left_shoulder': {'index': left_shoulder_idx, 'price': left_shoulder_price},
                                'head': {'index': head_idx, 'price': head_price},
                                'right_shoulder': {'index': right_shoulder_idx, 'price': right_shoulder_price},
                                'neckline_price': neckline_price,
                                'pattern_height': neckline_price - head_price,
                                'target_price': neckline_price + (neckline_price - head_price),
                                'direction': 'bullish'
                            }
                            patterns.append(pattern)
        
        return patterns
    
    def detect_double_tops(self, df, peaks):
        """Detect Double Top patterns"""
        patterns = []
        
        if len(peaks) < 2:
            return patterns
        
        for i in range(len(peaks) - 1):
            first_peak_idx = peaks[i]
            second_peak_idx = peaks[i + 1]
            
            first_peak_price = df['close'].iloc[first_peak_idx]
            second_peak_price = df['close'].iloc[second_peak_idx]
            
            # Peaks should be roughly equal (within 2% tolerance)
            peak_diff = abs(first_peak_price - second_peak_price) / first_peak_price
            
            if peak_diff <= 0.02:
                # Find the trough between the two peaks
                trough_slice = df['close'].iloc[first_peak_idx:second_peak_idx+1]
                if len(trough_slice) > 0:
                    min_idx_relative = trough_slice.argmin()
                    trough_idx = first_peak_idx + min_idx_relative
                    trough_price = df['close'].iloc[trough_idx]
                    
                    # Ensure the trough is significantly lower than the peaks
                    if trough_price < first_peak_price * 0.97:  # At least 3% lower
                        pattern_height = max(first_peak_price, second_peak_price) - trough_price
                        
                        pattern = {
                            'type': 'double_top',
                            'first_peak': {'index': first_peak_idx, 'price': first_peak_price},
                            'second_peak': {'index': second_peak_idx, 'price': second_peak_price},
                            'trough': {'index': trough_idx, 'price': trough_price},
                            'neckline_price': trough_price,
                            'pattern_height': pattern_height,
                            'target_price': trough_price - pattern_height,
                            'direction': 'bearish'
                        }
                        patterns.append(pattern)
        
        return patterns
    
    def detect_double_bottoms(self, df, troughs):
        """Detect Double Bottom patterns"""
        patterns = []
        
        if len(troughs) < 2:
            return patterns
        
        for i in range(len(troughs) - 1):
            first_trough_idx = troughs[i]
            second_trough_idx = troughs[i + 1]
            
            first_trough_price = df['close'].iloc[first_trough_idx]
            second_trough_price = df['close'].iloc[second_trough_idx]
            
            # Troughs should be roughly equal (within 2% tolerance)
            trough_diff = abs(first_trough_price - second_trough_price) / first_trough_price
            
            if trough_diff <= 0.02:
                # Find the peak between the two troughs
                peak_slice = df['close'].iloc[first_trough_idx:second_trough_idx+1]
                if len(peak_slice) > 0:
                    max_idx_relative = peak_slice.argmax()
                    peak_idx = first_trough_idx + max_idx_relative
                    peak_price = df['close'].iloc[peak_idx]
                    
                    # Ensure the peak is significantly higher than the troughs
                    if peak_price > first_trough_price * 1.03:  # At least 3% higher
                        pattern_height = peak_price - min(first_trough_price, second_trough_price)
                        
                        pattern = {
                            'type': 'double_bottom',
                            'first_trough': {'index': first_trough_idx, 'price': first_trough_price},
                            'second_trough': {'index': second_trough_idx, 'price': second_trough_price},
                            'peak': {'index': peak_idx, 'price': peak_price},
                            'neckline_price': peak_price,
                            'pattern_height': pattern_height,
                            'target_price': peak_price + pattern_height,
                            'direction': 'bullish'
                        }
                        patterns.append(pattern)
        
        return patterns
    
    def generate_signals(self, symbol='BTC/USDT', timeframe='1h', limit=500):
        """Generate reversal pattern trading signals"""
        try:
            df = self.fetch_data(symbol, timeframe, limit)
            if df is None or len(df) == 0:
                return None
            
            # Calculate volume moving average for confirmation
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            # Identify peaks and troughs
            peaks, troughs = self.identify_peaks_and_troughs(df)
            
            # Detect all pattern types
            hs_top_patterns = self.detect_head_and_shoulders(df, peaks, troughs)
            hs_bottom_patterns = self.detect_inverse_head_and_shoulders(df, peaks, troughs)
            double_top_patterns = self.detect_double_tops(df, peaks)
            double_bottom_patterns = self.detect_double_bottoms(df, troughs)
            
            all_patterns = hs_top_patterns + hs_bottom_patterns + double_top_patterns + double_bottom_patterns
            
            # Store patterns for chart annotation
            self._current_patterns = all_patterns
            
            # Initialize signal columns
            df['buy_signal'] = 0
            df['sell_signal'] = 0
            df['position'] = 0
            df['pattern_detected'] = 0
            df['pattern_type'] = ''
            
            signals_generated = []
            pattern_signals = {}  # Track signals per pattern
            
            # Process each pattern and generate signals
            for pattern_idx, pattern in enumerate(all_patterns):
                pattern_end_idx = self.get_pattern_end_index(pattern)
                
                # Mark pattern detection
                if pattern_end_idx < len(df):
                    df.iloc[pattern_end_idx, df.columns.get_loc('pattern_detected')] = 1
                    df.iloc[pattern_end_idx, df.columns.get_loc('pattern_type')] = pattern['type']
                
                # Generate signals based on neckline breaks
                neckline_price = pattern['neckline_price']
                direction = pattern['direction']
                
                # Look for breakout after pattern completion
                for i in range(pattern_end_idx + 1, min(pattern_end_idx + 20, len(df))):  # Limit search to next 20 bars
                    current_price = df['close'].iloc[i]
                    current_volume_ratio = df['volume_ratio'].iloc[i] if pd.notna(df['volume_ratio'].iloc[i]) else 1.0
                    
                    # Check if this pattern already generated a signal
                    if pattern_idx in pattern_signals:
                        continue
                    
                    # Bearish breakout (sell signal)
                    if (direction == 'bearish' and current_price < neckline_price and 
                        current_volume_ratio >= self.volume_threshold):
                        
                        df.iloc[i, df.columns.get_loc('sell_signal')] = 1
                        pattern_signals[pattern_idx] = True
                        
                        signals_generated.append({
                            'index': i,
                            'type': 'SELL',
                            'price': current_price,
                            'pattern': pattern['type'],
                            'target': pattern['target_price'],
                            'stop_loss': self.calculate_stop_loss(pattern, 'bearish')
                        })
                        break
                    
                    # Bullish breakout (buy signal)
                    elif (direction == 'bullish' and current_price > neckline_price and 
                          current_volume_ratio >= self.volume_threshold):
                        
                        df.iloc[i, df.columns.get_loc('buy_signal')] = 1
                        pattern_signals[pattern_idx] = True
                        
                        signals_generated.append({
                            'index': i,
                            'type': 'BUY',
                            'price': current_price,
                            'pattern': pattern['type'],
                            'target': pattern['target_price'],
                            'stop_loss': self.calculate_stop_loss(pattern, 'bullish')
                        })
                        break
            
            # Update position column
            current_pos = 0
            for i in range(len(df)):
                if df.iloc[i]['buy_signal'] == 1:
                    current_pos = 1
                elif df.iloc[i]['sell_signal'] == 1:
                    current_pos = -1
                df.iloc[i, df.columns.get_loc('position')] = current_pos
            
            # Calculate performance metrics
            buy_signals = df[df['buy_signal'] == 1]
            sell_signals = df[df['sell_signal'] == 1]
            total_patterns = len(all_patterns)
            
            # Determine current signal
            current_signal = "HOLD"
            if len(df) > 0:
                last_position = df.iloc[-1]['position']
                last_price = df.iloc[-1]['close']
                
                # Check if we're near any active pattern breakout levels
                for pattern in all_patterns[-3:]:  # Check last 3 patterns
                    neckline = pattern['neckline_price']
                    direction = pattern['direction']
                    
                    if direction == 'bearish' and last_price > neckline * 0.995 and last_position == 0:
                        current_signal = "WATCH SELL"
                        break
                    elif direction == 'bullish' and last_price < neckline * 1.005 and last_position == 0:
                        current_signal = "WATCH BUY"
                        break
                
                if current_signal == "HOLD":
                    if last_position == 1:
                        current_signal = "HOLD LONG"
                    elif last_position == -1:
                        current_signal = "HOLD SHORT"
            
            self.signals = df
            
            result = {
                'success': True,
                'symbol': symbol,
                'timeframe': timeframe,
                'current_signal': current_signal,
                'current_price': float(df.iloc[-1]['close']) if len(df) > 0 else 0.0,
                'total_buy_signals': int(len(buy_signals)),
                'total_sell_signals': int(len(sell_signals)),
                'total_patterns_detected': int(total_patterns),
                'patterns_breakdown': {
                    'head_and_shoulders_top': int(len(hs_top_patterns)),
                    'inverse_head_and_shoulders': int(len(hs_bottom_patterns)),
                    'double_top': int(len(double_top_patterns)),
                    'double_bottom': int(len(double_bottom_patterns))
                },
                'recent_signals': self._get_recent_signals(df, signals_generated),
                'analysis_data': df,
                'detected_patterns': self._serialize_patterns(all_patterns),
                'parameters_used': {
                    'lookback_period': int(self.lookback_period),
                    'min_pattern_bars': int(self.min_pattern_bars),
                    'volume_threshold': float(self.volume_threshold),
                    'timeframe': timeframe,
                    'limit': int(limit)
                }
            }
            
            return result
            
        except Exception as e:
            print(f"Error generating Reversal Patterns signals: {str(e)}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def get_pattern_end_index(self, pattern):
        """Get the index where the pattern is completed"""
        if pattern['type'] in ['head_and_shoulders_top', 'inverse_head_and_shoulders']:
            return pattern['right_shoulder']['index']
        elif pattern['type'] in ['double_top', 'double_bottom']:
            if 'second_peak' in pattern:
                return pattern['second_peak']['index']
            else:
                return pattern['second_trough']['index']
        return 0
    
    def get_pattern_start_index(self, pattern):
        """Get the index where the pattern starts"""
        if pattern['type'] in ['head_and_shoulders_top', 'inverse_head_and_shoulders']:
            return pattern['left_shoulder']['index']
        elif pattern['type'] in ['double_top', 'double_bottom']:
            if 'first_peak' in pattern:
                return pattern['first_peak']['index']
            else:
                return pattern['first_trough']['index']
        return 0
    
    def calculate_stop_loss(self, pattern, direction):
        """Calculate stop-loss level based on pattern type"""
        if direction == 'bearish':
            if pattern['type'] == 'head_and_shoulders_top':
                return pattern['right_shoulder']['price'] * 1.02  # 2% above right shoulder
            elif pattern['type'] == 'double_top':
                return max(pattern['first_peak']['price'], pattern['second_peak']['price']) * 1.02
        else:  # bullish
            if pattern['type'] == 'inverse_head_and_shoulders':
                return pattern['right_shoulder']['price'] * 0.98  # 2% below right shoulder
            elif pattern['type'] == 'double_bottom':
                return min(pattern['first_trough']['price'], pattern['second_trough']['price']) * 0.98
        
        return None
    
    def _serialize_patterns(self, patterns):
        """Convert patterns to JSON-serializable format"""
        serialized = []
        for pattern in patterns:
            serialized_pattern = {}
            for key, value in pattern.items():
                if isinstance(value, dict):
                    # Handle nested dictionaries (like shoulder/peak data)
                    serialized_dict = {}
                    for k, v in value.items():
                        if hasattr(v, 'item'):  # NumPy scalar
                            serialized_dict[k] = v.item()
                        elif isinstance(v, (np.integer, np.floating)):
                            serialized_dict[k] = float(v) if isinstance(v, np.floating) else int(v)
                        else:
                            serialized_dict[k] = v
                    serialized_pattern[key] = serialized_dict
                elif hasattr(value, 'item'):  # NumPy scalar
                    serialized_pattern[key] = value.item()
                elif isinstance(value, (np.integer, np.floating)):
                    serialized_pattern[key] = float(value) if isinstance(value, np.floating) else int(value)
                else:
                    serialized_pattern[key] = value
            serialized.append(serialized_pattern)
        return serialized
    
    def _get_recent_signals(self, df, signals_generated, num_signals=10):
        """Get recent buy/sell signals with pattern information"""
        signals = []
        
        # Convert generated signals to the expected format
        for signal in signals_generated[-num_signals:]:
            try:
                price = signal.get('price', 0)
                target = signal.get('target', 0)
                stop_loss = signal.get('stop_loss')
                
                # Handle NaN values
                if pd.isna(price):
                    price = 0
                if pd.isna(target):
                    target = 0
                if stop_loss is not None and pd.isna(stop_loss):
                    stop_loss = None
                
                signals.append({
                    'type': signal.get('type', 'UNKNOWN'),
                    'timestamp': df.index[signal['index']].isoformat(),
                    'price': float(price) if price else 0.0,
                    'pattern_type': signal.get('pattern', 'unknown'),
                    'target_price': float(target) if target else 0.0,
                    'stop_loss': float(stop_loss) if stop_loss else None
                })
            except Exception as e:
                print(f"Error processing signal: {e}")
                continue
        
        # Sort by timestamp
        signals.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return signals[:num_signals]
    
    def create_chart(self, analysis_data, symbol='BTC/USDT'):
        """Create Reversal Patterns strategy chart"""
        try:
            if analysis_data is None or len(analysis_data) == 0:
                return None
                
            df = analysis_data.copy()
            
            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12), 
                                         gridspec_kw={'height_ratios': [3, 1]},
                                         facecolor='#0D0E11')
            
            # Plot 1: Price and patterns
            ax1.set_facecolor('#0D0E11')
            
            # Plot candlestick-style price line
            ax1.plot(df.index, df['close'], color='#FFFFFF', linewidth=1.5, label='Price', alpha=0.8)
            
            # Plot buy signals
            buy_signals = df[df['buy_signal'] == 1]
            if len(buy_signals) > 0:
                ax1.scatter(buy_signals.index, buy_signals['close'], 
                           color='#00FF88', marker='^', s=150, 
                           label=f'Pattern Buy Signals ({len(buy_signals)})', zorder=5)
            
            # Plot sell signals
            sell_signals = df[df['sell_signal'] == 1]
            if len(sell_signals) > 0:
                ax1.scatter(sell_signals.index, sell_signals['close'], 
                           color='#FF4444', marker='v', s=150, 
                           label=f'Pattern Sell Signals ({len(sell_signals)})', zorder=5)
            
            # Draw necklines for detected patterns
            if hasattr(self, '_current_patterns'):
                for pattern in self._current_patterns:
                    neckline_price = pattern.get('neckline_price')
                    if neckline_price:
                        pattern_start_idx = self.get_pattern_start_index(pattern)
                        pattern_end_idx = self.get_pattern_end_index(pattern)
                        
                        # Draw neckline
                        if pattern_start_idx < len(df) and pattern_end_idx < len(df):
                            start_time = df.index[pattern_start_idx]
                            end_time = df.index[min(pattern_end_idx + 10, len(df) - 1)]
                            
                            ax1.hlines(y=neckline_price, xmin=start_time, xmax=end_time,
                                     colors='#FFD700', linestyles='--', linewidth=2, alpha=0.8,
                                     label='Necklines' if pattern == self._current_patterns[0] else "")

            # Mark pattern detection points with labels
            pattern_points = df[df['pattern_detected'] == 1]
            if len(pattern_points) > 0:
                ax1.scatter(pattern_points.index, pattern_points['close'], 
                           color='#FFAA00', marker='o', s=100, 
                           label=f'Patterns Detected ({len(pattern_points)})', alpha=0.7, zorder=4)
                
                # Add pattern labels with neckline info
                for idx, row in pattern_points.iterrows():
                    pattern_type = row['pattern_type']
                    price = row['close']
                    
                    # Find the corresponding pattern data for neckline
                    pattern_data = None
                    if hasattr(self, '_current_patterns'):
                        for pattern in self._current_patterns:
                            pattern_end_idx = self.get_pattern_end_index(pattern)
                            if abs(pattern_end_idx - df.index.get_loc(idx)) <= 2:  # Close match
                                pattern_data = pattern
                                break
                    
                    # Create short labels
                    if pattern_type == 'head_and_shoulders_top':
                        label = 'H&S Bear'
                        color = '#FF4444'
                    elif pattern_type == 'inverse_head_and_shoulders':
                        label = 'H&S Bull' 
                        color = '#00FF88'
                    elif pattern_type == 'double_top':
                        label = 'DT Bear'
                        color = '#FF4444'
                    elif pattern_type == 'double_bottom':
                        label = 'DB Bull'
                        color = '#00FF88'
                    else:
                        label = 'Pattern'
                        color = '#FFAA00'
                    
                    # Add neckline info if available
                    if pattern_data:
                        neckline = pattern_data.get('neckline_price', 0)
                        full_label = f'{label}\nNL: ${neckline:.0f}'
                    else:
                        full_label = label
                    
                    # Add text annotation with better positioning
                    ax1.annotate(full_label, 
                               xy=(idx, price), 
                               xytext=(15, 25), 
                               textcoords='offset points',
                               bbox=dict(boxstyle='round,pad=0.4', facecolor=color, alpha=0.9, edgecolor='white', linewidth=1),
                               arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.15', color=color, lw=1.5),
                               fontsize=9, 
                               color='white', 
                               fontweight='bold',
                               ha='left',
                               va='bottom')
            
            ax1.set_title(f'{symbol} - Major Reversal Patterns Strategy', 
                         color='#FFFFFF', fontsize=16, fontweight='bold')
            ax1.set_ylabel('Price (USDT)', color='#FFFFFF', fontweight='bold')
            ax1.tick_params(colors='#FFFFFF')
            ax1.grid(True, alpha=0.3, color='#444444')
            ax1.legend(facecolor='#1A1A1A', edgecolor='#444444', 
                      labelcolor='#FFFFFF', framealpha=0.9)
            
            # Plot 2: Volume with pattern confirmations
            ax2.set_facecolor('#0D0E11')
            
            # Plot volume bars
            colors = ['#00FF88' if close > open_price else '#FF4444' 
                     for close, open_price in zip(df['close'], df['open'])]
            ax2.bar(df.index, df['volume'], color=colors, alpha=0.6, width=0.02)
            
            # Plot volume moving average
            ax2.plot(df.index, df['volume_ma'], color='#00D4FF', linewidth=2, 
                    label='Volume MA (20)')
            
            # Highlight volume confirmations on pattern breakouts
            volume_confirmations = df[(df['buy_signal'] == 1) | (df['sell_signal'] == 1)]
            if len(volume_confirmations) > 0:
                ax2.scatter(volume_confirmations.index, volume_confirmations['volume'], 
                           color='#FFAA00', marker='*', s=200, 
                           label='Volume Confirmation', zorder=5)
            
            ax2.set_title('Volume Analysis with Pattern Confirmations', 
                         color='#FFFFFF', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Volume', color='#FFFFFF', fontweight='bold')
            ax2.set_xlabel('Time', color='#FFFFFF', fontweight='bold')
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
            print(f"Error creating Reversal Patterns chart: {str(e)}")
            traceback.print_exc()
            if 'plt' in locals():
                plt.close()
            return None
    
    def get_strategy_info(self):
        """Get strategy information"""
        return {
            'name': self.name,
            'description': 'Major reversal patterns strategy identifying Head & Shoulders, Double Tops/Bottoms with volume confirmation',
            'parameters': {
                'lookback_period': {
                    'description': 'Number of periods to look back for pattern detection',
                    'default': 40,
                    'range': '30-100'
                },
                'min_pattern_bars': {
                    'description': 'Minimum number of bars required for pattern formation',
                    'default': 8,
                    'range': '5-20'
                },
                'volume_threshold': {
                    'description': 'Volume surge multiplier required for pattern confirmation',
                    'default': 1.15,
                    'range': '1.1-2.0'
                }
            },
            'category': 'technical',
            'risk_level': 'medium',
            'best_timeframes': ['4h', '1d', '1w']
        }

def run_reversal_patterns_analysis(symbol='BTC/USDT', timeframe='1h', limit=500, **kwargs):
    """Standalone function to run Reversal Patterns analysis"""
    try:
        # Extract parameters
        lookback_period = kwargs.get('lookback_period', 40)
        min_pattern_bars = kwargs.get('min_pattern_bars', 8)
        volume_threshold = kwargs.get('volume_threshold', 1.15)
        
        # Create strategy instance
        strategy = ReversalPatternsStrategy(
            lookback_period=lookback_period,
            min_pattern_bars=min_pattern_bars,
            volume_threshold=volume_threshold
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
        print(f"Error in Reversal Patterns analysis: {str(e)}")
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
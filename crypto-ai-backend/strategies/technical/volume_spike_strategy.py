# strategies/technical/volume_spike_strategy.py

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

class VolumeSpikeStrategy:
    """
    Volume Spike Strategy
    
    This strategy uses:
    1. Volume Moving Average to identify normal volume levels
    2. Volume spikes (volume > threshold * average volume)
    3. Price direction confirmation
    4. Buy signal: Volume spike + bullish price action
    5. Sell signal: Volume spike + bearish price action or exit conditions
    """
    
    def __init__(self, volume_period=20, spike_multiplier=2.0, price_change_threshold=0.01):
        self.name = "Volume Spike Strategy"
        self.volume_period = volume_period
        self.spike_multiplier = spike_multiplier
        self.price_change_threshold = price_change_threshold  # 1% price change threshold
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
    
    def calculate_volume_indicators(self, df):
        """Calculate volume-related indicators"""
        # Volume moving average
        df['volume_ma'] = df['volume'].rolling(window=self.volume_period).mean()
        
        # Volume ratio (current volume / average volume)
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # Volume spike detection
        df['volume_spike'] = (df['volume_ratio'] > self.spike_multiplier).astype(int)
        
        # Price change percentage
        df['price_change'] = (df['close'] - df['open']) / df['open']
        df['price_change_pct'] = df['price_change'] * 100
        
        # Bullish/Bearish volume spikes
        df['bullish_spike'] = ((df['volume_spike'] == 1) & 
                              (df['price_change'] > self.price_change_threshold)).astype(int)
        df['bearish_spike'] = ((df['volume_spike'] == 1) & 
                              (df['price_change'] < -self.price_change_threshold)).astype(int)
        
        return df
    
    def generate_signals(self, symbol='BTC/USDT', timeframe='1h', limit=500):
        """Generate Volume Spike trading signals"""
        try:
            df = self.fetch_data(symbol, timeframe, limit)
            if df is None or len(df) == 0:
                return None
            
            # Calculate volume indicators
            df = self.calculate_volume_indicators(df)
            
            # Initialize signal columns
            df['buy_signal'] = 0
            df['sell_signal'] = 0
            df['position'] = 0
            
            # Generate signals based on volume spikes and price action
            current_position = 0
            entry_price = 0
            bars_in_position = 0
            max_hold_periods = 24  # Maximum periods to hold position (24 hours for 1h timeframe)
            
            for i in range(self.volume_period, len(df)):  # Start after volume MA is available
                current_bullish_spike = df.iloc[i]['bullish_spike']
                current_bearish_spike = df.iloc[i]['bearish_spike']
                current_price = df.iloc[i]['close']
                current_volume_ratio = df.iloc[i]['volume_ratio']
                
                # Skip if volume MA is not available
                if pd.isna(df.iloc[i]['volume_ma']):
                    df.iloc[i, df.columns.get_loc('position')] = current_position
                    continue
                
                # Buy signal: Bullish volume spike
                if current_bullish_spike == 1 and current_position == 0:
                    # Additional confirmation: ensure significant volume increase
                    if current_volume_ratio >= self.spike_multiplier:
                        df.iloc[i, df.columns.get_loc('buy_signal')] = 1
                        current_position = 1
                        entry_price = current_price
                        bars_in_position = 0
                
                # Sell signal conditions for existing position
                elif current_position == 1:
                    bars_in_position += 1
                    
                    # Sell condition 1: Bearish volume spike
                    if current_bearish_spike == 1:
                        df.iloc[i, df.columns.get_loc('sell_signal')] = 1
                        current_position = 0
                        bars_in_position = 0
                    
                    # Sell condition 2: Take profit (5% gain)
                    elif current_price >= entry_price * 1.05:
                        df.iloc[i, df.columns.get_loc('sell_signal')] = 1
                        current_position = 0
                        bars_in_position = 0
                    
                    # Sell condition 3: Stop loss (3% loss)
                    elif current_price <= entry_price * 0.97:
                        df.iloc[i, df.columns.get_loc('sell_signal')] = 1
                        current_position = 0
                        bars_in_position = 0
                    
                    # Sell condition 4: Maximum hold period reached
                    elif bars_in_position >= max_hold_periods:
                        df.iloc[i, df.columns.get_loc('sell_signal')] = 1
                        current_position = 0
                        bars_in_position = 0
                
                df.iloc[i, df.columns.get_loc('position')] = current_position
            
            # Calculate some performance metrics
            buy_signals = df[df['buy_signal'] == 1]
            sell_signals = df[df['sell_signal'] == 1]
            volume_spikes = df[df['volume_spike'] == 1]
            
            # Determine current signal
            current_signal = "HOLD"
            if len(df) > 0:
                last_bullish_spike = df.iloc[-1]['bullish_spike']
                last_bearish_spike = df.iloc[-1]['bearish_spike']
                last_volume_ratio = df.iloc[-1]['volume_ratio']
                last_position = df.iloc[-1]['position']
                
                if pd.notna(last_volume_ratio):
                    if last_bullish_spike == 1 and last_position == 0:
                        current_signal = "BUY"
                    elif last_bearish_spike == 1 and last_position == 1:
                        current_signal = "SELL"
                    elif last_position == 1:
                        current_signal = "HOLD LONG"
            
            self.signals = df
            
            result = {
                'success': True,
                'symbol': symbol,
                'timeframe': timeframe,
                'current_signal': current_signal,
                'current_price': float(df.iloc[-1]['close']) if len(df) > 0 else 0,
                'current_volume': float(df.iloc[-1]['volume']) if len(df) > 0 else 0,
                'current_volume_ratio': float(df.iloc[-1]['volume_ratio']) if len(df) > 0 and pd.notna(df.iloc[-1]['volume_ratio']) else 0,
                'current_volume_ma': float(df.iloc[-1]['volume_ma']) if len(df) > 0 and pd.notna(df.iloc[-1]['volume_ma']) else 0,
                'total_buy_signals': len(buy_signals),
                'total_sell_signals': len(sell_signals),
                'total_volume_spikes': len(volume_spikes),
                'recent_signals': self._get_recent_signals(df),
                'analysis_data': df,
                'parameters_used': {
                    'volume_period': self.volume_period,
                    'spike_multiplier': self.spike_multiplier,
                    'price_change_threshold': self.price_change_threshold,
                    'timeframe': timeframe,
                    'limit': limit
                }
            }
            
            return result
            
        except Exception as e:
            print(f"Error generating Volume Spike signals: {str(e)}")
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
                'volume_ratio': float(row['volume_ratio']) if pd.notna(row['volume_ratio']) else None,
                'price_change_pct': float(row['price_change_pct']) if pd.notna(row['price_change_pct']) else None
            })
        
        # Get sell signals
        sell_signals = df[df['sell_signal'] == 1].tail(num_signals//2)
        for idx, row in sell_signals.iterrows():
            signals.append({
                'type': 'SELL',
                'timestamp': idx.isoformat(),
                'price': float(row['close']),
                'volume_ratio': float(row['volume_ratio']) if pd.notna(row['volume_ratio']) else None,
                'price_change_pct': float(row['price_change_pct']) if pd.notna(row['price_change_pct']) else None
            })
        
        # Sort by timestamp
        signals.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return signals[:num_signals]
    
    def create_chart(self, analysis_data, symbol='BTC/USDT'):
        """Create Volume Spike strategy chart"""
        try:
            if analysis_data is None or len(analysis_data) == 0:
                return None
                
            df = analysis_data.copy()
            
            # Create figure with subplots
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12), 
                                              gridspec_kw={'height_ratios': [2, 1, 1]},
                                              facecolor='#0D0E11')
            
            # Plot 1: Price and signals
            ax1.set_facecolor('#0D0E11')
            
            # Plot price
            ax1.plot(df.index, df['close'], color='#FFFFFF', linewidth=1.5, label='Price')
            
            # Plot buy signals (bullish volume spikes)
            buy_signals = df[df['buy_signal'] == 1]
            if len(buy_signals) > 0:
                ax1.scatter(buy_signals.index, buy_signals['close'], 
                           color='#00FF88', marker='^', s=120, 
                           label=f'Volume Buy Signals ({len(buy_signals)})', zorder=5)
            
            # Plot sell signals
            sell_signals = df[df['sell_signal'] == 1]
            if len(sell_signals) > 0:
                ax1.scatter(sell_signals.index, sell_signals['close'], 
                           color='#FF4444', marker='v', s=120, 
                           label=f'Volume Sell Signals ({len(sell_signals)})', zorder=5)
            
            # Highlight volume spike periods
            volume_spikes = df[df['volume_spike'] == 1]
            if len(volume_spikes) > 0:
                for idx, row in volume_spikes.iterrows():
                    ax1.axvline(x=idx, color='#FFAA00', alpha=0.3, linewidth=2)
            
            ax1.set_title(f'{symbol} - Volume Spike Strategy', 
                         color='#FFFFFF', fontsize=16, fontweight='bold')
            ax1.set_ylabel('Price (USDT)', color='#FFFFFF', fontweight='bold')
            ax1.tick_params(colors='#FFFFFF')
            ax1.grid(True, alpha=0.3, color='#444444')
            ax1.legend(facecolor='#1A1A1A', edgecolor='#444444', 
                      labelcolor='#FFFFFF', framealpha=0.9)
            
            # Plot 2: Volume and Volume MA
            ax2.set_facecolor('#0D0E11')
            
            # Plot volume bars
            colors = ['#00FF88' if change > 0 else '#FF4444' for change in df['price_change']]
            ax2.bar(df.index, df['volume'], color=colors, alpha=0.6, width=0.02)
            
            # Plot volume moving average
            ax2.plot(df.index, df['volume_ma'], color='#00D4FF', linewidth=2, 
                    label=f'Volume MA ({self.volume_period})')
            
            # Highlight volume spikes
            spike_threshold = df['volume_ma'] * self.spike_multiplier
            ax2.plot(df.index, spike_threshold, color='#FFAA00', linewidth=1, 
                    linestyle='--', label=f'Spike Threshold ({self.spike_multiplier}x)')
            
            ax2.set_title('Volume Analysis', color='#FFFFFF', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Volume', color='#FFFFFF', fontweight='bold')
            ax2.tick_params(colors='#FFFFFF')
            ax2.grid(True, alpha=0.3, color='#444444')
            ax2.legend(facecolor='#1A1A1A', edgecolor='#444444', 
                      labelcolor='#FFFFFF', framealpha=0.9)
            
            # Plot 3: Volume Ratio
            ax3.set_facecolor('#0D0E11')
            
            # Plot volume ratio
            ax3.plot(df.index, df['volume_ratio'], color='#00D4FF', linewidth=2, label='Volume Ratio')
            
            # Plot spike threshold line
            ax3.axhline(y=self.spike_multiplier, color='#FFAA00', linestyle='--', 
                       alpha=0.7, label=f'Spike Threshold ({self.spike_multiplier})')
            ax3.axhline(y=1.0, color='#FFFFFF', linestyle=':', alpha=0.5, label='Average (1.0)')
            
            # Fill spike areas
            ax3.fill_between(df.index, self.spike_multiplier, df['volume_ratio'], 
                            where=(df['volume_ratio'] > self.spike_multiplier), 
                            color='#FFAA00', alpha=0.2, interpolate=True)
            
            ax3.set_title('Volume Ratio (Current/Average)', color='#FFFFFF', fontsize=14, fontweight='bold')
            ax3.set_ylabel('Ratio', color='#FFFFFF', fontweight='bold')
            ax3.set_xlabel('Time', color='#FFFFFF', fontweight='bold')
            ax3.tick_params(colors='#FFFFFF')
            ax3.grid(True, alpha=0.3, color='#444444')
            ax3.legend(facecolor='#1A1A1A', edgecolor='#444444', 
                      labelcolor='#FFFFFF', framealpha=0.9)
            
            # Format x-axis
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            ax3.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, len(df)//10)))
            plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
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
            print(f"Error creating Volume Spike chart: {str(e)}")
            traceback.print_exc()
            if 'plt' in locals():
                plt.close()
            return None
    
    def get_strategy_info(self):
        """Get strategy information"""
        return {
            'name': self.name,
            'description': 'Volume spike strategy using unusual volume patterns with price confirmation',
            'parameters': {
                'volume_period': {
                    'description': 'Number of periods for volume moving average',
                    'default': 20,
                    'range': '10-50'
                },
                'spike_multiplier': {
                    'description': 'Multiplier for volume spike detection (volume > multiplier * average)',
                    'default': 2.0,
                    'range': '1.5-5.0'
                },
                'price_change_threshold': {
                    'description': 'Minimum price change percentage for signal confirmation',
                    'default': 0.01,
                    'range': '0.005-0.03'
                }
            },
            'category': 'technical',
            'risk_level': 'high',
            'best_timeframes': ['15m', '1h', '4h']
        }

def run_volume_spike_analysis(symbol='BTC/USDT', timeframe='1h', limit=500, **kwargs):
    """Standalone function to run Volume Spike analysis"""
    try:
        # Extract parameters
        volume_period = kwargs.get('volume_period', 20)
        spike_multiplier = kwargs.get('spike_multiplier', 2.0)
        price_change_threshold = kwargs.get('price_change_threshold', 0.01)
        
        # Create strategy instance
        strategy = VolumeSpikeStrategy(
            volume_period=volume_period,
            spike_multiplier=spike_multiplier,
            price_change_threshold=price_change_threshold
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
        print(f"Error in Volume Spike analysis: {str(e)}")
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
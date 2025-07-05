# strategies/technical/ma_crossover_strategy.py

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

class MovingAverageCrossoverStrategy:
    """
    Moving Average Crossover Strategy
    
    This strategy uses:
    1. Fast moving average (e.g., 10-period)
    2. Slow moving average (e.g., 30-period)
    3. Buy signal when fast MA crosses above slow MA
    4. Sell signal when fast MA crosses below slow MA
    """
    
    def __init__(self, fast_period=10, slow_period=30, ma_type='sma'):
        self.name = "Moving Average Crossover Strategy"
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.ma_type = ma_type  # 'sma' or 'ema'
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
    
    def calculate_moving_average(self, prices, period, ma_type='sma'):
        """Calculate moving average (SMA or EMA)"""
        if ma_type.lower() == 'ema':
            return prices.ewm(span=period).mean()
        else:  # Default to SMA
            return prices.rolling(window=period).mean()
    
    def generate_signals(self, symbol='BTC/USDT', timeframe='1h', limit=500):
        """Generate Moving Average Crossover signals"""
        try:
            df = self.fetch_data(symbol, timeframe, limit)
            if df is None or len(df) == 0:
                return None
            
            # Calculate moving averages
            df['fast_ma'] = self.calculate_moving_average(df['close'], self.fast_period, self.ma_type)
            df['slow_ma'] = self.calculate_moving_average(df['close'], self.slow_period, self.ma_type)
            
            # Initialize signal columns
            df['buy_signal'] = 0
            df['sell_signal'] = 0
            df['position'] = 0
            
            # Generate signals based on MA crossovers
            current_position = 0
            
            for i in range(1, len(df)):  # Start from 1 to compare with previous
                current_fast = df.iloc[i]['fast_ma']
                current_slow = df.iloc[i]['slow_ma']
                prev_fast = df.iloc[i-1]['fast_ma']
                prev_slow = df.iloc[i-1]['slow_ma']
                
                # Skip if any MA is NaN
                if pd.isna(current_fast) or pd.isna(current_slow) or pd.isna(prev_fast) or pd.isna(prev_slow):
                    df.iloc[i, df.columns.get_loc('position')] = current_position
                    continue
                
                # Buy signal: Fast MA crosses above Slow MA (Golden Cross)
                if (prev_fast <= prev_slow and current_fast > current_slow and current_position == 0):
                    df.iloc[i, df.columns.get_loc('buy_signal')] = 1
                    current_position = 1
                
                # Sell signal: Fast MA crosses below Slow MA (Death Cross)
                elif (prev_fast >= prev_slow and current_fast < current_slow and current_position == 1):
                    df.iloc[i, df.columns.get_loc('sell_signal')] = 1
                    current_position = 0
                
                df.iloc[i, df.columns.get_loc('position')] = current_position
            
            # Calculate some performance metrics
            buy_signals = df[df['buy_signal'] == 1]
            sell_signals = df[df['sell_signal'] == 1]
            
            # Determine current signal
            current_signal = "HOLD"
            if len(df) > 0:
                last_fast = df.iloc[-1]['fast_ma']
                last_slow = df.iloc[-1]['slow_ma']
                last_position = df.iloc[-1]['position']
                
                if pd.notna(last_fast) and pd.notna(last_slow):
                    if last_fast > last_slow and last_position == 0:
                        current_signal = "BUY"
                    elif last_fast < last_slow and last_position == 1:
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
                'current_fast_ma': float(df.iloc[-1]['fast_ma']) if len(df) > 0 and pd.notna(df.iloc[-1]['fast_ma']) else 0,
                'current_slow_ma': float(df.iloc[-1]['slow_ma']) if len(df) > 0 and pd.notna(df.iloc[-1]['slow_ma']) else 0,
                'total_buy_signals': len(buy_signals),
                'total_sell_signals': len(sell_signals),
                'recent_signals': self._get_recent_signals(df),
                'analysis_data': df,
                'parameters_used': {
                    'fast_period': self.fast_period,
                    'slow_period': self.slow_period,
                    'ma_type': self.ma_type,
                    'timeframe': timeframe,
                    'limit': limit
                }
            }
            
            return result
            
        except Exception as e:
            print(f"Error generating MA crossover signals: {str(e)}")
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
                'fast_ma': float(row['fast_ma']) if pd.notna(row['fast_ma']) else None,
                'slow_ma': float(row['slow_ma']) if pd.notna(row['slow_ma']) else None
            })
        
        # Get sell signals
        sell_signals = df[df['sell_signal'] == 1].tail(num_signals//2)
        for idx, row in sell_signals.iterrows():
            signals.append({
                'type': 'SELL',
                'timestamp': idx.isoformat(),
                'price': float(row['close']),
                'fast_ma': float(row['fast_ma']) if pd.notna(row['fast_ma']) else None,
                'slow_ma': float(row['slow_ma']) if pd.notna(row['slow_ma']) else None
            })
        
        # Sort by timestamp
        signals.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return signals[:num_signals]
    
    def create_chart(self, analysis_data, symbol='BTC/USDT'):
        """Create Moving Average Crossover strategy chart"""
        try:
            if analysis_data is None or len(analysis_data) == 0:
                return None
                
            df = analysis_data.copy()
            
            # Create figure
            fig, ax = plt.subplots(1, 1, figsize=(15, 8), facecolor='#0D0E11')
            ax.set_facecolor('#0D0E11')
            
            # Plot price
            ax.plot(df.index, df['close'], color='#FFFFFF', linewidth=1.5, label='Price', alpha=0.8)
            
            # Plot moving averages
            ma_type_label = 'EMA' if self.ma_type.lower() == 'ema' else 'SMA'
            ax.plot(df.index, df['fast_ma'], color='#00D4FF', linewidth=2, 
                   label=f'Fast {ma_type_label} ({self.fast_period})')
            ax.plot(df.index, df['slow_ma'], color='#FF9500', linewidth=2, 
                   label=f'Slow {ma_type_label} ({self.slow_period})')
            
            # Plot buy signals (Golden Cross)
            buy_signals = df[df['buy_signal'] == 1]
            if len(buy_signals) > 0:
                ax.scatter(buy_signals.index, buy_signals['close'], 
                           color='#00FF88', marker='^', s=120, 
                           label=f'Golden Cross ({len(buy_signals)})', zorder=5)
            
            # Plot sell signals (Death Cross)
            sell_signals = df[df['sell_signal'] == 1]
            if len(sell_signals) > 0:
                ax.scatter(sell_signals.index, sell_signals['close'], 
                           color='#FF4444', marker='v', s=120, 
                           label=f'Death Cross ({len(sell_signals)})', zorder=5)
            
            # Fill area between MAs to show trend
            ax.fill_between(df.index, df['fast_ma'], df['slow_ma'], 
                           where=(df['fast_ma'] > df['slow_ma']), 
                           color='#00FF88', alpha=0.1, interpolate=True, label='Bullish Trend')
            ax.fill_between(df.index, df['fast_ma'], df['slow_ma'], 
                           where=(df['fast_ma'] <= df['slow_ma']), 
                           color='#FF4444', alpha=0.1, interpolate=True, label='Bearish Trend')
            
            ax.set_title(f'{symbol} - Moving Average Crossover Strategy', 
                         color='#FFFFFF', fontsize=16, fontweight='bold')
            ax.set_ylabel('Price (USDT)', color='#FFFFFF', fontweight='bold')
            ax.set_xlabel('Time', color='#FFFFFF', fontweight='bold')
            ax.tick_params(colors='#FFFFFF')
            ax.grid(True, alpha=0.3, color='#444444')
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, len(df)//10)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Legend
            ax.legend(facecolor='#1A1A1A', edgecolor='#444444', 
                     labelcolor='#FFFFFF', framealpha=0.9, loc='upper left')
            
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
            print(f"Error creating MA crossover chart: {str(e)}")
            traceback.print_exc()
            if 'plt' in locals():
                plt.close()
            return None
    
    def get_strategy_info(self):
        """Get strategy information"""
        return {
            'name': self.name,
            'description': 'Moving Average crossover strategy using fast and slow MAs for trend following',
            'parameters': {
                'fast_period': {
                    'description': 'Period for fast moving average',
                    'default': 10,
                    'range': '5-30'
                },
                'slow_period': {
                    'description': 'Period for slow moving average',
                    'default': 30,
                    'range': '20-100'
                },
                'ma_type': {
                    'description': 'Type of moving average (SMA or EMA)',
                    'default': 'sma',
                    'options': ['sma', 'ema']
                }
            },
            'category': 'technical',
            'risk_level': 'low',
            'best_timeframes': ['1h', '4h', '1d']
        }

def run_ma_crossover_analysis(symbol='BTC/USDT', timeframe='1h', limit=500, **kwargs):
    """Standalone function to run MA Crossover analysis"""
    try:
        # Extract parameters
        fast_period = kwargs.get('fast_period', 10)
        slow_period = kwargs.get('slow_period', 30)
        ma_type = kwargs.get('ma_type', 'sma')
        
        # Create strategy instance
        strategy = MovingAverageCrossoverStrategy(
            fast_period=fast_period,
            slow_period=slow_period,
            ma_type=ma_type
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
        print(f"Error in MA Crossover analysis: {str(e)}")
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
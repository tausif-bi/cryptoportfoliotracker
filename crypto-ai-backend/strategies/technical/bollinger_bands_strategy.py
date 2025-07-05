# strategies/technical/bollinger_bands_strategy.py

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

class BollingerBandsStrategy:
    """
    Bollinger Bands Strategy
    
    This strategy uses:
    1. Middle line: Simple Moving Average (typically 20-period)
    2. Upper band: Middle line + (2 * standard deviation)
    3. Lower band: Middle line - (2 * standard deviation)
    4. Buy signal when price touches or goes below lower band
    5. Sell signal when price touches or goes above upper band
    """
    
    def __init__(self, period=20, std_dev=2.0):
        self.name = "Bollinger Bands Strategy"
        self.period = period
        self.std_dev = std_dev
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
    
    def calculate_bollinger_bands(self, prices, period=20, std_dev=2.0):
        """Calculate Bollinger Bands"""
        # Calculate middle line (SMA)
        middle = prices.rolling(window=period).mean()
        
        # Calculate standard deviation
        std = prices.rolling(window=period).std()
        
        # Calculate upper and lower bands
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        return middle, upper, lower
    
    def generate_signals(self, symbol='BTC/USDT', timeframe='1h', limit=500):
        """Generate Bollinger Bands trading signals"""
        try:
            df = self.fetch_data(symbol, timeframe, limit)
            if df is None or len(df) == 0:
                return None
            
            # Calculate Bollinger Bands
            df['bb_middle'], df['bb_upper'], df['bb_lower'] = self.calculate_bollinger_bands(
                df['close'], self.period, self.std_dev)
            
            # Calculate Band Width and %B indicator
            df['bb_width'] = ((df['bb_upper'] - df['bb_lower']) / df['bb_middle']) * 100
            df['bb_percent'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # Initialize signal columns
            df['buy_signal'] = 0
            df['sell_signal'] = 0
            df['position'] = 0
            
            # Generate signals based on Bollinger Bands
            current_position = 0
            
            for i in range(1, len(df)):  # Start from 1 to compare with previous
                current_price = df.iloc[i]['close']
                prev_price = df.iloc[i-1]['close']
                current_lower = df.iloc[i]['bb_lower']
                current_upper = df.iloc[i]['bb_upper']
                current_middle = df.iloc[i]['bb_middle']
                current_bb_percent = df.iloc[i]['bb_percent']
                
                # Skip if any band is NaN
                if pd.isna(current_lower) or pd.isna(current_upper) or pd.isna(current_middle):
                    df.iloc[i, df.columns.get_loc('position')] = current_position
                    continue
                
                # Buy signal: Price touches or goes below lower band (oversold)
                if (current_price <= current_lower and current_position == 0):
                    # Additional confirmation: %B should be close to 0 (near lower band)
                    if current_bb_percent <= 0.1:
                        df.iloc[i, df.columns.get_loc('buy_signal')] = 1
                        current_position = 1
                
                # Sell signal: Price touches or goes above upper band (overbought)
                elif (current_price >= current_upper and current_position == 1):
                    # Additional confirmation: %B should be close to 1 (near upper band)
                    if current_bb_percent >= 0.9:
                        df.iloc[i, df.columns.get_loc('sell_signal')] = 1
                        current_position = 0
                
                # Alternative sell signal: Price crosses below middle line (trend change)
                elif (current_price < current_middle and current_position == 1):
                    if prev_price >= df.iloc[i-1]['bb_middle']:
                        df.iloc[i, df.columns.get_loc('sell_signal')] = 1
                        current_position = 0
                
                df.iloc[i, df.columns.get_loc('position')] = current_position
            
            # Calculate some performance metrics
            buy_signals = df[df['buy_signal'] == 1]
            sell_signals = df[df['sell_signal'] == 1]
            
            # Determine current signal
            current_signal = "HOLD"
            if len(df) > 0:
                last_price = df.iloc[-1]['close']
                last_upper = df.iloc[-1]['bb_upper']
                last_lower = df.iloc[-1]['bb_lower']
                last_middle = df.iloc[-1]['bb_middle']
                last_bb_percent = df.iloc[-1]['bb_percent']
                last_position = df.iloc[-1]['position']
                
                if pd.notna(last_upper) and pd.notna(last_lower) and pd.notna(last_middle):
                    if last_price <= last_lower and last_position == 0:
                        current_signal = "BUY"
                    elif last_price >= last_upper and last_position == 1:
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
                'current_bb_upper': float(df.iloc[-1]['bb_upper']) if len(df) > 0 and pd.notna(df.iloc[-1]['bb_upper']) else 0,
                'current_bb_middle': float(df.iloc[-1]['bb_middle']) if len(df) > 0 and pd.notna(df.iloc[-1]['bb_middle']) else 0,
                'current_bb_lower': float(df.iloc[-1]['bb_lower']) if len(df) > 0 and pd.notna(df.iloc[-1]['bb_lower']) else 0,
                'current_bb_percent': float(df.iloc[-1]['bb_percent']) if len(df) > 0 and pd.notna(df.iloc[-1]['bb_percent']) else 0,
                'total_buy_signals': len(buy_signals),
                'total_sell_signals': len(sell_signals),
                'recent_signals': self._get_recent_signals(df),
                'analysis_data': df,
                'parameters_used': {
                    'period': self.period,
                    'std_dev': self.std_dev,
                    'timeframe': timeframe,
                    'limit': limit
                }
            }
            
            return result
            
        except Exception as e:
            print(f"Error generating Bollinger Bands signals: {str(e)}")
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
                'bb_percent': float(row['bb_percent']) if pd.notna(row['bb_percent']) else None,
                'distance_from_lower': float(row['close'] - row['bb_lower']) if pd.notna(row['bb_lower']) else None
            })
        
        # Get sell signals
        sell_signals = df[df['sell_signal'] == 1].tail(num_signals//2)
        for idx, row in sell_signals.iterrows():
            signals.append({
                'type': 'SELL',
                'timestamp': idx.isoformat(),
                'price': float(row['close']),
                'bb_percent': float(row['bb_percent']) if pd.notna(row['bb_percent']) else None,
                'distance_from_upper': float(row['bb_upper'] - row['close']) if pd.notna(row['bb_upper']) else None
            })
        
        # Sort by timestamp
        signals.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return signals[:num_signals]
    
    def create_chart(self, analysis_data, symbol='BTC/USDT'):
        """Create Bollinger Bands strategy chart"""
        try:
            if analysis_data is None or len(analysis_data) == 0:
                return None
                
            df = analysis_data.copy()
            
            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), 
                                         gridspec_kw={'height_ratios': [3, 1]},
                                         facecolor='#0D0E11')
            
            # Plot 1: Price and Bollinger Bands
            ax1.set_facecolor('#0D0E11')
            
            # Plot price
            ax1.plot(df.index, df['close'], color='#FFFFFF', linewidth=1.5, label='Price', zorder=3)
            
            # Plot Bollinger Bands
            ax1.plot(df.index, df['bb_upper'], color='#FF4444', linewidth=1, 
                    label=f'Upper Band ({self.std_dev}σ)', alpha=0.8)
            ax1.plot(df.index, df['bb_middle'], color='#00D4FF', linewidth=1.5, 
                    label=f'Middle (SMA {self.period})', alpha=0.8)
            ax1.plot(df.index, df['bb_lower'], color='#00FF88', linewidth=1, 
                    label=f'Lower Band ({self.std_dev}σ)', alpha=0.8)
            
            # Fill area between bands
            ax1.fill_between(df.index, df['bb_upper'], df['bb_lower'], 
                            color='#00D4FF', alpha=0.1, label='BB Channel')
            
            # Plot buy signals
            buy_signals = df[df['buy_signal'] == 1]
            if len(buy_signals) > 0:
                ax1.scatter(buy_signals.index, buy_signals['close'], 
                           color='#00FF88', marker='^', s=120, 
                           label=f'Buy Signals ({len(buy_signals)})', zorder=5)
            
            # Plot sell signals
            sell_signals = df[df['sell_signal'] == 1]
            if len(sell_signals) > 0:
                ax1.scatter(sell_signals.index, sell_signals['close'], 
                           color='#FF4444', marker='v', s=120, 
                           label=f'Sell Signals ({len(sell_signals)})', zorder=5)
            
            ax1.set_title(f'{symbol} - Bollinger Bands Strategy', 
                         color='#FFFFFF', fontsize=16, fontweight='bold')
            ax1.set_ylabel('Price (USDT)', color='#FFFFFF', fontweight='bold')
            ax1.tick_params(colors='#FFFFFF')
            ax1.grid(True, alpha=0.3, color='#444444')
            ax1.legend(facecolor='#1A1A1A', edgecolor='#444444', 
                      labelcolor='#FFFFFF', framealpha=0.9)
            
            # Plot 2: %B indicator (Bollinger Band %)
            ax2.set_facecolor('#0D0E11')
            
            # Plot %B line
            ax2.plot(df.index, df['bb_percent'], color='#00D4FF', linewidth=2, label='%B')
            
            # Plot reference lines
            ax2.axhline(y=1.0, color='#FF4444', linestyle='--', alpha=0.7, label='Overbought (1.0)')
            ax2.axhline(y=0.0, color='#00FF88', linestyle='--', alpha=0.7, label='Oversold (0.0)')
            ax2.axhline(y=0.5, color='#FFAA00', linestyle=':', alpha=0.5, label='Middle (0.5)')
            
            # Fill overbought/oversold areas
            ax2.fill_between(df.index, 0.8, 1.2, color='#FF4444', alpha=0.1)
            ax2.fill_between(df.index, -0.2, 0.2, color='#00FF88', alpha=0.1)
            
            ax2.set_title('Bollinger Band %B Indicator', color='#FFFFFF', fontsize=14, fontweight='bold')
            ax2.set_ylabel('%B', color='#FFFFFF', fontweight='bold')
            ax2.set_xlabel('Time', color='#FFFFFF', fontweight='bold')
            ax2.set_ylim(-0.2, 1.2)
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
            print(f"Error creating Bollinger Bands chart: {str(e)}")
            traceback.print_exc()
            if 'plt' in locals():
                plt.close()
            return None
    
    def get_strategy_info(self):
        """Get strategy information"""
        return {
            'name': self.name,
            'description': 'Bollinger Bands strategy using volatility bands for mean reversion trading',
            'parameters': {
                'period': {
                    'description': 'Number of periods for moving average and standard deviation',
                    'default': 20,
                    'range': '10-50'
                },
                'std_dev': {
                    'description': 'Number of standard deviations for band width',
                    'default': 2.0,
                    'range': '1.5-3.0'
                }
            },
            'category': 'technical',
            'risk_level': 'medium',
            'best_timeframes': ['1h', '4h', '1d']
        }

def run_bollinger_bands_analysis(symbol='BTC/USDT', timeframe='1h', limit=500, **kwargs):
    """Standalone function to run Bollinger Bands analysis"""
    try:
        # Extract parameters
        period = kwargs.get('period', 20)
        std_dev = kwargs.get('std_dev', 2.0)
        
        # Create strategy instance
        strategy = BollingerBandsStrategy(
            period=period,
            std_dev=std_dev
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
        print(f"Error in Bollinger Bands analysis: {str(e)}")
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
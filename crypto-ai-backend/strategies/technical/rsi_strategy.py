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
    RSI (Relative Strength Index) Strategy
    
    This strategy uses:
    1. RSI indicator for overbought/oversold conditions
    2. RSI > 70 = Overbought (Sell signal)
    3. RSI < 30 = Oversold (Buy signal)
    4. RSI crossings of 50 line for trend confirmation
    """
    
    def __init__(self, rsi_period=14, overbought_level=70, oversold_level=30):
        self.name = "RSI Strategy"
        self.rsi_period = rsi_period
        self.overbought_level = overbought_level
        self.oversold_level = oversold_level
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
    
    def generate_signals(self, symbol='BTC/USDT', timeframe='1h', limit=500):
        """Generate RSI-based trading signals"""
        try:
            df = self.fetch_data(symbol, timeframe, limit)
            if df is None or len(df) == 0:
                return None
            
            # Calculate RSI
            df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
            
            # Initialize signal columns
            df['buy_signal'] = 0
            df['sell_signal'] = 0
            df['position'] = 0
            
            # Generate signals based on RSI levels
            current_position = 0
            
            for i in range(len(df)):
                current_rsi = df.iloc[i]['rsi']
                
                if pd.isna(current_rsi):
                    df.iloc[i, df.columns.get_loc('position')] = current_position
                    continue
                
                # Buy signal: RSI crosses above oversold level and we're not in position
                if current_rsi < self.oversold_level and current_position == 0:
                    if i > 0 and df.iloc[i-1]['rsi'] >= self.oversold_level:
                        df.iloc[i, df.columns.get_loc('buy_signal')] = 1
                        current_position = 1
                
                # Sell signal: RSI crosses above overbought level and we're in position
                elif current_rsi > self.overbought_level and current_position == 1:
                    if i > 0 and df.iloc[i-1]['rsi'] <= self.overbought_level:
                        df.iloc[i, df.columns.get_loc('sell_signal')] = 1
                        current_position = 0
                
                # Alternative sell signal: RSI drops back below 50 (trend change)
                elif current_rsi < 50 and current_position == 1:
                    if i > 0 and df.iloc[i-1]['rsi'] >= 50:
                        df.iloc[i, df.columns.get_loc('sell_signal')] = 1
                        current_position = 0
                
                df.iloc[i, df.columns.get_loc('position')] = current_position
            
            # Calculate some performance metrics
            buy_signals = df[df['buy_signal'] == 1]
            sell_signals = df[df['sell_signal'] == 1]
            
            current_signal = "HOLD"
            if len(df) > 0:
                last_rsi = df.iloc[-1]['rsi']
                last_position = df.iloc[-1]['position']
                
                if pd.notna(last_rsi):
                    if last_rsi < self.oversold_level and last_position == 0:
                        current_signal = "BUY"
                    elif last_rsi > self.overbought_level and last_position == 1:
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
                'current_rsi': float(df.iloc[-1]['rsi']) if len(df) > 0 and pd.notna(df.iloc[-1]['rsi']) else 0,
                'total_buy_signals': len(buy_signals),
                'total_sell_signals': len(sell_signals),
                'recent_signals': self._get_recent_signals(df),
                'analysis_data': df,
                'parameters_used': {
                    'rsi_period': self.rsi_period,
                    'overbought_level': self.overbought_level,
                    'oversold_level': self.oversold_level,
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
        """Create RSI strategy chart"""
        try:
            if analysis_data is None or len(analysis_data) == 0:
                return None
                
            df = analysis_data.copy()
            
            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), 
                                         gridspec_kw={'height_ratios': [2, 1]},
                                         facecolor='#0D0E11')
            
            # Plot 1: Price and signals
            ax1.set_facecolor('#0D0E11')
            
            # Plot candlesticks (simplified as line for now)
            ax1.plot(df.index, df['close'], color='#FFFFFF', linewidth=1.5, label='Price')
            
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
            
            ax1.set_title(f'{symbol} - RSI Strategy Analysis', 
                         color='#FFFFFF', fontsize=16, fontweight='bold')
            ax1.set_ylabel('Price (USDT)', color='#FFFFFF', fontweight='bold')
            ax1.tick_params(colors='#FFFFFF')
            ax1.grid(True, alpha=0.3, color='#444444')
            ax1.legend(facecolor='#1A1A1A', edgecolor='#444444', 
                      labelcolor='#FFFFFF', framealpha=0.9)
            
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
    
    def get_strategy_info(self):
        """Get strategy information"""
        return {
            'name': self.name,
            'description': 'RSI-based strategy using overbought/oversold levels for entry/exit signals',
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
                }
            },
            'category': 'technical',
            'risk_level': 'medium',
            'best_timeframes': ['1h', '4h', '1d']
        }

def run_rsi_analysis(symbol='BTC/USDT', timeframe='1h', limit=500, **kwargs):
    """Standalone function to run RSI analysis"""
    try:
        # Extract parameters
        rsi_period = kwargs.get('rsi_period', 14)
        overbought_level = kwargs.get('overbought_level', 70)
        oversold_level = kwargs.get('oversold_level', 30)
        
        # Create strategy instance
        strategy = RSIStrategy(
            rsi_period=rsi_period,
            overbought_level=overbought_level,
            oversold_level=oversold_level
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
"""
Chart Data Formatter for TradingView Lightweight Charts

Formats strategy data for use with TradingView Lightweight Charts library
"""

import pandas as pd
from datetime import datetime
import numpy as np


class ChartDataFormatter:
    """Format strategy data for TradingView Lightweight Charts"""
    
    @staticmethod
    def format_candlestick_data(df):
        """
        Format OHLCV data for candlestick chart
        
        Expected format:
        [
            { time: '2023-01-01', open: 100, high: 110, low: 90, close: 105 },
            ...
        ]
        """
        candlestick_data = []
        
        for idx, row in df.iterrows():
            candlestick_data.append({
                'time': idx.strftime('%Y-%m-%d %H:%M:%S') if hasattr(idx, 'strftime') else str(idx),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close'])
            })
            
        return candlestick_data
    
    @staticmethod
    def format_volume_data(df):
        """
        Format volume data for histogram
        
        Expected format:
        [
            { time: '2023-01-01', value: 1000000, color: 'rgba(0, 150, 136, 0.8)' },
            ...
        ]
        """
        volume_data = []
        
        for idx, row in df.iterrows():
            # Green for up candles, red for down
            color = 'rgba(0, 150, 136, 0.8)' if row['close'] > row['open'] else 'rgba(255, 82, 82, 0.8)'
            
            volume_data.append({
                'time': idx.strftime('%Y-%m-%d %H:%M:%S') if hasattr(idx, 'strftime') else str(idx),
                'value': float(row['volume']),
                'color': color
            })
            
        return volume_data
    
    @staticmethod
    def format_line_series(df, column_name, color='#2962FF'):
        """
        Format any column as a line series (e.g., SMA, EMA)
        
        Expected format:
        [
            { time: '2023-01-01', value: 100 },
            ...
        ]
        """
        line_data = []
        
        for idx, row in df.iterrows():
            if pd.notna(row[column_name]):
                line_data.append({
                    'time': idx.strftime('%Y-%m-%d %H:%M:%S') if hasattr(idx, 'strftime') else str(idx),
                    'value': float(row[column_name])
                })
                
        return line_data
    
    @staticmethod
    def format_markers(df, buy_col='signal', sell_col='signal'):
        """
        Format buy/sell signals as markers
        
        Expected format:
        [
            {
                time: '2023-01-01',
                position: 'belowBar',
                color: '#2196F3',
                shape: 'arrowUp',
                text: 'Buy'
            },
            ...
        ]
        """
        markers = []
        
        for idx, row in df.iterrows():
            if buy_col in row and row[buy_col] == 1:
                markers.append({
                    'time': idx.strftime('%Y-%m-%d %H:%M:%S') if hasattr(idx, 'strftime') else str(idx),
                    'position': 'belowBar',
                    'color': '#26a69a',
                    'shape': 'arrowUp',
                    'text': 'Buy'
                })
            elif sell_col in row and (
                (sell_col == 'signal' and row[sell_col] == -1) or 
                (sell_col != 'signal' and row[sell_col] == 1)
            ):
                markers.append({
                    'time': idx.strftime('%Y-%m-%d %H:%M:%S') if hasattr(idx, 'strftime') else str(idx),
                    'position': 'aboveBar',
                    'color': '#ef5350',
                    'shape': 'arrowDown',
                    'text': 'Sell'
                })
                
        return markers
    
    @staticmethod
    def format_pattern_annotations(df, pattern_col='pattern_detected'):
        """
        Format pattern detections as annotations
        
        Returns both markers and price levels
        """
        annotations = []
        price_levels = []
        
        for idx, row in df.iterrows():
            if pattern_col in row and row[pattern_col] and row[pattern_col] != '' and row[pattern_col] != 'none':
                time_str = idx.strftime('%Y-%m-%d %H:%M:%S') if hasattr(idx, 'strftime') else str(idx)
                
                # Add marker for pattern
                annotations.append({
                    'time': time_str,
                    'position': 'aboveBar',
                    'color': '#9c27b0',
                    'shape': 'circle',
                    'text': row[pattern_col]
                })
                
                # Add horizontal lines for stop loss and take profit if available
                if 'stop_loss' in row and pd.notna(row['stop_loss']) and row['stop_loss'] > 0:
                    price_levels.append({
                        'price': float(row['stop_loss']),
                        'color': '#ef5350',
                        'lineWidth': 1,
                        'lineStyle': 2,  # Dashed
                        'axisLabelVisible': True,
                        'title': 'SL'
                    })
                    
                if 'take_profit' in row and pd.notna(row['take_profit']) and row['take_profit'] > 0:
                    price_levels.append({
                        'price': float(row['take_profit']),
                        'color': '#26a69a',
                        'lineWidth': 1,
                        'lineStyle': 2,  # Dashed
                        'axisLabelVisible': True,
                        'title': 'TP'
                    })
                    
        return annotations, price_levels
    
    @staticmethod
    def format_strategy_data(df, strategy_type='default'):
        """
        Format all strategy data for TradingView Lightweight Charts
        
        Returns a complete data structure ready for the frontend
        """
        chart_data = {
            'candlestick': ChartDataFormatter.format_candlestick_data(df),
            'volume': ChartDataFormatter.format_volume_data(df),
            'markers': ChartDataFormatter.format_markers(df),
            'indicators': {},
            'annotations': [],
            'priceLevels': []
        }
        
        # Add moving averages if present
        if 'sma20' in df.columns:
            chart_data['indicators']['sma20'] = {
                'name': 'SMA 20',
                'data': ChartDataFormatter.format_line_series(df, 'sma20', '#FFA726'),
                'color': '#FFA726'
            }
            
        if 'sma50' in df.columns:
            chart_data['indicators']['sma50'] = {
                'name': 'SMA 50',
                'data': ChartDataFormatter.format_line_series(df, 'sma50', '#EF5350'),
                'color': '#EF5350'
            }
            
        # Add pattern-specific data
        if 'pattern_detected' in df.columns:
            annotations, price_levels = ChartDataFormatter.format_pattern_annotations(df)
            chart_data['annotations'].extend(annotations)
            chart_data['priceLevels'].extend(price_levels)
            
        # Strategy-specific formatting
        if strategy_type == 'bollinger':
            if 'upper_band' in df.columns:
                chart_data['indicators']['upper_band'] = {
                    'name': 'Upper Band',
                    'data': ChartDataFormatter.format_line_series(df, 'upper_band', '#2196F3'),
                    'color': '#2196F3'
                }
            if 'lower_band' in df.columns:
                chart_data['indicators']['lower_band'] = {
                    'name': 'Lower Band',
                    'data': ChartDataFormatter.format_line_series(df, 'lower_band', '#2196F3'),
                    'color': '#2196F3'
                }
                
        elif strategy_type == 'rsi':
            if 'rsi' in df.columns:
                # RSI needs a separate pane
                chart_data['oscillators'] = {
                    'rsi': {
                        'name': 'RSI',
                        'data': ChartDataFormatter.format_line_series(df, 'rsi', '#9C27B0'),
                        'color': '#9C27B0',
                        'overbought': 70,
                        'oversold': 30
                    }
                }
                
        # Add statistics
        if len(df) > 0:
            chart_data['statistics'] = {
                'currentPrice': float(df['close'].iloc[-1]),
                'priceChange': float(df['close'].iloc[-1] - df['close'].iloc[0]),
                'priceChangePercent': float((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100),
                'highPrice': float(df['high'].max()),
                'lowPrice': float(df['low'].min()),
                'avgVolume': float(df['volume'].mean())
            }
            
        return chart_data
# routes/chart_routes.py

from flask import Blueprint, jsonify, request
from strategies.technical.rsi_strategy import RSIStrategy
import traceback
import json

chart_bp = Blueprint('chart', __name__)

@chart_bp.route('/api/chart/interactive/<symbol>', methods=['GET'])
def get_interactive_chart_data(symbol):
    """Get chart data in JSON format for TradingView Lightweight Charts"""
    try:
        # Get parameters
        timeframe = request.args.get('timeframe', '1h')
        limit = int(request.args.get('limit', 500))
        
        # Replace / with - for symbol
        symbol = symbol.replace('-', '/')
        
        # Create strategy instance
        strategy = RSIStrategy(
            rsi_period=14,
            overbought_level=70,
            oversold_level=30,
            trendline_lookback=30,
            rolling_window_order=4
        )
        
        # Generate signals
        result = strategy.generate_signals(symbol, timeframe, limit)
        
        if result and result.get('success'):
            # Get chart data in JSON format
            chart_data = strategy.get_chart_data(result['analysis_data'], symbol)
            
            if chart_data:
                return jsonify({
                    'success': True,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'currentSignal': result['current_signal'],
                    'chartData': chart_data
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to generate chart data'
                }), 500
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to generate signals')
            }), 500
            
    except Exception as e:
        print(f"Error generating interactive chart data: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chart_bp.route('/api/chart/strategies', methods=['GET'])
def get_available_strategies():
    """Get list of available strategies"""
    return jsonify({
        'success': True,
        'strategies': [
            {
                'id': 'trendline_breakout',
                'name': 'Trendline Breakout (with RSI)',
                'description': 'Dynamic support/resistance breakout with RSI display',
                'category': 'technical',
                'endpoint': '/api/chart/interactive/{symbol}'
            }
        ]
    })

@chart_bp.route('/api/chart/view/<symbol>', methods=['GET'])
def view_interactive_chart(symbol):
    """Serve interactive chart as HTML page"""
    try:
        from flask import render_template_string
        
        # Get parameters
        timeframe = request.args.get('timeframe', '1h')
        limit = int(request.args.get('limit', 500))
        
        # Replace / with - for symbol
        symbol_clean = symbol.replace('-', '/')
        
        # Create strategy instance
        strategy = RSIStrategy(
            rsi_period=14,
            overbought_level=70,
            oversold_level=30,
            trendline_lookback=30,
            rolling_window_order=4
        )
        
        # Generate signals
        result = strategy.generate_signals(symbol_clean, timeframe, limit)
        
        if result and result.get('success'):
            # Get chart data in JSON format
            chart_data = strategy.get_chart_data(result['analysis_data'], symbol_clean)
            
            if chart_data:
                chart_data['symbol'] = symbol_clean
                chart_data['currentSignal'] = result['current_signal']
                
                # Read the template file
                import os
                template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'trading_chart.html')
                
                if os.path.exists(template_path):
                    with open(template_path, 'r') as f:
                        html_template = f.read()
                    
                    # Inject the chart data into the template
                    html_with_data = html_template.replace(
                        '// Request data from React Native',
                        f'// Injected chart data\nconst chartData = {json.dumps(chart_data)};\nsetTimeout(() => updateChart(chartData), 100);'
                    )
                    
                    return html_with_data
                else:
                    # Return a simple HTML with chart data
                    return f'''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Interactive Chart - {symbol_clean}</title>
                        <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
                        <style>
                            body {{ margin: 0; background: #0D0E11; color: #d1d4dc; font-family: Arial, sans-serif; }}
                            #chart {{ width: 100vw; height: 100vh; }}
                        </style>
                    </head>
                    <body>
                        <div id="chart"></div>
                        <script>
                            const chartData = {json.dumps(chart_data)};
                            // Chart initialization code would go here
                            console.log('Chart data loaded:', chartData);
                        </script>
                    </body>
                    </html>
                    '''
            else:
                return jsonify({'error': 'Failed to generate chart data'}), 500
        else:
            return jsonify({'error': result.get('error', 'Failed to generate signals')}), 500
            
    except Exception as e:
        print(f"Error serving interactive chart: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
import ccxt
import json
from datetime import datetime, timedelta
import time
import pandas as pd

def fetch_historical_ohlcv(exchange, symbol, timeframe, start_date, end_date):
    """
    Fetch historical OHLCV data from exchange
    
    Args:
        exchange: CCXT exchange instance
        symbol: Trading pair (e.g., 'BTC/USDT')
        timeframe: Candle timeframe (e.g., '1h')
        start_date: Start date string (e.g., '2024-01-01')
        end_date: End date string (e.g., '2024-12-31')
    
    Returns:
        List of OHLCV candles
    """
    # Convert dates to timestamps
    start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
    end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
    
    all_candles = []
    current_timestamp = start_timestamp
    
    print(f"Fetching {symbol} data from {start_date} to {end_date}...")
    
    while current_timestamp < end_timestamp:
        try:
            # Fetch candles (max 1000 at a time for Binance)
            candles = exchange.fetch_ohlcv(
                symbol, 
                timeframe, 
                since=current_timestamp, 
                limit=1000
            )
            
            if not candles:
                break
            
            # Add candles to our list
            all_candles.extend(candles)
            
            # Update timestamp to the last candle's timestamp
            current_timestamp = candles[-1][0] + 1
            
            print(f"Fetched {len(candles)} candles, total: {len(all_candles)}")
            
            # Sleep to respect rate limits (Binance allows 1200 requests/minute)
            time.sleep(0.1)  # 100ms delay between requests
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            time.sleep(1)  # Wait 1 second on error
            
    # Filter candles to ensure they're within our date range
    filtered_candles = [
        candle for candle in all_candles 
        if start_timestamp <= candle[0] <= end_timestamp
    ]
    
    return filtered_candles

def generate_simulated_trades(candles, quantity=0.01):
    """
    Generate simulated trades based on price movements
    
    Logic:
    - Buy when price drops > 1% from previous candle
    - Sell when price rises > 1% from previous candle (only if holding)
    
    Args:
        candles: List of OHLCV candles
        quantity: Trade quantity in BTC
    
    Returns:
        List of trade dictionaries
    """
    trades = []
    trade_id = 1
    position = 0  # Track how much BTC we're holding
    
    # Iterate through candles (skip first one as we need previous price)
    for i in range(1, len(candles)):
        current_candle = candles[i]
        previous_candle = candles[i-1]
        
        # Extract close prices
        current_close = current_candle[4]  # Close price is at index 4
        previous_close = previous_candle[4]
        
        # Calculate percentage change
        price_change_pct = ((current_close - previous_close) / previous_close) * 100
        
        # Trading logic
        trade = None
        
        # Buy signal: price dropped more than 1%
        if price_change_pct < -1.0:
            trade = {
                'trade_id': trade_id,
                'timestamp': current_candle[0],  # Timestamp is at index 0
                'datetime': datetime.fromtimestamp(current_candle[0] / 1000).isoformat(),
                'side': 'buy',
                'price': current_close,
                'quantity': quantity,
                'value': current_close * quantity,
                'price_change_pct': round(price_change_pct, 2)
            }
            position += quantity
            trade_id += 1
            
        # Sell signal: price rose more than 1% AND we have position to sell
        elif price_change_pct > 1.0 and position >= quantity:
            trade = {
                'trade_id': trade_id,
                'timestamp': current_candle[0],
                'datetime': datetime.fromtimestamp(current_candle[0] / 1000).isoformat(),
                'side': 'sell',
                'price': current_close,
                'quantity': quantity,
                'value': current_close * quantity,
                'price_change_pct': round(price_change_pct, 2)
            }
            position -= quantity
            trade_id += 1
        
        # Add trade if one was generated
        if trade:
            trades.append(trade)
    
    return trades

def calculate_trade_statistics(trades):
    """
    Calculate basic statistics about the trades
    
    Args:
        trades: List of trade dictionaries
    
    Returns:
        Dictionary with trade statistics
    """
    if not trades:
        return {}
    
    buy_trades = [t for t in trades if t['side'] == 'buy']
    sell_trades = [t for t in trades if t['side'] == 'sell']
    
    total_buy_value = sum(t['value'] for t in buy_trades)
    total_sell_value = sum(t['value'] for t in sell_trades)
    
    avg_buy_price = sum(t['price'] for t in buy_trades) / len(buy_trades) if buy_trades else 0
    avg_sell_price = sum(t['price'] for t in sell_trades) / len(sell_trades) if sell_trades else 0
    
    stats = {
        'total_trades': len(trades),
        'buy_trades': len(buy_trades),
        'sell_trades': len(sell_trades),
        'total_buy_value': round(total_buy_value, 2),
        'total_sell_value': round(total_sell_value, 2),
        'average_buy_price': round(avg_buy_price, 2),
        'average_sell_price': round(avg_sell_price, 2),
        'net_value': round(total_sell_value - total_buy_value, 2)
    }
    
    return stats

def main():
    """
    Main function to orchestrate the trade simulation
    """
    # Initialize Binance exchange (no authentication needed for public data)
    exchange = ccxt.binance({
        'enableRateLimit': True,  # Automatic rate limiting
        'options': {
            'defaultType': 'spot',  # Use spot market
        }
    })
    
    # Parameters
    symbol = 'BTC/USDT'
    timeframe = '1h'
    start_date = '2024-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')  # Today
    trade_quantity = 0.01  # BTC
    
    print(f"=== BTC/USDT Trade Simulation ===")
    print(f"Period: {start_date} to {end_date}")
    print(f"Trade Quantity: {trade_quantity} BTC")
    print(f"Strategy: Buy on >1% drop, Sell on >1% rise")
    print("=" * 40)
    
    try:
        # Fetch historical data
        candles = fetch_historical_ohlcv(
            exchange, 
            symbol, 
            timeframe, 
            start_date, 
            end_date
        )
        
        print(f"\nTotal candles fetched: {len(candles)}")
        
        if not candles:
            print("No data fetched!")
            return
        
        # Generate simulated trades
        print("\nGenerating simulated trades...")
        trades = generate_simulated_trades(candles, trade_quantity)
        
        print(f"Generated {len(trades)} trades")
        
        # Calculate statistics
        stats = calculate_trade_statistics(trades)
        
        # Print statistics
        print("\n=== Trade Statistics ===")
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        # Save trades to JSON file
        output_data = {
            'metadata': {
                'symbol': symbol,
                'timeframe': timeframe,
                'start_date': start_date,
                'end_date': end_date,
                'trade_quantity': trade_quantity,
                'strategy': 'Buy on >1% drop, Sell on >1% rise',
                'generated_at': datetime.now().isoformat()
            },
            'statistics': stats,
            'trades': trades
        }
        
        # Write to file
        with open('simulated_trades.json', 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nTrades saved to 'simulated_trades.json'")
        
        # Also save a CSV version for easy viewing in Excel
        if trades:
            df = pd.DataFrame(trades)
            df.to_csv('simulated_trades.csv', index=False)
            print("Also saved as 'simulated_trades.csv' for spreadsheet viewing")
        
        # Print first and last few trades as examples
        if trades:
            print("\n=== First 3 Trades ===")
            for trade in trades[:3]:
                print(f"{trade['datetime']} - {trade['side'].upper()} @ ${trade['price']:,.2f}")
            
            if len(trades) > 6:
                print("\n=== Last 3 Trades ===")
                for trade in trades[-3:]:
                    print(f"{trade['datetime']} - {trade['side'].upper()} @ ${trade['price']:,.2f}")
        
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
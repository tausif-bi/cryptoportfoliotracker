"""
Migration utilities for moving from JSON files to database
"""
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from models.database import db, User, Portfolio, Trade, Holding
from utils.logger import get_logger
from utils.exceptions import DataValidationError
import uuid

logger = get_logger(__name__)

class DataMigrator:
    """Handle migration of data from JSON files to database"""
    
    def __init__(self, app):
        self.app = app
        
    def migrate_all_data(self, user_id=None):
        """Migrate all data from JSON files to database"""
        logger.info("Starting data migration from JSON files to database")
        
        try:
            # Create default user if none provided
            if not user_id:
                user_id = self.create_default_user()
            
            # Create default portfolio
            portfolio_id = self.create_default_portfolio(user_id)
            
            # Migrate trades data
            trades_migrated = self.migrate_trades_data(portfolio_id)
            
            # Calculate and update holdings based on trades
            self.update_holdings_from_trades(portfolio_id)
            
            logger.info(f"Migration completed successfully. Migrated {trades_migrated} trades")
            return {
                'success': True,
                'user_id': str(user_id),
                'portfolio_id': str(portfolio_id),
                'trades_migrated': trades_migrated
            }
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            db.session.rollback()
            raise e
    
    def create_default_user(self):
        """Create a default user for migration"""
        # Check if default user exists
        user = User.query.filter_by(username='default_user').first()
        if user:
            logger.info("Default user already exists")
            return user.id
        
        # Create new default user
        user = User(
            username='default_user',
            email='user@cryptoportfolio.local',
            password_hash='default_hash_change_after_auth_implementation',
            is_active=True
        )
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"Created default user with ID: {user.id}")
        return user.id
    
    def create_default_portfolio(self, user_id):
        """Create a default portfolio for the user"""
        # Check if default portfolio exists
        portfolio = Portfolio.query.filter_by(
            user_id=user_id, 
            is_default=True
        ).first()
        
        if portfolio:
            logger.info("Default portfolio already exists")
            return portfolio.id
        
        # Create new default portfolio
        portfolio = Portfolio(
            user_id=user_id,
            name='Main Portfolio',
            description='Default portfolio migrated from JSON data',
            is_default=True,
            is_active=True
        )
        
        db.session.add(portfolio)
        db.session.commit()
        
        logger.info(f"Created default portfolio with ID: {portfolio.id}")
        return portfolio.id
    
    def migrate_trades_data(self, portfolio_id):
        """Migrate trades from JSON files"""
        trades_file_paths = [
            'simulated_trades.json',
            'simulated_trades.csv'  # We'll handle CSV if JSON doesn't exist
        ]
        
        trades_data = None
        metadata = None
        
        # Try to find and load trades data
        for file_path in trades_file_paths:
            full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)
            if os.path.exists(full_path):
                logger.info(f"Found trades file: {file_path}")
                
                if file_path.endswith('.json'):
                    trades_data, metadata = self.load_json_trades(full_path)
                elif file_path.endswith('.csv'):
                    trades_data = self.load_csv_trades(full_path)
                    metadata = None
                
                if trades_data:
                    break
        
        if not trades_data:
            logger.warning("No trades data found to migrate")
            return 0
        
        # Extract symbol from metadata
        symbol = None
        if metadata and 'symbol' in metadata:
            symbol = metadata['symbol']
            logger.info(f"Using symbol from metadata: {symbol}")
        
        # Migrate each trade
        migrated_count = 0
        for trade_data in trades_data:
            try:
                # Add symbol to trade data if missing
                if symbol and 'symbol' not in trade_data:
                    trade_data['symbol'] = symbol
                    
                self.migrate_single_trade(portfolio_id, trade_data)
                migrated_count += 1
            except Exception as e:
                logger.error(f"Failed to migrate trade: {trade_data}. Error: {str(e)}")
                continue
        
        db.session.commit()
        logger.info(f"Successfully migrated {migrated_count} trades")
        return migrated_count
    
    def load_json_trades(self, file_path):
        """Load trades from JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Handle different JSON structures
            if isinstance(data, list):
                return data, None
            elif isinstance(data, dict):
                # Check if this is the simulated_trades.json structure
                if 'metadata' in data and 'statistics' in data:
                    # Extract trades (all keys that are numbers)
                    trades = []
                    metadata = data.get('metadata', {})
                    for key, value in data.items():
                        if key.isdigit() and isinstance(value, dict):
                            trades.append(value)
                    return trades, metadata
                elif 'trades' in data:
                    metadata = data.get('metadata', {})
                    return data['trades'], metadata
                else:
                    # Fallback - treat remaining dict items as trades
                    metadata = data.get('metadata', {})
                    trades = []
                    for key, value in data.items():
                        if key not in ['metadata', 'statistics'] and isinstance(value, dict):
                            trades.append(value)
                    return trades, metadata
            else:
                logger.warning(f"Unexpected JSON structure in {file_path}")
                return [], None
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {str(e)}")
            return [], None
        except Exception as e:
            logger.error(f"Error loading {file_path}: {str(e)}")
            return [], None
    
    def load_csv_trades(self, file_path):
        """Load trades from CSV file and convert to JSON-like structure"""
        try:
            import pandas as pd
            df = pd.read_csv(file_path)
            
            # Convert DataFrame to list of dictionaries
            return df.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error loading CSV {file_path}: {str(e)}")
            return []
    
    def migrate_single_trade(self, portfolio_id, trade_data):
        """Migrate a single trade record"""
        # Normalize trade data fields
        symbol = self.normalize_symbol(trade_data.get('symbol'))
        if not symbol:
            raise DataValidationError('symbol', 'Invalid or missing symbol')
        
        base_asset, quote_asset = symbol.split('/')
        
        # Extract trade details with fallbacks
        quantity = self.safe_decimal(trade_data.get('quantity') or trade_data.get('amount') or 0)
        price = self.safe_decimal(trade_data.get('price') or 0)
        side = str(trade_data.get('side', 'buy')).lower()
        
        if quantity <= 0 or price <= 0:
            raise DataValidationError('quantity/price', 'Invalid quantity or price')
        
        # Calculate total value
        total_value = quantity * price
        
        # Handle timestamp
        executed_at = self.parse_timestamp(
            trade_data.get('timestamp') or 
            trade_data.get('datetime') or 
            datetime.now(timezone.utc)
        )
        
        # Handle fees
        fee_amount = self.safe_decimal(trade_data.get('fee_amount') or 0)
        fee_currency = trade_data.get('fee_currency') or quote_asset
        
        # Check if trade already exists (avoid duplicates)
        exchange_trade_id = str(trade_data.get('trade_id') or trade_data.get('id') or uuid.uuid4())
        existing_trade = Trade.query.filter_by(
            portfolio_id=portfolio_id,
            exchange_trade_id=exchange_trade_id
        ).first()
        
        if existing_trade:
            logger.debug(f"Trade {exchange_trade_id} already exists, skipping")
            return
        
        # Create new trade record
        trade = Trade(
            portfolio_id=portfolio_id,
            exchange_trade_id=exchange_trade_id,
            exchange_name=trade_data.get('exchange_name', 'imported'),
            symbol=symbol,
            base_asset=base_asset,
            quote_asset=quote_asset,
            side=side,
            type=trade_data.get('type', 'market'),
            quantity=quantity,
            price=price,
            total_value=total_value,
            fee_amount=fee_amount,
            fee_currency=fee_currency,
            executed_at=executed_at,
            trade_metadata={
                'imported_from': 'json_migration',
                'original_data': trade_data
            }
        )
        
        db.session.add(trade)
        logger.debug(f"Added trade: {side} {quantity} {symbol} at {price}")
    
    def update_holdings_from_trades(self, portfolio_id):
        """Calculate current holdings based on trades"""
        logger.info("Calculating holdings from trades")
        
        # Get all trades for this portfolio
        trades = Trade.query.filter_by(portfolio_id=portfolio_id).order_by(Trade.executed_at).all()
        
        # Calculate holdings for each asset
        holdings_data = {}
        
        for trade in trades:
            asset = trade.base_asset
            
            if asset not in holdings_data:
                holdings_data[asset] = {
                    'total_quantity': Decimal('0'),
                    'total_cost': Decimal('0'),
                    'trades_count': 0
                }
            
            if trade.side == 'buy':
                # Add to holdings
                holdings_data[asset]['total_quantity'] += trade.quantity
                holdings_data[asset]['total_cost'] += trade.total_value
            elif trade.side == 'sell':
                # Subtract from holdings
                holdings_data[asset]['total_quantity'] -= trade.quantity
                # For sells, we subtract the original cost basis (this is simplified)
                if holdings_data[asset]['total_quantity'] > 0:
                    holdings_data[asset]['total_cost'] -= trade.total_value
            
            holdings_data[asset]['trades_count'] += 1
        
        # Create or update holding records
        for asset, data in holdings_data.items():
            if data['total_quantity'] <= 0:
                continue  # Skip assets with zero or negative balance
            
            # Calculate average cost
            avg_cost = data['total_cost'] / data['total_quantity'] if data['total_quantity'] > 0 else Decimal('0')
            
            # Check if holding exists
            holding = Holding.query.filter_by(
                portfolio_id=portfolio_id,
                asset=asset
            ).first()
            
            if holding:
                # Update existing holding
                holding.total_quantity = data['total_quantity']
                holding.available_quantity = data['total_quantity']  # Simplified
                holding.average_cost = avg_cost
                holding.total_cost = data['total_cost']
                holding.updated_at = datetime.now(timezone.utc)
            else:
                # Create new holding
                holding = Holding(
                    portfolio_id=portfolio_id,
                    asset=asset,
                    total_quantity=data['total_quantity'],
                    available_quantity=data['total_quantity'],
                    locked_quantity=Decimal('0'),
                    average_cost=avg_cost,
                    total_cost=data['total_cost']
                )
                db.session.add(holding)
            
            logger.debug(f"Updated holding: {data['total_quantity']} {asset} at avg cost {avg_cost}")
        
        db.session.commit()
        logger.info(f"Updated holdings for {len(holdings_data)} assets")
    
    def normalize_symbol(self, symbol):
        """Normalize trading symbol format"""
        if not symbol:
            return None
        
        symbol = str(symbol).upper().strip()
        
        # Handle common variations
        if '/' not in symbol and len(symbol) > 3:
            # Try to infer base/quote split for common patterns
            if symbol.endswith('USDT'):
                base = symbol[:-4]
                quote = 'USDT'
                symbol = f"{base}/USDT"
            elif symbol.endswith('USD'):
                base = symbol[:-3]
                quote = 'USD'
                symbol = f"{base}/USD"
            elif symbol.endswith('BTC'):
                base = symbol[:-3]
                quote = 'BTC'
                symbol = f"{base}/BTC"
            elif symbol.endswith('ETH'):
                base = symbol[:-3]
                quote = 'ETH'
                symbol = f"{base}/ETH"
        
        # Validate format
        if '/' not in symbol:
            return None
        
        parts = symbol.split('/')
        if len(parts) != 2 or not all(parts):
            return None
        
        return symbol
    
    def safe_decimal(self, value):
        """Safely convert value to Decimal"""
        if value is None:
            return Decimal('0')
        
        try:
            return Decimal(str(value))
        except:
            return Decimal('0')
    
    def parse_timestamp(self, timestamp):
        """Parse timestamp from various formats"""
        if isinstance(timestamp, datetime):
            return timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp
        
        if isinstance(timestamp, (int, float)):
            # Unix timestamp
            if timestamp > 1e10:  # Milliseconds
                timestamp = timestamp / 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        
        if isinstance(timestamp, str):
            # Try to parse ISO format
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
            except:
                pass
        
        # Fallback to current time
        return datetime.now(timezone.utc)
    
    def cleanup_json_files(self, backup=True):
        """Clean up JSON files after successful migration"""
        if backup:
            self.backup_json_files()
        
        files_to_remove = ['simulated_trades.json', 'simulated_trades.csv']
        for file_name in files_to_remove:
            file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Removed {file_name}")
    
    def backup_json_files(self):
        """Create backup of JSON files before cleanup"""
        import shutil
        
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data_backup')
        os.makedirs(backup_dir, exist_ok=True)
        
        files_to_backup = ['simulated_trades.json', 'simulated_trades.csv']
        for file_name in files_to_backup:
            file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_name)
            if os.path.exists(file_path):
                backup_path = os.path.join(backup_dir, f"{file_name}.backup")
                shutil.copy2(file_path, backup_path)
                logger.info(f"Backed up {file_name} to {backup_path}")

def run_migration(app):
    """Run the complete migration process"""
    with app.app_context():
        migrator = DataMigrator(app)
        return migrator.migrate_all_data()
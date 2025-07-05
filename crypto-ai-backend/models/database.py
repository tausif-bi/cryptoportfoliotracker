"""
Database models for the crypto portfolio tracker
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timezone
import json
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text, JSON, String, TypeDecorator
import uuid
import os

db = SQLAlchemy()
migrate = Migrate()

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses String(36).
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value

def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    migrate.init_app(app, db)

class User(db.Model):
    """User model for authentication and user management"""
    __tablename__ = 'users'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime(timezone=True))
    
    # Relationships
    portfolios = db.relationship('Portfolio', backref='owner', lazy=True, cascade='all, delete-orphan')
    exchange_credentials = db.relationship('ExchangeCredential', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class ExchangeCredential(db.Model):
    """Encrypted storage for exchange API credentials"""
    __tablename__ = 'exchange_credentials'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    exchange_name = db.Column(db.String(50), nullable=False)
    api_key_encrypted = db.Column(db.Text)  # Encrypted API key
    api_secret_encrypted = db.Column(db.Text)  # Encrypted API secret
    password_encrypted = db.Column(db.Text)  # Encrypted password (for some exchanges)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_used = db.Column(db.DateTime(timezone=True))
    
    # Ensure one active credential per exchange per user
    __table_args__ = (
        db.UniqueConstraint('user_id', 'exchange_name', name='unique_user_exchange'),
    )
    
    def __repr__(self):
        return f'<ExchangeCredential {self.exchange_name} for {self.user_id}>'

class Portfolio(db.Model):
    """Portfolio model for tracking multiple portfolios per user"""
    __tablename__ = 'portfolios'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    trades = db.relationship('Trade', backref='portfolio', lazy=True, cascade='all, delete-orphan')
    holdings = db.relationship('Holding', backref='portfolio', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Portfolio {self.name}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'is_default': self.is_default,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Trade(db.Model):
    """Trade model for storing individual trades"""
    __tablename__ = 'trades'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    portfolio_id = db.Column(GUID(), db.ForeignKey('portfolios.id'), nullable=False)
    exchange_trade_id = db.Column(db.String(100))  # Original trade ID from exchange
    exchange_name = db.Column(db.String(50), nullable=False)
    
    # Trade details
    symbol = db.Column(db.String(20), nullable=False)  # e.g., BTC/USDT
    base_asset = db.Column(db.String(10), nullable=False)  # e.g., BTC
    quote_asset = db.Column(db.String(10), nullable=False)  # e.g., USDT
    side = db.Column(db.String(10), nullable=False)  # buy/sell
    type = db.Column(db.String(20), default='market')  # market/limit/stop
    
    # Quantities and prices
    quantity = db.Column(db.Numeric(20, 8), nullable=False)
    price = db.Column(db.Numeric(20, 8), nullable=False)
    total_value = db.Column(db.Numeric(20, 8), nullable=False)  # quantity * price
    
    # Fees
    fee_amount = db.Column(db.Numeric(20, 8), default=0)
    fee_currency = db.Column(db.String(10))
    
    # Timestamps
    executed_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Additional metadata
    trade_metadata = db.Column(JSON)  # Store additional trade information as JSON
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_trades_portfolio_symbol', 'portfolio_id', 'symbol'),
        db.Index('idx_trades_executed_at', 'executed_at'),
        db.Index('idx_trades_base_asset', 'base_asset'),
    )
    
    def __repr__(self):
        return f'<Trade {self.side} {self.quantity} {self.symbol} at {self.price}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'exchange_trade_id': self.exchange_trade_id,
            'exchange_name': self.exchange_name,
            'symbol': self.symbol,
            'base_asset': self.base_asset,
            'quote_asset': self.quote_asset,
            'side': self.side,
            'type': self.type,
            'quantity': float(self.quantity),
            'price': float(self.price),
            'total_value': float(self.total_value),
            'fee_amount': float(self.fee_amount) if self.fee_amount else 0,
            'fee_currency': self.fee_currency,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'trade_metadata': self.trade_metadata
        }

class Holding(db.Model):
    """Current holdings/balances for a portfolio"""
    __tablename__ = 'holdings'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    portfolio_id = db.Column(GUID(), db.ForeignKey('portfolios.id'), nullable=False)
    asset = db.Column(db.String(10), nullable=False)  # e.g., BTC, ETH
    
    # Quantities
    total_quantity = db.Column(db.Numeric(20, 8), nullable=False, default=0)
    available_quantity = db.Column(db.Numeric(20, 8), nullable=False, default=0)
    locked_quantity = db.Column(db.Numeric(20, 8), nullable=False, default=0)
    
    # Cost basis tracking
    average_cost = db.Column(db.Numeric(20, 8), default=0)
    total_cost = db.Column(db.Numeric(20, 8), default=0)
    
    # Current market data (cached)
    current_price = db.Column(db.Numeric(20, 8))
    current_value_usd = db.Column(db.Numeric(20, 8))
    price_updated_at = db.Column(db.DateTime(timezone=True))
    
    # Timestamps
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Ensure one holding per asset per portfolio
    __table_args__ = (
        db.UniqueConstraint('portfolio_id', 'asset', name='unique_portfolio_asset'),
        db.Index('idx_holdings_portfolio', 'portfolio_id'),
    )
    
    def __repr__(self):
        return f'<Holding {self.total_quantity} {self.asset}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'asset': self.asset,
            'total_quantity': float(self.total_quantity),
            'available_quantity': float(self.available_quantity),
            'locked_quantity': float(self.locked_quantity),
            'average_cost': float(self.average_cost) if self.average_cost else 0,
            'total_cost': float(self.total_cost) if self.total_cost else 0,
            'current_price': float(self.current_price) if self.current_price else 0,
            'current_value_usd': float(self.current_value_usd) if self.current_value_usd else 0,
            'price_updated_at': self.price_updated_at.isoformat() if self.price_updated_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class StrategyResult(db.Model):
    """Store results from trading strategy analysis"""
    __tablename__ = 'strategy_results'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    strategy_name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    timeframe = db.Column(db.String(10), nullable=False)
    
    # Analysis results
    signals = db.Column(JSON)  # Buy/sell signals
    performance_metrics = db.Column(JSON)  # Performance data
    chart_data = db.Column(db.Text)  # Base64 encoded chart image
    
    # Timestamps
    analysis_date = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        db.Index('idx_strategy_results_user_strategy', 'user_id', 'strategy_name'),
        db.Index('idx_strategy_results_analysis_date', 'analysis_date'),
    )
    
    def __repr__(self):
        return f'<StrategyResult {self.strategy_name} {self.symbol}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'signals': self.signals,
            'performance_metrics': self.performance_metrics,
            'chart_data': self.chart_data,
            'analysis_date': self.analysis_date.isoformat() if self.analysis_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class PriceHistory(db.Model):
    """Cache for historical price data"""
    __tablename__ = 'price_history'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    symbol = db.Column(db.String(20), nullable=False)
    timeframe = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False)
    
    # OHLCV data
    open = db.Column(db.Numeric(20, 8), nullable=False)
    high = db.Column(db.Numeric(20, 8), nullable=False)
    low = db.Column(db.Numeric(20, 8), nullable=False)
    close = db.Column(db.Numeric(20, 8), nullable=False)
    volume = db.Column(db.Numeric(20, 8), nullable=False)
    
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Indexes and constraints
    __table_args__ = (
        db.UniqueConstraint('symbol', 'timeframe', 'timestamp', name='unique_price_data'),
        db.Index('idx_price_history_symbol_timeframe', 'symbol', 'timeframe'),
        db.Index('idx_price_history_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f'<PriceHistory {self.symbol} {self.timeframe} {self.timestamp}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'open': float(self.open),
            'high': float(self.high),
            'low': float(self.low),
            'close': float(self.close),
            'volume': float(self.volume),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
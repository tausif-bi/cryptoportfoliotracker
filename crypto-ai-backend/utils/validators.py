"""
Input validation schemas and utilities for API endpoints
"""
from marshmallow import Schema, fields, validate, ValidationError
import re

class ExchangeCredentialsSchema(Schema):
    """Schema for validating exchange credentials"""
    exchangeName = fields.Str(
        required=True,
        validate=validate.OneOf(['binance', 'coinbase', 'kraken', 'bitfinex', 'huobi', 'kucoin', 'okex', 'bybit', 'ftx', 'gate', 'lbank2', 'demo']),
        error_messages={'required': 'Exchange name is required'}
    )
    apiKey = fields.Str(required=False, allow_none=True, validate=validate.Length(min=1, max=500))
    apiSecret = fields.Str(required=False, allow_none=True, validate=validate.Length(min=1, max=500))
    password = fields.Str(required=False, allow_none=True, validate=validate.Length(min=1, max=100))

class TradeQuerySchema(Schema):
    """Schema for validating trade query parameters"""
    symbol = fields.Str(required=False, allow_none=True, validate=validate.Regexp(r'^[A-Z]{2,10}\/[A-Z]{2,10}$'))
    since = fields.Int(required=False, allow_none=True, validate=validate.Range(min=0))
    limit = fields.Int(required=False, allow_none=True, validate=validate.Range(min=1, max=1000))

class StrategyAnalysisSchema(Schema):
    """Schema for validating strategy analysis parameters"""
    symbol = fields.Str(
        required=True,
        validate=validate.Regexp(r'^[A-Z]{2,10}\/[A-Z]{2,10}$'),
        error_messages={'required': 'Symbol is required', 'invalid': 'Invalid symbol format (e.g., BTC/USDT)'}
    )
    timeframe = fields.Str(
        required=False,
        validate=validate.OneOf(['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '3d', '1w']),
        missing='1h'
    )
    limit = fields.Int(required=False, validate=validate.Range(min=50, max=1000), missing=500)

class PortfolioQuerySchema(Schema):
    """Schema for validating portfolio query parameters"""
    period = fields.Str(
        required=False,
        validate=validate.OneOf(['1d', '1w', '1m', '3m', '6m', '1y', 'all']),
        missing='all'
    )

class UserRegistrationSchema(Schema):
    """Schema for validating user registration"""
    username = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=80),
        error_messages={'required': 'Username is required'}
    )
    email = fields.Email(
        required=True,
        error_messages={'required': 'Valid email is required'}
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=128),
        error_messages={'required': 'Password is required'}
    )

class UserLoginSchema(Schema):
    """Schema for validating user login"""
    username_or_email = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=120),
        error_messages={'required': 'Username or email is required'}
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=128),
        error_messages={'required': 'Password is required'}
    )

class PasswordChangeSchema(Schema):
    """Schema for validating password change"""
    current_password = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=128),
        error_messages={'required': 'Current password is required'}
    )
    new_password = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=128),
        error_messages={'required': 'New password is required'}
    )

def validate_json_input(schema_class):
    """Decorator to validate JSON input against a schema"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            from flask import request, jsonify
            
            if not request.is_json:
                return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
            
            try:
                schema = schema_class()
                data = schema.load(request.json or {})
                request.validated_json = data
                return f(*args, **kwargs)
            except ValidationError as err:
                return jsonify({
                    'success': False, 
                    'error': 'Validation failed',
                    'details': err.messages
                }), 400
            except Exception as e:
                return jsonify({'success': False, 'error': 'Invalid JSON format'}), 400
                
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

def validate_query_params(schema_class):
    """Decorator to validate query parameters against a schema"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            from flask import request, jsonify
            
            try:
                schema = schema_class()
                data = schema.load(request.args.to_dict())
                request.validated_args = data
                return f(*args, **kwargs)
            except ValidationError as err:
                return jsonify({
                    'success': False, 
                    'error': 'Invalid query parameters',
                    'details': err.messages
                }), 400
                
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

def sanitize_string(value, max_length=255):
    """Sanitize string input to prevent XSS and injection attacks"""
    if not isinstance(value, str):
        return str(value)
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\'\x00-\x1f\x7f-\x9f]', '', value)
    
    # Limit length
    return sanitized[:max_length]

def validate_symbol_format(symbol):
    """Validate cryptocurrency symbol format"""
    if not symbol:
        return False
    
    # Check for basic format like BTC/USDT, ETH/USD, etc.
    pattern = r'^[A-Z]{2,10}\/[A-Z]{2,10}$'
    return bool(re.match(pattern, symbol.upper()))

def validate_exchange_name(exchange_name):
    """Validate exchange name against supported exchanges"""
    supported_exchanges = [
        'demo', 'binance', 'coinbase', 'kraken', 'bitfinex', 
        'huobi', 'kucoin', 'okex', 'bybit', 'ftx', 'gate', 'lbank2'
    ]
    return exchange_name.lower() in supported_exchanges
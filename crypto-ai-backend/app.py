from flask import Flask, request, jsonify
import os
from config import config
from models.database import db
from models.portfolio_analyzer import PortfolioAnalyzer
from utils.security import get_limiter, add_security_headers
from utils.logger import setup_logging, get_logger, RequestIDMiddleware
from utils.auth import init_jwt
from utils.encryption import init_encryption
from utils.error_handlers import init_error_handlers
from services.websocket_service import init_websocket
from services.email_service import init_mail

# Import blueprints
from routes import auth_bp, portfolio_bp, trading_bp, admin_bp, websocket_bp, charts_bp, chart_bp
from routes.password_reset import password_reset_bp

# Initialize Flask app with configuration
app = Flask(__name__, static_folder='static', static_url_path='/static')

# Load configuration based on environment
env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[env])

# Initialize logging
setup_logging(app)
logger = get_logger(__name__)

# CORS handling based on environment configuration
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    allowed_origins = app.config.get('CORS_ORIGINS', [])
    
    # In production, only allow specific origins
    if app.config.get('ENV') == 'production':
        if origin and (origin in allowed_origins or '*' in allowed_origins):
            response.headers['Access-Control-Allow-Origin'] = origin
        elif allowed_origins and allowed_origins[0] != '*':
            # Set to first allowed origin if current origin not allowed
            response.headers['Access-Control-Allow-Origin'] = allowed_origins[0]
    else:
        # Development mode - be more permissive
        response.headers['Access-Control-Allow-Origin'] = origin or '*'
    
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,Accept,Origin,X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    # Add security headers
    return add_security_headers(response)

# Handle preflight OPTIONS requests
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'status': 'OK'})
        origin = request.headers.get('Origin')
        allowed_origins = app.config.get('CORS_ORIGINS', [])
        
        if app.config.get('ENV') == 'production':
            if origin and (origin in allowed_origins or '*' in allowed_origins):
                response.headers['Access-Control-Allow-Origin'] = origin
            elif allowed_origins and allowed_origins[0] != '*':
                response.headers['Access-Control-Allow-Origin'] = allowed_origins[0]
        else:
            response.headers['Access-Control-Allow-Origin'] = origin or '*'
            
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,Accept,Origin,X-Requested-With'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response

# Initialize database
db.init_app(app)

# Initialize JWT authentication
jwt = init_jwt(app)

# Initialize encryption
init_encryption(app)

# Initialize error handlers
init_error_handlers(app)

# Initialize rate limiter
limiter = get_limiter()
limiter.init_app(app)

# Add request ID middleware
app.wsgi_app = RequestIDMiddleware(app.wsgi_app)

# Initialize services
portfolio_analyzer = PortfolioAnalyzer()
app.config['portfolio_analyzer'] = portfolio_analyzer

# Initialize WebSocket
socketio, price_service = init_websocket(app)

# Initialize Flask-Mail
init_mail(app)

# Store blacklisted tokens in app context (in production, use Redis)
app.config['blacklisted_tokens'] = set()

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(portfolio_bp)
app.register_blueprint(trading_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(websocket_bp)
app.register_blueprint(charts_bp)
app.register_blueprint(chart_bp)
app.register_blueprint(password_reset_bp)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Use SocketIO run instead of app.run for WebSocket support
    socketio.run(
        app,
        debug=app.config['DEBUG'],
        host=app.config['HOST'],
        port=app.config['PORT'],
        allow_unsafe_werkzeug=True
    )
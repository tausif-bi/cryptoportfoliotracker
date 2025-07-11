from flask import Blueprint, jsonify, current_app
from sqlalchemy import text
from utils.auth import admin_required
from utils.security import get_limiter, require_valid_request
from utils.exceptions import handle_exceptions
from utils.logger import get_logger
from utils.migration import run_migration
from models.database import db, User, Portfolio, Trade, Holding

logger = get_logger(__name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')
limiter = get_limiter()

@admin_bp.route('/migrate-data', methods=['POST'])
@limiter.limit("1 per minute")
@require_valid_request
@admin_required
@handle_exceptions(logger)
def migrate_data_endpoint():
    """Migrate data from JSON files to database"""
    logger.info("Starting data migration via API endpoint")
    
    try:
        result = run_migration(current_app)
        logger.info("Data migration completed successfully")
        return jsonify({
            'success': True,
            'message': 'Data migration completed successfully',
            'details': result
        })
    except Exception as e:
        logger.error(f"Data migration failed: {str(e)}")
        raise e

@admin_bp.route('/db-status', methods=['GET'])
@limiter.limit("10 per minute")
@require_valid_request
@admin_required
@handle_exceptions(logger)
def database_status():
    """Get database status and statistics"""
    try:
        # Check database connection
        db.session.execute(text('SELECT 1'))
        
        # Get table counts
        stats = {
            'users': User.query.count(),
            'portfolios': Portfolio.query.count(),
            'trades': Trade.query.count(),
            'holdings': Holding.query.count()
        }
        
        return jsonify({
            'success': True,
            'database_connected': True,
            'statistics': stats
        })
    except Exception as e:
        logger.error(f"Database status check failed: {str(e)}")
        return jsonify({
            'success': False,
            'database_connected': False,
            'error': str(e)
        }), 500
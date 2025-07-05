#!/usr/bin/env python3
"""
Database initialization script
Creates tables and runs initial migration if needed
"""
import os
import sys
from flask import Flask
from config import config
from models.database import db, init_db
from utils.migration import run_migration
from utils.logger import setup_logging, get_logger

def create_app():
    """Create Flask app for database operations"""
    app = Flask(__name__)
    
    # Load configuration
    env = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[env])
    
    # Initialize database
    init_db(app)
    
    # Setup logging
    setup_logging(app)
    
    return app

def init_database():
    """Initialize database with all tables"""
    app = create_app()
    logger = get_logger(__name__)
    
    with app.app_context():
        try:
            logger.info("Creating database tables...")
            
            # Create all tables
            db.create_all()
            
            logger.info("Database tables created successfully")
            
            # Check if we need to run migration
            from models.database import User, Trade
            
            user_count = User.query.count()
            trade_count = Trade.query.count()
            
            logger.info(f"Current database state: {user_count} users, {trade_count} trades")
            
            # If no data exists, try to migrate from JSON files
            if user_count == 0 and trade_count == 0:
                logger.info("No existing data found. Checking for JSON files to migrate...")
                
                # Check if JSON files exist
                json_files = ['simulated_trades.json', 'simulated_trades.csv']
                json_exists = any(os.path.exists(f) for f in json_files)
                
                if json_exists:
                    logger.info("Found JSON files. Starting migration...")
                    try:
                        result = run_migration(app)
                        logger.info(f"Migration completed: {result}")
                    except Exception as e:
                        logger.error(f"Migration failed: {str(e)}")
                        print(f"Warning: Migration failed - {str(e)}")
                else:
                    logger.info("No JSON files found to migrate")
            else:
                logger.info("Existing data found. Skipping migration.")
            
            print("✅ Database initialization completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            print(f"❌ Database initialization failed: {str(e)}")
            return False

def reset_database():
    """Reset database by dropping and recreating all tables"""
    app = create_app()
    logger = get_logger(__name__)
    
    with app.app_context():
        try:
            logger.warning("Resetting database - dropping all tables")
            
            # Drop all tables
            db.drop_all()
            
            # Recreate tables
            db.create_all()
            
            logger.info("Database reset completed")
            print("✅ Database reset completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Database reset failed: {str(e)}")
            print(f"❌ Database reset failed: {str(e)}")
            return False

def check_database_connection():
    """Check if database connection is working"""
    app = create_app()
    logger = get_logger(__name__)
    
    with app.app_context():
        try:
            from sqlalchemy import text
            result = db.session.execute(text('SELECT 1'))
            logger.info("Database connection successful")
            print("✅ Database connection is working!")
            return True
            
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            print(f"❌ Database connection failed: {str(e)}")
            print("\nTroubleshooting:")
            print("1. Make sure PostgreSQL is running")
            print("2. Check your .env file database configuration")
            print("3. Verify database credentials and permissions")
            return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'init':
            init_database()
        elif command == 'reset':
            confirm = input("Are you sure you want to reset the database? This will delete all data. (yes/no): ")
            if confirm.lower() == 'yes':
                reset_database()
            else:
                print("Database reset cancelled.")
        elif command == 'check':
            check_database_connection()
        elif command == 'migrate':
            app = create_app()
            with app.app_context():
                try:
                    result = run_migration(app)
                    print(f"✅ Migration completed: {result}")
                except Exception as e:
                    print(f"❌ Migration failed: {str(e)}")
        else:
            print(f"Unknown command: {command}")
            print("Available commands:")
            print("  init    - Initialize database and migrate data")
            print("  reset   - Reset database (delete all data)")
            print("  check   - Check database connection")
            print("  migrate - Run data migration from JSON files")
    else:
        print("Usage: python init_db.py <command>")
        print("Commands:")
        print("  init    - Initialize database and migrate data")
        print("  reset   - Reset database (delete all data)")
        print("  check   - Check database connection")
        print("  migrate - Run data migration from JSON files")
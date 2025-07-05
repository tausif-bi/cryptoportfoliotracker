#!/usr/bin/env python3
"""
Production startup script for Crypto Portfolio Tracker
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load production environment
env_file = Path('.env.production')
if env_file.exists():
    load_dotenv(env_file)
else:
    print("ERROR: .env.production file not found!")
    print("Please create it from .env.production.example")
    sys.exit(1)

# Validate required environment variables
required_vars = [
    'SECRET_KEY',
    'JWT_SECRET_KEY',
    'ENCRYPTION_KEY',
    'DB_PASSWORD',
    'CORS_ORIGINS'
]

missing_vars = []
for var in required_vars:
    if not os.environ.get(var) or os.environ.get(var).startswith('generate-'):
        missing_vars.append(var)

if missing_vars:
    print("ERROR: The following required environment variables are not set:")
    for var in missing_vars:
        print(f"  - {var}")
    print("\nPlease run 'python generate_keys.py' to generate secure keys")
    print("and update your .env.production file")
    sys.exit(1)

# Check for default/insecure values
if 'yourdomain.com' in os.environ.get('CORS_ORIGINS', ''):
    print("WARNING: CORS_ORIGINS still contains example domain")
    print("Please update it with your actual domain(s)")

# Set production environment
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = 'False'

# Import and run the app with gunicorn in production
if __name__ == '__main__':
    print("Starting Crypto Portfolio Tracker in PRODUCTION mode...")
    print(f"CORS Origins: {os.environ.get('CORS_ORIGINS')}")
    print(f"Database: {os.environ.get('DB_TYPE', 'sqlite')}")
    
    # For production, use gunicorn
    workers = int(os.environ.get('GUNICORN_WORKERS', 4))
    bind = f"{os.environ.get('HOST', '0.0.0.0')}:{os.environ.get('PORT', 5000)}"
    
    os.system(f"gunicorn -w {workers} -b {bind} --timeout 120 app:app")
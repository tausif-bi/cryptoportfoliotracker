#!/bin/bash
# Setup script for adding portfoliq.xyz to existing server

echo "=== Setting up Portfoliq.xyz on existing server ==="

# Navigate to portfoliq directory
cd /var/www/portfoliq/crypto-ai-backend

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn eventlet psycopg2-binary

# Create production .env file
cat > .env <<'EOF'
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-unique-secret-key-here
JWT_SECRET_KEY=your-unique-jwt-secret-here
ENCRYPTION_KEY=your-unique-encryption-key-here

# Database (new database for portfoliq)
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=portfoliq_db
DB_USER=portfoliq_user
DB_PASSWORD=your_secure_password_here

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=Portfoliq <your-email@gmail.com>

# CORS
CORS_ORIGINS=https://portfoliq.xyz,https://www.portfoliq.xyz,http://localhost:3000

# Other
DEFAULT_EXCHANGE=binance
LOG_LEVEL=INFO
PORT=5001
EOF

echo "Backend setup complete! Don't forget to:"
echo "1. Update the .env file with your actual credentials"
echo "2. Create the PostgreSQL database"
echo "3. Run: python init_db.py"
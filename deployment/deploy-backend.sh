#!/bin/bash
# Deploy Backend Script

cd /var/www/portfoliq

# Clone repository (first time only)
# git clone https://github.com/YOUR_USERNAME/cryptoportfoliotracker.git .

# Navigate to backend
cd crypto-ai-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn eventlet psycopg2-binary

# Create production .env file
cat > .env <<EOF
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
ENCRYPTION_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# Database
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crypto_portfolio
DB_USER=portfoliq
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
EOF

# Initialize database
python init_db.py

echo "Backend setup complete!"
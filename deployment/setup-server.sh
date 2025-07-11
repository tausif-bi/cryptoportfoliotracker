#!/bin/bash
# Contabo VPS Setup Script for Portfoliq.xyz

echo "=== Starting Portfoliq.xyz Server Setup ==="

# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y python3-pip python3-venv python3-dev build-essential \
    postgresql postgresql-contrib nginx git supervisor \
    certbot python3-certbot-nginx ufw curl

# Install Node.js for frontend
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Create app user
sudo useradd -m -s /bin/bash portfoliq
sudo usermod -aG sudo portfoliq

# Setup firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5000/tcp  # For development
sudo ufw --force enable

# Create app directories
sudo mkdir -p /var/www/portfoliq
sudo mkdir -p /var/log/portfoliq
sudo chown -R portfoliq:portfoliq /var/www/portfoliq
sudo chown -R portfoliq:portfoliq /var/log/portfoliq

# Setup PostgreSQL
sudo -u postgres psql <<EOF
CREATE DATABASE crypto_portfolio;
CREATE USER portfoliq WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE crypto_portfolio TO portfoliq;
EOF

echo "=== Basic setup complete! ==="
echo "Next: Clone your repository and set up the application"
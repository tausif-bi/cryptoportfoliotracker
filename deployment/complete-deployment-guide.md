# Complete Contabo VPS Deployment Guide for Portfoliq.xyz

## Prerequisites
- Contabo VPS with Ubuntu 22.04
- Domain (portfoliq.xyz) from GoDaddy
- GitHub repository with your code

## Step 1: Initial Login to Contabo VPS
```bash
# SSH into your server (Contabo will email you the IP and password)
ssh root@YOUR_SERVER_IP

# Change root password immediately
passwd
```

## Step 2: Run Initial Setup
```bash
# Download and run setup script
wget https://raw.githubusercontent.com/YOUR_USERNAME/cryptoportfoliotracker/main/deployment/setup-server.sh
chmod +x setup-server.sh
./setup-server.sh
```

## Step 3: Clone Your Repository
```bash
# Switch to app user
su - portfoliq

# Clone your code
cd /var/www/portfoliq
git clone https://github.com/YOUR_USERNAME/cryptoportfoliotracker.git .
```

## Step 4: Deploy Backend
```bash
cd /var/www/portfoliq/crypto-ai-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Edit .env file with your settings
nano .env
# Add your database password, email settings, etc.

# Initialize database
python init_db.py
```

## Step 5: Setup Nginx
```bash
# Copy nginx config
sudo cp /var/www/portfoliq/deployment/nginx-config.conf /etc/nginx/sites-available/portfoliq
sudo ln -s /etc/nginx/sites-available/portfoliq /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test nginx config
sudo nginx -t
sudo systemctl restart nginx
```

## Step 6: Setup Supervisor
```bash
# Copy supervisor config
sudo cp /var/www/portfoliq/deployment/supervisor-config.conf /etc/supervisor/conf.d/portfoliq.conf
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start portfoliq:*
```

## Step 7: Point Domain to Server

### In GoDaddy DNS Management:
Add these records:

```
Type: A
Name: @
Value: YOUR_CONTABO_IP
TTL: 600

Type: A  
Name: www
Value: YOUR_CONTABO_IP
TTL: 600

Type: A
Name: api
Value: YOUR_CONTABO_IP
TTL: 600
```

## Step 8: Setup SSL with Let's Encrypt
```bash
# Wait for DNS to propagate (5-30 minutes)
# Then run:
sudo certbot --nginx -d portfoliq.xyz -d www.portfoliq.xyz -d api.portfoliq.xyz
```

## Step 9: Build and Deploy Frontend
```bash
cd /var/www/portfoliq/crypto-portfolio

# Install dependencies
npm install

# Build for web
npx expo build:web

# The built files will be in web-build/ directory
# Nginx is already configured to serve them
```

## Step 10: Final Steps
```bash
# Restart all services
sudo systemctl restart nginx
sudo supervisorctl restart all

# Check logs
sudo tail -f /var/log/portfoliq/backend.log
sudo tail -f /var/log/nginx/error.log
```

## Your URLs:
- Frontend: https://portfoliq.xyz
- API: https://portfoliq.xyz/api
- API Direct: https://api.portfoliq.xyz

## Maintenance Commands:
```bash
# View backend logs
sudo supervisorctl tail -f portfoliq-backend

# Restart backend
sudo supervisorctl restart portfoliq-backend

# Update code
cd /var/www/portfoliq
git pull
sudo supervisorctl restart all

# Database backup
pg_dump -U portfoliq crypto_portfolio > backup.sql
```

## Security Checklist:
- [ ] Changed root password
- [ ] Created non-root user
- [ ] Enabled firewall (ufw)
- [ ] SSL certificates installed
- [ ] Database has strong password
- [ ] .env file has secure keys
- [ ] Email credentials configured

## Monitoring:
- Use `htop` to monitor resources
- Check logs regularly
- Set up UptimeRobot for free monitoring
- Consider adding Sentry for error tracking
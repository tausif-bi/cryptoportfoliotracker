# Adding Portfoliq.xyz to Your Existing Contabo Server

## Step 1: Check Current Setup
```bash
# SSH into your existing server
ssh root@YOUR_SERVER_IP

# Check what's currently running
sudo nginx -t
ls /etc/nginx/sites-enabled/
sudo supervisorctl status
```

## Step 2: Create Directory for New Site
```bash
# Create directory structure
sudo mkdir -p /var/www/portfoliq
sudo chown -R $USER:$USER /var/www/portfoliq
```

## Step 3: Deploy Your App
```bash
cd /var/www/portfoliq
git clone https://github.com/YOUR_USERNAME/cryptoportfoliotracker.git .

# Set up backend
cd crypto-ai-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create separate database for portfoliq
sudo -u postgres psql
CREATE DATABASE portfoliq_db;
CREATE USER portfoliq_user WITH PASSWORD 'new_secure_password';
GRANT ALL PRIVILEGES ON DATABASE portfoliq_db TO portfoliq_user;
\q
```

## Step 4: Configure Nginx for Multiple Sites

Create new Nginx config for portfoliq.xyz:
```bash
sudo nano /etc/nginx/sites-available/portfoliq
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name portfoliq.xyz www.portfoliq.xyz;
    
    # Frontend
    root /var/www/portfoliq/crypto-portfolio/web-build;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy
    location /api {
        proxy_pass http://127.0.0.1:5001;  # Note: Different port!
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/portfoliq /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Step 5: Run Backend on Different Port

Create supervisor config for portfoliq:
```bash
sudo nano /etc/supervisor/conf.d/portfoliq.conf
```

```ini
[program:portfoliq-backend]
command=/var/www/portfoliq/crypto-ai-backend/venv/bin/gunicorn --worker-class eventlet -w 1 --bind 127.0.0.1:5001 app:app
directory=/var/www/portfoliq/crypto-ai-backend
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/portfoliq/backend.log
environment=PATH="/var/www/portfoliq/crypto-ai-backend/venv/bin"
```

Start it:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start portfoliq-backend
```

## Step 6: Point Domain to Your Server

In GoDaddy DNS:
```
Type: A
Name: @
Value: YOUR_CONTABO_SERVER_IP (same as test domain)
TTL: 600

Type: A
Name: www
Value: YOUR_CONTABO_SERVER_IP
TTL: 600
```

## Step 7: Setup SSL for New Domain
```bash
sudo certbot --nginx -d portfoliq.xyz -d www.portfoliq.xyz
```

## Managing Multiple Sites:

### Check what's running:
```bash
# See all sites
ls /etc/nginx/sites-enabled/

# See all backend processes
sudo supervisorctl status

# Check ports in use
sudo netstat -tlnp | grep python
```

### Your server will have:
- Test domain on port 5000 → testdomain.com
- Portfoliq on port 5001 → portfoliq.xyz
- Both using same Nginx (port 80/443)
- Both can use same PostgreSQL (different databases)

### Resource Check:
```bash
# Check if server can handle both
htop  # Check CPU and RAM usage
df -h  # Check disk space
```

If your Contabo VPS has 4GB+ RAM, you can easily run 3-4 small apps!
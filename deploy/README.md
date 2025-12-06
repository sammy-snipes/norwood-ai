# Norwood AI - Production Deployment Guide

Complete guide for deploying Norwood AI on AWS EC2 with HTTPS.

## Prerequisites

- AWS EC2 instance running Ubuntu 22.04+
- Domain `norwood-ai.com` pointing to your EC2 IP address
- SSH access to the EC2 instance
- Security Group allowing ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)

## Quick Start

### 1. Connect to Your EC2 Instance

```bash
ssh -i your-key.pem ubuntu@norwood-ai.com
```

### 2. Clone Your Repository

```bash
cd ~
git clone <your-repo-url> norwood-ai
cd norwood-ai
```

### 3. Setup Environment Variables

```bash
cp .env.example .env
nano .env
```

Update these critical values:
```bash
ENV=prod
DATABASE_URL=postgresql://user:pass@localhost:5432/norwood
ANTHROPIC_API_KEY=your-key-here
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
JWT_SECRET_KEY=generate-a-secure-random-key
STRIPE_SECRET_KEY=your-stripe-key
STRIPE_PUBLISHABLE_KEY=your-stripe-pub-key
STRIPE_PREMIUM_PRICE_ID=your-price-id
```

### 4. Setup Database

```bash
# Create PostgreSQL database and user
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE norwood;
CREATE USER norwooduser WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE norwood TO norwooduser;
\q

# Run migrations
psql "$DATABASE_URL" -f migrations/2024_12_4_1_create_users.sql
psql "$DATABASE_URL" -f migrations/2024_12_4_2_create_analyses.sql
psql "$DATABASE_URL" -f migrations/2024_12_4_3_create_payments.sql
```

### 5. Run Setup Scripts

```bash
cd ~/norwood-ai/deploy

# Step 1: Setup services (FastAPI + Celery)
./setup-services.sh

# Step 2: Setup HTTPS (Nginx + Let's Encrypt)
./setup-https.sh
```

### 6. Verify Everything Works

```bash
# Check services are running
sudo systemctl status norwood-ai
sudo systemctl status norwood-celery
sudo systemctl status nginx

# Test HTTPS
curl https://norwood-ai.com/health
```

## Manual Steps (Alternative to Scripts)

### Install Dependencies

```bash
sudo apt update
sudo apt install -y python3.11 nginx certbot python3-certbot-nginx \
    postgresql redis-server nodejs npm
```

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

### Setup Nginx

```bash
sudo cp ~/norwood-ai/deploy/nginx.conf /etc/nginx/sites-available/norwood-ai
sudo ln -s /etc/nginx/sites-available/norwood-ai /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### Get SSL Certificate

```bash
sudo certbot --nginx -d norwood-ai.com -d www.norwood-ai.com
```

### Setup Systemd Services

```bash
sudo cp ~/norwood-ai/deploy/norwood-ai.service /etc/systemd/system/
sudo cp ~/norwood-ai/deploy/norwood-celery.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable norwood-ai norwood-celery
sudo systemctl start norwood-ai norwood-celery
```

## Useful Commands

### Service Management

```bash
# Restart app after code changes
sudo systemctl restart norwood-ai

# View app logs
sudo journalctl -u norwood-ai -f

# View Celery logs
sudo journalctl -u norwood-celery -f

# Check service status
sudo systemctl status norwood-ai
```

### Deployment Updates

```bash
cd ~/norwood-ai
git pull origin main
cd frontend && npm run build && cd ..
sudo systemctl restart norwood-ai
sudo systemctl restart norwood-celery
```

### SSL Certificate Renewal

Certificates auto-renew via systemd timer. To manually renew:

```bash
sudo certbot renew
sudo systemctl reload nginx
```

### Database Backups

```bash
# Backup
pg_dump "$DATABASE_URL" > backup-$(date +%Y%m%d).sql

# Restore
psql "$DATABASE_URL" < backup-20241205.sql
```

## Security Checklist

- [ ] Changed `JWT_SECRET_KEY` to a secure random value
- [ ] Updated all API keys in `.env`
- [ ] Configured PostgreSQL with strong password
- [ ] Enabled AWS Security Group rules (80, 443, 22 only)
- [ ] Setup AWS S3 bucket for image storage
- [ ] Configured Stripe webhook URL to use HTTPS
- [ ] Updated Google OAuth redirect URLs to HTTPS
- [ ] SSL certificate auto-renewal is enabled

## Troubleshooting

### App won't start

```bash
# Check logs
sudo journalctl -u norwood-ai -n 100

# Common issues:
# - Missing .env file
# - Database connection failed
# - Port 8000 already in use
```

### Nginx errors

```bash
# Test config
sudo nginx -t

# Check logs
sudo tail -f /var/log/nginx/error.log
```

### SSL certificate issues

```bash
# Check cert status
sudo certbot certificates

# Renew manually
sudo certbot renew --force-renewal
```

### Can't connect to database

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql "$DATABASE_URL" -c "SELECT 1;"
```

## Support

For issues, check:
1. Service logs: `sudo journalctl -u norwood-ai -f`
2. Nginx logs: `/var/log/nginx/error.log`
3. Application logs in systemd journal

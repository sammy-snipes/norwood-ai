# 🚀 Quick Start - HTTPS Setup

## Before You Start

1. **Make sure your domain points to your EC2 IP:**
   ```bash
   dig norwood-ai.com +short
   # Should return your EC2 public IP
   ```

2. **Security Group must allow:**
   - Port 22 (SSH)
   - Port 80 (HTTP)
   - Port 443 (HTTPS)

## Step-by-Step Setup

### 1️⃣ SSH into your EC2 instance
```bash
ssh -i your-key.pem ubuntu@<your-ec2-ip>
```

### 2️⃣ Clone your repo
```bash
cd ~
git clone <your-repo-url> norwood-ai
cd norwood-ai
```

### 3️⃣ Setup environment file
```bash
cp .env.example .env
nano .env
```

**Critical settings to update:**
```bash
ENV=prod
ANTHROPIC_API_KEY=sk-ant-...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
DATABASE_URL=postgresql://...
```

### 4️⃣ Setup database
```bash
# Create database
sudo -u postgres psql -c "CREATE DATABASE norwood;"
sudo -u postgres psql -c "CREATE USER norwooduser WITH PASSWORD 'yourpassword';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE norwood TO norwooduser;"

# Update DATABASE_URL in .env with the password you just set
nano .env

# Run migrations
psql "$DATABASE_URL" -f migrations/2024_12_4_1_create_users.sql
psql "$DATABASE_URL" -f migrations/2024_12_4_2_create_analyses.sql
psql "$DATABASE_URL" -f migrations/2024_12_4_3_create_payments.sql
```

### 5️⃣ Run setup scripts
```bash
cd ~/norwood-ai/deploy

# Make scripts executable (if not already)
chmod +x *.sh

# Setup app and celery services
./setup-services.sh

# Setup HTTPS with Let's Encrypt
./setup-https.sh
```

### 6️⃣ Verify it works
```bash
# Check all services are running
sudo systemctl status norwood-ai
sudo systemctl status norwood-celery
sudo systemctl status nginx

# Test HTTPS endpoint
curl https://norwood-ai.com/health
```

### 7️⃣ Update Stripe webhooks
1. Go to Stripe Dashboard → Webhooks
2. Update webhook URL to: `https://norwood-ai.com/api/stripe/webhook`
3. Test the webhook

### 8️⃣ Update Google OAuth
1. Go to Google Cloud Console → APIs & Credentials
2. Update authorized redirect URIs to: `https://norwood-ai.com/auth/callback`

## Done! 🎉

Your app is now running with HTTPS at: **https://norwood-ai.com**

## Common Issues

**Q: "App not starting"**
```bash
sudo journalctl -u norwood-ai -f  # Check logs
```

**Q: "502 Bad Gateway"**
```bash
# App probably not running on port 8000
sudo systemctl restart norwood-ai
```

**Q: "SSL certificate failed"**
```bash
# Make sure ports 80 and 443 are open in security group
# Make sure domain points to correct IP
dig norwood-ai.com +short
```

## Updating Your App

```bash
cd ~/norwood-ai
git pull origin main
cd frontend && npm run build && cd ..
sudo systemctl restart norwood-ai
sudo systemctl restart norwood-celery
```

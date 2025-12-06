#!/bin/bash
set -e

echo "🚀 Norwood AI - HTTPS Setup Script"
echo "===================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo "❌ Please run as ubuntu user (not root)"
   exit 1
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install required packages
echo "📦 Installing Nginx, Certbot, and dependencies..."
sudo apt install -y nginx certbot python3-certbot-nginx

# Create certbot directory
sudo mkdir -p /var/www/certbot

# Copy Nginx configuration
echo "⚙️  Configuring Nginx..."
sudo cp ~/norwood-ai/deploy/nginx.conf /etc/nginx/sites-available/norwood-ai

# Remove default site and enable our site
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/norwood-ai /etc/nginx/sites-enabled/

# Test Nginx configuration
echo "✅ Testing Nginx configuration..."
sudo nginx -t

# Restart Nginx
echo "🔄 Restarting Nginx..."
sudo systemctl restart nginx
sudo systemctl enable nginx

# Check if app is running on port 8000
echo "🔍 Checking if app is running on port 8000..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "⚠️  WARNING: App doesn't seem to be running on port 8000"
    echo "   Please start your app first with systemd services"
    echo "   Run: ./setup-services.sh"
fi

# Get SSL certificate
echo ""
echo "🔐 Obtaining SSL certificate from Let's Encrypt..."
echo "   You'll be prompted to enter your email and agree to terms."
echo ""
sudo certbot --nginx -d norwood-ai.com -d www.norwood-ai.com

# Setup auto-renewal
echo "⏰ Setting up SSL certificate auto-renewal..."
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Test renewal
echo "🧪 Testing SSL renewal process..."
sudo certbot renew --dry-run

echo ""
echo "✅ HTTPS setup complete!"
echo ""
echo "🌐 Your site should now be accessible at:"
echo "   https://norwood-ai.com"
echo ""
echo "🔒 SSL certificate will auto-renew every 60 days"
echo ""
echo "📝 Next steps:"
echo "   1. Update your .env file: ENV=prod"
echo "   2. Update Stripe webhook URL to use https://"
echo "   3. Test your site at https://norwood-ai.com"
echo ""

#!/bin/bash
set -e

echo "🚀 Norwood AI - Service Setup Script"
echo "====================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo "❌ Please run as ubuntu user (not root)"
   exit 1
fi

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib redis-server

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.bashrc
fi

# Navigate to project directory
cd ~/norwood-ai

# Install Python dependencies
echo "📦 Installing Python dependencies..."
uv sync

# Build frontend
echo "🏗️  Building frontend..."
cd frontend
npm install
npm run build
cd ..

# Setup systemd services
echo "⚙️  Setting up systemd services..."
sudo cp ~/norwood-ai/deploy/norwood-ai.service /etc/systemd/system/
sudo cp ~/norwood-ai/deploy/norwood-celery.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start Redis
echo "🔄 Starting Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Enable and start PostgreSQL
echo "🔄 Starting PostgreSQL..."
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Start services
echo "🚀 Starting Norwood AI services..."
sudo systemctl enable norwood-ai
sudo systemctl start norwood-ai

sudo systemctl enable norwood-celery
sudo systemctl start norwood-celery

# Check service status
echo ""
echo "📊 Service Status:"
echo "=================="
sudo systemctl status norwood-ai --no-pager | head -15
echo ""
sudo systemctl status norwood-celery --no-pager | head -15

echo ""
echo "✅ Services setup complete!"
echo ""
echo "🔧 Useful commands:"
echo "   sudo systemctl status norwood-ai     # Check app status"
echo "   sudo systemctl status norwood-celery # Check celery status"
echo "   sudo systemctl restart norwood-ai    # Restart app"
echo "   sudo journalctl -u norwood-ai -f     # View app logs"
echo ""
echo "📝 Next step: Run ./setup-https.sh to enable HTTPS"
echo ""

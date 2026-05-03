#!/bin/bash
# =============================================================================
# GutBot — EC2 Deployment Script
# =============================================================================
# Run this ONCE on your EC2 instance after uploading the project.
# It copies all config files to their correct system locations,
# sets up log directories, enables services, and starts everything.
#
# Prerequisites (must be done before running this):
#   1. Project uploaded to /home/ubuntu/gutbot/
#   2. backend/.env filled with real credentials (cp .env.example .env)
#   3. Python venv created and requirements installed (see EC2_SETUP_GUIDE.md)
#   4. Frontend built: cd frontend && npm run build
#   5. server_name set in ec2-files/nginx-gutbot (replace YOUR_EC2_IP_OR_DOMAIN)
#   6. MemoryMax in ec2-files/gutbot.service matches your instance RAM
#
# Usage:
#   cd /home/ubuntu/gutbot
#   chmod +x ec2-files/deploy.sh
#   ./ec2-files/deploy.sh
# =============================================================================

set -e   # Exit immediately on any error

# ── Colour output ─────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# ── Guard: must run as ubuntu from /home/ubuntu/gutbot ────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ "$(pwd)" != "$PROJECT_DIR" ]; then
    fail "Run this script from the project root: cd $PROJECT_DIR && ./ec2-files/deploy.sh"
fi

echo ""
echo "=============================================="
echo "  GutBot — EC2 Deployment"
echo "  Project: $PROJECT_DIR"
echo "=============================================="
echo ""

# ── 1. Pre-flight checks ──────────────────────────────────────────────────────
echo "[1/9] Running pre-flight checks..."

# .env must exist and have credentials filled in
if [ ! -f "backend/.env" ]; then
    fail "backend/.env not found. Run: cp backend/.env.example backend/.env  then fill in your credentials."
fi
if grep -q "YOUR_AWS_ACCESS_KEY_ID" backend/.env; then
    fail "backend/.env still has placeholder credentials. Open it and fill in your real AWS keys."
fi

# nginx-gutbot must have a real server_name
if grep -q "YOUR_EC2_IP_OR_DOMAIN" ec2-files/nginx-gutbot; then
    fail "ec2-files/nginx-gutbot still has YOUR_EC2_IP_OR_DOMAIN. Edit it and set your EC2 IP or domain."
fi

# venv must exist
if [ ! -f "backend/venv/bin/gunicorn" ]; then
    fail "Gunicorn not found. Set up venv first: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && pip install gevent"
fi

# Frontend dist must exist
if [ ! -d "frontend/dist" ]; then
    warn "frontend/dist not found — frontend will NOT be served. Build it: cd frontend && npm install && npm run build"
fi

ok "Pre-flight checks passed"

# ── 2. Create log directories ─────────────────────────────────────────────────
echo "[2/9] Creating log directories..."
sudo mkdir -p /var/log/gutbot
sudo chown ubuntu:ubuntu /var/log/gutbot
ok "/var/log/gutbot created"

# ── 3. Install systemd service ────────────────────────────────────────────────
echo "[3/9] Installing systemd service..."
sudo cp ec2-files/gutbot.service /etc/systemd/system/gutbot.service
sudo chmod 644 /etc/systemd/system/gutbot.service
sudo systemctl daemon-reload
sudo systemctl enable gutbot
ok "gutbot.service installed and enabled"

# ── 4. Install Nginx main config ──────────────────────────────────────────────
echo "[4/9] Installing Nginx main config..."
# Back up the original nginx.conf if not already backed up
if [ ! -f "/etc/nginx/nginx.conf.original" ]; then
    sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.original
    ok "Original nginx.conf backed up to nginx.conf.original"
fi
sudo cp ec2-files/nginx.conf /etc/nginx/nginx.conf
ok "nginx.conf installed"

# ── 5. Install Nginx site config ──────────────────────────────────────────────
echo "[5/9] Installing Nginx site config..."
sudo cp ec2-files/nginx-gutbot /etc/nginx/sites-available/gutbot

# Enable gutbot site
sudo ln -sf /etc/nginx/sites-available/gutbot /etc/nginx/sites-enabled/gutbot

# Remove Nginx default site so it does not conflict
if [ -f /etc/nginx/sites-enabled/default ]; then
    sudo rm /etc/nginx/sites-enabled/default
    ok "Removed default Nginx site"
fi
ok "Nginx site config installed"

# ── 6. Test Nginx configuration ───────────────────────────────────────────────
echo "[6/9] Testing Nginx config syntax..."
sudo nginx -t || fail "Nginx config test failed. Check the error above and fix ec2-files/nginx-gutbot or ec2-files/nginx.conf"
ok "Nginx config syntax OK"

# ── 7. Protect .env file ─────────────────────────────────────────────────────
echo "[7/9] Securing .env permissions..."
chmod 600 backend/.env
ok ".env permissions set to 600 (owner read/write only)"

# ── 8. Start / Restart services ───────────────────────────────────────────────
echo "[8/9] Starting services..."

sudo systemctl restart gutbot
sudo systemctl enable nginx
sudo systemctl restart nginx

ok "gutbot service started"
ok "nginx restarted"

# ── 9. Verify ─────────────────────────────────────────────────────────────────
echo "[9/9] Verifying deployment..."
sleep 3   # Give Gunicorn a moment to finish loading the embedding model

# Check if Gunicorn is listening on port 8000
if curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
       -X POST http://127.0.0.1:8000/documents \
       -H "Content-Type: application/json" \
       -d '{"conversationId":"deploy-check"}' | grep -q "200"; then
    ok "Backend responding on port 8000"
else
    warn "Backend did not respond in time. Check: sudo systemctl status gutbot"
fi

# Check Nginx is running
if sudo systemctl is-active --quiet nginx; then
    ok "Nginx is running"
else
    fail "Nginx failed to start. Check: sudo systemctl status nginx"
fi

echo ""
echo "=============================================="
echo -e "${GREEN}  Deployment complete!${NC}"
echo "=============================================="
echo ""
echo "  Backend service : sudo systemctl status gutbot"
echo "  Backend logs    : sudo tail -f /var/log/gutbot/error.log"
echo "  Nginx logs      : sudo tail -f /var/log/nginx/gutbot_error.log"
echo "  Live app logs   : sudo journalctl -u gutbot -f"
echo ""
echo "  To restart backend : sudo systemctl restart gutbot"
echo "  To reload Nginx    : sudo systemctl reload nginx"
echo ""

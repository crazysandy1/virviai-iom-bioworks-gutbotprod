# GutBot — EC2 Production Setup Guide

This guide takes you from a freshly launched EC2 instance to a publicly accessible, production-grade chatbot that serves 100 concurrent users without crashes or session mixing.

**Target:** Ubuntu 22.04 LTS on AWS EC2  
**Architecture:** Nginx (80/443) → Gunicorn (8000) → Flask app + FAISS  
**Concurrency model:** 1 Gunicorn worker with gevent (keeps session data isolated per user)

---

## Table of Contents

1. [Launch the EC2 Instance](#1-launch-the-ec2-instance)
2. [Connect to the Instance](#2-connect-to-the-instance)
3. [Initial Server Setup](#3-initial-server-setup)
4. [Install Python and Dependencies](#4-install-python-and-dependencies)
5. [Install Node.js (for frontend build)](#5-install-nodejs-for-frontend-build)
6. [Deploy the Application](#6-deploy-the-application)
7. [Configure Environment Variables](#7-configure-environment-variables)
8. [Build the Frontend](#8-build-the-frontend)
9. [Configure Gunicorn as a systemd Service](#9-configure-gunicorn-as-a-systemd-service)
10. [Configure Nginx](#10-configure-nginx)
11. [Configure the Firewall](#11-configure-the-firewall)
12. [Enable HTTPS with Let's Encrypt (Optional)](#12-enable-https-with-lets-encrypt-optional)
13. [Verify Multi-User Isolation](#13-verify-multi-user-isolation)
14. [Monitoring and Logs](#14-monitoring-and-logs)
15. [Updating the Application](#15-updating-the-application)
16. [Scaling Beyond 100 Users](#16-scaling-beyond-100-users)

---

## 1. Launch the EC2 Instance

### In the AWS Console: EC2 → Launch Instance

**AMI (Operating System):**
- Ubuntu Server 22.04 LTS (HVM), SSD Volume Type
- Architecture: 64-bit (x86)

**Instance type — choose based on expected load:**

| Instance | vCPU | RAM | Suitable for |
|---|---|---|---|
| t3.medium | 2 | 4 GB | Up to ~30 simultaneous users (minimum) |
| t3.large | 2 | 8 GB | Up to ~60 simultaneous users |
| t3.xlarge | 4 | 16 GB | Up to ~100 simultaneous users (recommended) |
| c5.xlarge | 4 | 8 GB | CPU-optimised, good for embedding workload |

> The embedding model (SentenceTransformers) and FAISS run in memory. For 100 users uploading PDFs concurrently, 8 GB RAM minimum is strongly recommended.

**Key pair:** Create or select an existing key pair. Save the `.pem` file securely — you cannot recover it.

**Network settings — Security Group (create new or edit existing):**

| Type | Protocol | Port | Source | Purpose |
|---|---|---|---|---|
| SSH | TCP | 22 | Your IP only | Admin access |
| HTTP | TCP | 80 | 0.0.0.0/0 | Public web access |
| HTTPS | TCP | 443 | 0.0.0.0/0 | Public HTTPS (optional) |

> Do NOT open port 8000 to the public. Gunicorn must only be accessible through Nginx.

**Storage:**
- Root volume: 30 GB GP3 (minimum; 50 GB recommended for logs + uploaded PDFs)

**Launch the instance** and note the **Public IPv4 address** (e.g., `54.123.45.67`).

---

## 2. Connect to the Instance

```bash
# On your local machine
chmod 400 your-key.pem

ssh -i your-key.pem ubuntu@54.123.45.67
```

If you have a domain name, point an A record to the IP before continuing (so Let's Encrypt works in step 12).

---

## 3. Initial Server Setup

```bash
# Update package lists and upgrade existing packages
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y git curl wget unzip build-essential software-properties-common

# Set timezone (change to match your region)
sudo timedatectl set-timezone Asia/Kolkata

# Verify
date
```

---

## 4. Install Python and Dependencies

```bash
# Install Python 3.10+ (Ubuntu 22.04 ships with 3.10)
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Verify
python3 --version   # should be 3.10.x or higher
pip3 --version
```

---

## 5. Install Node.js (for frontend build)

```bash
# Install Node.js 20 LTS via NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version    # v20.x.x
npm --version     # 10.x.x
```

---

## 6. Deploy the Application

> **Project structure note:** The backend and frontend are two separate repositories.
> On EC2 the frontend must live **inside** the backend directory at `gutbot/frontend/`
> so that Nginx can find the built static files at `gutbot/frontend/dist/`.

### Option A — Clone from Git (both repos)

```bash
cd /home/ubuntu

# 1. Clone the backend repo as "gutbot"
git clone https://github.com/YOUR_ORG/virviai-iom-bioworks-gutbotprod.git gutbot

# 2. Clone the frontend repo inside gutbot/
git clone https://github.com/YOUR_ORG/gutbot-frontend.git gutbot/frontend

cd /home/ubuntu/gutbot
```

### Option B — Upload via SCP (if no git remote)

```bash
# Run these on your local machine (adjust paths to match where your folders are)

# 1. Upload the backend repo
scp -i your-key.pem -r \
  "path/to/virviai-iom-bioworks-gutbotprod/." \
  ubuntu@54.123.45.67:/home/ubuntu/gutbot

# 2. Upload the frontend repo into gutbot/frontend/
scp -i your-key.pem -r \
  "path/to/frontend/." \
  ubuntu@54.123.45.67:/home/ubuntu/gutbot/frontend
```

After upload, verify the structure looks like this:

```
/home/ubuntu/gutbot/
├── backend/          ← Flask app, requirements.txt, .env
├── ec2-files/        ← Gunicorn/Nginx/systemd configs
├── frontend/         ← React source + node_modules (after npm install)
│   └── dist/         ← Built static files (after npm run build)
├── README.md
└── EC2_SETUP_GUIDE.md
```

### Set up Python virtual environment

```bash
cd /home/ubuntu/gutbot/backend

python3 -m venv venv
source venv/bin/activate

# Install all dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install gevent for concurrent request handling
pip install gevent
```

> **Note:** The first `pip install` downloads PyTorch and SentenceTransformers, which are large (~1.5 GB). This can take 5–10 minutes on a fresh instance.

---

## 7. Configure Environment Variables

```bash
cd /home/ubuntu/gutbot/backend

cp .env.example .env
nano .env
```

Fill in every value. The critical fields:

```env
# LLM Backend
LLM_BACKEND=bedrock

# AWS Bedrock
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=AKIA...YOUR_KEY...
AWS_SECRET_ACCESS_KEY=...YOUR_SECRET...
BEDROCK_MODEL_ID=anthropic.claude-haiku-4-5-20251001-v1:0

BEDROCK_MAX_TOKENS=512
BEDROCK_TEMPERATURE=0.2

# Deployment — IMPORTANT: change these two
FLASK_ENV=production
EC2_DOMAIN=54.123.45.67        # or gutbot.yourdomain.com if you have one
```

Save and close: `Ctrl+O`, `Enter`, `Ctrl+X`

**Protect the credentials file:**
```bash
chmod 600 /home/ubuntu/gutbot/backend/.env
```

---

## 8. Build the Frontend

```bash
cd /home/ubuntu/gutbot/frontend

npm install
npm run build
# Output: frontend/dist/
```

Nginx will serve these static files directly.

---

## 9. Configure Gunicorn as a systemd Service

The repository includes a ready-made config file for this. **Before running the commands below, open `ec2-files/gutbot.service` and set `MemoryMax` to match your instance RAM** (see the comment table inside the file).

```bash
# Edit MemoryMax for your instance (2G / 4G / 8G)
nano /home/ubuntu/gutbot/ec2-files/gutbot.service

# Install
sudo cp /home/ubuntu/gutbot/ec2-files/gutbot.service /etc/systemd/system/gutbot.service
sudo mkdir -p /var/log/gutbot && sudo chown ubuntu:ubuntu /var/log/gutbot
sudo systemctl daemon-reload
sudo systemctl enable gutbot
sudo systemctl start gutbot

# Verify
sudo systemctl status gutbot
```

You should see `Active: active (running)`. Quick test:

```bash
curl -s -X POST http://127.0.0.1:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test"}'
# Expected: {"documents": []}
```

**Key design decisions baked into `ec2-files/gutbot.service`:**
- `--workers 1` — mandatory. GutBot stores every user's FAISS index in process memory keyed by `conversationId`. Multiple workers (separate OS processes) would silently break sessions.
- `CPUQuota=75%` — caps Gunicorn's CPU so SSH and system processes always have headroom.
- `MemoryMax` — hard ceiling so an OOM event kills Gunicorn before it can kill `sshd`.
- `Restart=on-failure` + `WantedBy=multi-user.target` — auto-restarts on crash and auto-starts on every reboot.

See `ec2-files/gunicorn.conf.py` for the full Gunicorn configuration (concurrency, timeouts, memory-leak protection via `max_requests`).

---

## 10. Configure Nginx

The repository includes two ready-made Nginx files. **Before running the commands below, open `ec2-files/nginx-gutbot` and replace `YOUR_EC2_IP_OR_DOMAIN`** with your actual IP or domain.

```bash
# Install Nginx
sudo apt install -y nginx

# Edit server_name
nano /home/ubuntu/gutbot/ec2-files/nginx-gutbot
# Change:  server_name YOUR_EC2_IP_OR_DOMAIN;
# To:      server_name 54.123.45.67;   (or your domain)

# Install main Nginx config (backs up original automatically)
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.original
sudo cp /home/ubuntu/gutbot/ec2-files/nginx.conf /etc/nginx/nginx.conf

# Install site config
sudo cp /home/ubuntu/gutbot/ec2-files/nginx-gutbot /etc/nginx/sites-available/gutbot
sudo ln -sf /etc/nginx/sites-available/gutbot /etc/nginx/sites-enabled/gutbot
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl enable nginx
```

Open a browser: `http://YOUR_EC2_IP` — GutBot frontend should load. If you see 502, check `sudo systemctl status gutbot`.

**What `ec2-files/nginx.conf` does differently from Ubuntu's default:**
- `worker_processes 1` instead of `auto` — prevents Nginx from consuming all CPU cores under load, leaving cores free for SSH.
- `worker_connections 512` instead of the default 768 — conservative ceiling that keeps the system stable.
- Per-IP rate limiting on `/upload` (2 req/s) and `/chat` (10 req/s) — prevents any single user from flooding the server.
- `keepalive_timeout 30` — drops idle connections promptly to free slots for new users.
- `client_body_timeout 30s` — drops slow-upload attackers quickly.

---

## 11. Configure the Firewall

```bash
# Allow SSH (keep this — if you lock yourself out you cannot reconnect)
sudo ufw allow OpenSSH

# Allow web traffic
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Block everything else (including direct access to port 8000)
sudo ufw enable

# Verify
sudo ufw status
```

Expected output:
```
Status: active

To                         Action      From
--                         ------      ----
OpenSSH                    ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

---

## 12. Enable HTTPS with Let's Encrypt (Optional but Recommended)

Required if you have a domain name pointing to the instance. Skip if using a raw IP.

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate (replace with your domain)
sudo certbot --nginx -d gutbot.yourdomain.com

# Follow the prompts:
#   - Enter your email address
#   - Agree to terms
#   - Choose redirect (2) to force HTTPS

# Test auto-renewal
sudo certbot renew --dry-run
```

Certbot will automatically update your Nginx config to add HTTPS. Certificates auto-renew every 60 days.

---

## 13. Verify Multi-User Isolation

Run this test to confirm that two simultaneous sessions cannot see each other's data.

```bash
# Session A: upload a PDF
curl -X POST http://54.123.45.67/upload \
  -F "file=@/path/to/medical_report.pdf" \
  -F "conversationId=session-A"

# Session B: list documents — should be empty
curl -X POST http://54.123.45.67/documents \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"session-B"}'
# Expected: {"documents": []}

# Session A: list documents — should show the uploaded file
curl -X POST http://54.123.45.67/documents \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"session-A"}'
# Expected: {"documents": [{"filename": "medical_report.pdf", ...}]}

# Debug endpoint for detailed isolation report
curl -X POST http://54.123.45.67/debug/isolation-check \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"session-A"}'
```

---

## 14. Monitoring and Logs

### Check application status

```bash
sudo systemctl status gutbot
```

### Real-time backend logs

```bash
# Application logs
sudo tail -f /var/log/gutbot/error.log

# Access logs
sudo tail -f /var/log/gutbot/access.log
```

### Nginx logs

```bash
sudo tail -f /var/log/nginx/gutbot_error.log
sudo tail -f /var/log/nginx/gutbot_access.log
```

### System resource usage

```bash
# CPU and memory snapshot
top -u ubuntu

# Memory usage
free -h

# Disk space (uploads folder can grow)
df -h
du -sh /home/ubuntu/gutbot/backend/uploads/
```

### Monitor uploaded files (clean up periodically)

```bash
# See how much disk the uploads folder uses
du -sh /home/ubuntu/gutbot/backend/uploads/

# The uploads folder contains PDFs from all user sessions.
# Note: session data (FAISS indices) lives in process memory and is lost on restart.
# Uploaded PDF files persist on disk until manually removed.
# Add a cron job to clear old uploads:
crontab -e
# Add:  0 2 * * * find /home/ubuntu/gutbot/backend/uploads/ -name "*.pdf" -mtime +7 -delete
```

---

## 15. Updating the Application

### Deploy code changes

```bash
cd /home/ubuntu/gutbot

# Pull latest code (if using git)
git pull origin main

# Install any new Python dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Rebuild frontend if changed
cd ../frontend
npm install
npm run build

# Restart the backend service
sudo systemctl restart gutbot

# Verify
sudo systemctl status gutbot
```

### Zero-downtime note

The current architecture does not support true zero-downtime deploys (restarting Gunicorn clears all in-memory sessions). To minimise impact, restart during off-peak hours and notify users beforehand. Active conversations will need to re-upload their documents after a restart.

---

## 16. Scaling Beyond 100 Users

The single-worker design is intentional and correct for the current in-memory session store. If you need to scale further:

### Vertical scaling (easiest)
Upgrade the EC2 instance to a larger type (t3.xlarge → m5.2xlarge). More RAM means more concurrent FAISS indices in memory and faster embedding.

### Horizontal scaling (requires code change)
To run multiple Gunicorn workers or multiple EC2 instances:
1. Move `conversation_indices` from in-memory dict to **Redis** (using `redis-py` + `pickle` for FAISS serialisation)
2. Use Nginx upstream load balancing with `ip_hash` (sticky sessions) as a simpler alternative

### Gunicorn tuning for the current single-worker setup

```bash
# In /etc/systemd/system/gutbot.service, adjust:

# Increase concurrent connections (default 200):
--worker-connections 400

# Increase timeout for very large PDFs or slow LLM responses:
--timeout 180
```

After changes:
```bash
sudo systemctl daemon-reload
sudo systemctl restart gutbot
```

### Storage scaling
If uploaded PDF volume grows large, move `backend/uploads/` to S3:
1. Mount S3 bucket as filesystem with `s3fs-fuse`
2. Or refactor upload handler to stream directly to S3 using `boto3`

---

## Quick Reference

```bash
# Start / Stop / Restart backend
sudo systemctl start   gutbot
sudo systemctl stop    gutbot
sudo systemctl restart gutbot

# Check backend status
sudo systemctl status gutbot

# Live backend logs
sudo journalctl -u gutbot -f

# Reload Nginx after config change
sudo nginx -t && sudo systemctl reload nginx

# Check what is listening on ports
sudo ss -tlnp | grep -E '80|443|8000'
```

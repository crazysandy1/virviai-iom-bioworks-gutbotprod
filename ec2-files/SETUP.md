# EC2 Config Files — Setup Guide

This folder contains all production configuration files for deploying GutBot on Ubuntu EC2.

| File | Destination on EC2 | Purpose |
|---|---|---|
| `gunicorn.conf.py` | Referenced in-place by `gutbot.service` | Gunicorn worker, timeout, memory, logging settings |
| `gutbot.service` | `/etc/systemd/system/gutbot.service` | Systemd unit — runs Gunicorn on boot, auto-restarts on crash |
| `nginx.conf` | `/etc/nginx/nginx.conf` | Nginx main config — worker processes, rate limits, client limits |
| `nginx-gutbot` | `/etc/nginx/sites-available/gutbot` | Nginx site — routes frontend + proxies API to Gunicorn |
| `deploy.sh` | Run from project root | Copies all files above to the right places and starts everything |

---

## Before You Run `deploy.sh`

Complete these steps first (see [EC2_SETUP_GUIDE.md](../EC2_SETUP_GUIDE.md) for full detail):

### Step 1 — Set your instance type in `gutbot.service`

Open `ec2-files/gutbot.service` and change `MemoryMax` to match your instance RAM:

```ini
# t3.medium  (4 GB):
MemoryMax=2G

# t3.large   (8 GB):
MemoryMax=4G

# t3.xlarge  (16 GB):
MemoryMax=8G
```

### Step 2 — Set your IP or domain in `nginx-gutbot`

Open `ec2-files/nginx-gutbot` and replace `YOUR_EC2_IP_OR_DOMAIN`:

```nginx
# Raw IP example:
server_name 54.123.45.67;

# Domain example:
server_name gutbot.yourdomain.com;
```

### Step 3 — Fill in `backend/.env`

```bash
cd /home/ubuntu/gutbot/backend
cp .env.example .env
nano .env
# Fill in: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, BEDROCK_MODEL_ID
# Set:     FLASK_ENV=production
# Set:     EC2_DOMAIN=your-ip-or-domain
```

### Step 4 — Set up Python environment

```bash
cd /home/ubuntu/gutbot/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gevent        # Required for async worker class
```

### Step 5 — Build the frontend

```bash
cd /home/ubuntu/gutbot/frontend
npm install
npm run build
# Output goes to frontend/dist/ — Nginx serves this directly
```

---

## Run the Deployment Script

```bash
cd /home/ubuntu/gutbot
chmod +x ec2-files/deploy.sh
./ec2-files/deploy.sh
```

The script will:
1. Check all prerequisites (credentials filled, server_name set, venv ready)
2. Create `/var/log/gutbot/` log directory
3. Install and enable the systemd service
4. Install Nginx main config (backs up original first)
5. Install and enable the Nginx site config
6. Test Nginx syntax before reloading
7. Protect `.env` file permissions
8. Start Gunicorn and Nginx
9. Run a live health check and print status

---

## After Deployment

```bash
# Check everything is running
sudo systemctl status gutbot
sudo systemctl status nginx

# Live backend logs
sudo journalctl -u gutbot -f

# Verify session isolation (two separate conversations)
curl -X POST http://YOUR_IP/documents \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-A"}'
# → {"documents": []}  (empty, isolated from any other session)
```

---

## Auto-Start on Reboot

Both services are set to `WantedBy=multi-user.target` and `sudo systemctl enable` is run by `deploy.sh`. This means:

- EC2 instance reboot → Nginx starts → Gunicorn starts → GutBot is live
- Gunicorn crash → systemd restarts it within 5 seconds (`RestartSec=5`)
- SSH remains accessible under load because `CPUQuota=75%` and `MemoryMax` prevent Gunicorn from consuming all system resources

---

## Tuning for Your Instance

### worker_connections in `gunicorn.conf.py`

| Instance | RAM | worker_connections |
|---|---|---|
| t3.medium | 4 GB | 60 |
| t3.large | 8 GB | 100 |
| t3.xlarge | 16 GB | 150 |

After changing, restart: `sudo systemctl restart gutbot`

### worker_processes in `nginx.conf`

| Instance | vCPU | worker_processes |
|---|---|---|
| t3.medium / t3.large | 2 | 1 |
| t3.xlarge / c5.xlarge | 4 | 2 |

After changing: `sudo nginx -t && sudo systemctl reload nginx`

---

## Re-deploying After Code Changes

```bash
cd /home/ubuntu/gutbot

# Pull latest code
git pull origin main

# Rebuild frontend if it changed
cd frontend && npm install && npm run build && cd ..

# Restart backend (picks up code changes)
sudo systemctl restart gutbot

# Reload Nginx if nginx-gutbot changed
sudo cp ec2-files/nginx-gutbot /etc/nginx/sites-available/gutbot
sudo nginx -t && sudo systemctl reload nginx
```

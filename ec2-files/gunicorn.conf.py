# =============================================================================
# Gunicorn Configuration — GutBot Production
# =============================================================================
# Reference: https://docs.gunicorn.org/en/stable/settings.html
# Used by: ec2-files/gutbot.service  (ExecStart references this file)
# =============================================================================

# ── Socket ────────────────────────────────────────────────────────────────────
# Bind to localhost only — Nginx proxies to us; never expose to public
bind    = "127.0.0.1:8000"
backlog = 64       # Pending connection queue. Keep low: a full queue means
                   # the server is already saturated — fail fast is better
                   # than queueing requests that will time out anyway.

# ── Workers ───────────────────────────────────────────────────────────────────
# MUST stay at 1.
# GutBot stores every user's FAISS index and uploaded chunks in process memory,
# keyed by conversationId. With more than 1 worker (separate OS processes),
# User A's documents uploaded on worker-1 would be invisible on worker-2,
# silently breaking their session. Single worker + gevent handles concurrent
# I/O efficiently without this problem.
workers         = 1
worker_class    = "gevent"      # Cooperative multitasking — ideal for I/O-bound workloads
                                # (LLM calls, FAISS search, PDF parsing)

# ── Concurrency limit ─────────────────────────────────────────────────────────
# Each active connection holds memory for its session (FAISS index, chunks).
# 100 is safe for t3.large (8 GB). Lower to 60 on t3.medium (4 GB).
# Raise to 150 on t3.xlarge (16 GB) if needed.
#
#   Instance     RAM      worker_connections
#   t3.medium    4 GB     60
#   t3.large     8 GB     100   ← default here
#   t3.xlarge    16 GB    150
#
worker_connections = 100

# ── Timeouts ──────────────────────────────────────────────────────────────────
timeout          = 120   # Kill worker if a request takes longer than 120s.
                         # LLM calls via Bedrock average 10–30s; 120s gives headroom.
graceful_timeout = 30    # On SIGTERM, wait 30s for in-flight requests to finish
                         # before force-killing the worker.
keepalive        = 5     # Reuse TCP connections for up to 5s of idle time.
                         # Reduces connection overhead for Nginx → Gunicorn.

# ── Memory safety — prevent slow memory leaks ─────────────────────────────────
# Gunicorn respawns the worker cleanly after this many requests.
# In-progress requests finish before the restart; sessions are preserved
# because the new worker reloads conversation_indices from scratch (empty).
# This is intentional: it prevents any long-running worker from gradually
# accumulating memory until the EC2 instance crashes.
max_requests        = 500
max_requests_jitter = 50    # Randomise ±50 to avoid all workers restarting at once

# ── App preloading ─────────────────────────────────────────────────────────────
# Load the Flask app, embedding model, and FAISS indices once before
# the worker starts. Saves ~800 MB of model-load time on each restart
# and gives a clean copy-on-write memory baseline.
preload_app = True

# ── Logging ───────────────────────────────────────────────────────────────────
accesslog = "/var/log/gutbot/access.log"
errorlog  = "/var/log/gutbot/error.log"
loglevel  = "info"
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" %(D)sus'
)

# ── Process name (shows in `ps aux` and `top`) ────────────────────────────────
proc_name = "gutbot"

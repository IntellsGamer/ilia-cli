"""
Gunicorn configuration for ilia Telemetry Server
For production deployment
"""

import multiprocessing

# Server socket
bind = "127.0.0.1:3001"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "./logs/gunicorn_access.log"
errorlog = "./logs/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "ilia-telemetry-server"

# Server mechanics
daemon = False
pidfile = "./logs/gunicorn.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment if using HTTPS)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"

# Server hooks
def post_fork(server, worker):
    server.log.info("Worker %s spawned", worker.pid)

def pre_fork(server, worker):
    pass

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("Worker %s received INT or QUIT signal", worker.pid)

def worker_abort(worker):
    worker.log.info("Worker %s received SIGABRT signal", worker.pid)
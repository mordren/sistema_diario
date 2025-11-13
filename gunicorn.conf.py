# gunicorn.conf.py
import multiprocessing

# Configurações para economizar memória no Render
workers = 1
threads = 2
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
preload_app = True
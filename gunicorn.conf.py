# /path-to-your-project/gunicorn_conf.py
bind = 'unix:lavita_backend.sock'
worker_class = 'sync'
loglevel = 'info'
accesslog = '/home/www/lavita/backend/logs/access.log'
acceslogformat ="%(h)s %(l)s %(u)s %(t)s %(r)s %(s)s %(b)s %(f)s %(a)s"
errorlog =  '/home/www/lavita/backend/logs/err.log'
workers = 2
release: python manage.py migrate
web: bin/start-pgbouncer-stunnel gunicorn toolsbackbone.wsgi --log-file -
autopilot: python manage.py autopilot

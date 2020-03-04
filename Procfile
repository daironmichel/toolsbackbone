release: python manage.py migrate
web: bin/start-pgbouncer-stunnel gunicorn toolsbackbone.wsgi --log-file -
autopilot: bin/start-pgbouncer-stunnel python manage.py autopilot

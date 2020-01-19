release: python manage.py migrate
web: gunicorn toolsbackbone.wsgi --log-file -
worker: python manage.py autopilot

release: python manage.py migrate
web: gunicorn notespace.wsgi:application --bind 0.0.0.0:$PORT

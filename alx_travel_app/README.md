# Celery Email Notifications

1. Install RabbitMQ:
   sudo apt install rabbitmq-server
   sudo systemctl start rabbitmq-server

2. Install dependencies:
   pip install -r requirements.txt

3. Start Django server:
   python manage.py runserver

4. Start Celery worker:
   celery -A alx_travel_app worker -l info

5. Create a booking to trigger email notifications.

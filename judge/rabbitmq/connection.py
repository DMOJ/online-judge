import pika
from django.conf import settings

URL = settings.JUDGE_AMQP_PATH
params = pika.URLParameters(URL)
vhost = params.virtual_host
conn = None


def connect():
    global conn
    if conn is None:
        conn = pika.BlockingConnection(params)
        chan = conn.channel()
        chan.queue_declare(queue='submission', durable=True)
        chan.queue_declare(queue='submission-id', durable=True)
        chan.queue_declare(queue='judge-ping', durable=True)
        chan.exchange_declare(exchange='broadcast', exchange_type='fanout', durable=True)
    return conn

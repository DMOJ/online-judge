import pika
from pika.exceptions import ConnectionClosed
from django.conf import settings

URL = settings.JUDGE_AMQP_PATH
params = pika.URLParameters(URL)
vhost = params.virtual_host
conn = None


def initialize(chan):
    chan.queue_declare(queue='submission', durable=True)
    chan.queue_declare(queue='submission-id', durable=True)
    chan.queue_declare(queue='judge-ping', durable=True)
    chan.queue_declare(queue='latency', durable=True)
    chan.exchange_declare(exchange='broadcast', exchange_type='fanout', durable=True)
    chan.close()


def connect():
    global conn
    if conn is not None:
        try:
            conn.process_data_events()
        except ConnectionClosed:
            pass
        else:
            return conn
    conn = pika.BlockingConnection(params)
    initialize(conn.channel())
    return conn

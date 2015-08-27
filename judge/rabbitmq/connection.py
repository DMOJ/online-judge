import pika
from django.conf import settings

URL = settings.JUDGE_AMQP_PATH
params = pika.URLParameters(URL)
vhost = params.virtual_host


def connect():
    return pika.BlockingConnection(params)

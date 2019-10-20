from django.conf import settings

__all__ = ['last', 'post']

if not settings.EVENT_DAEMON_USE:
    real = False

    def post(channel, message):
        return 0

    def last():
        return 0
elif hasattr(settings, 'EVENT_DAEMON_AMQP'):
    from .event_poster_amqp import last, post
    real = True
else:
    from .event_poster_ws import last, post
    real = True

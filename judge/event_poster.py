from django.conf import settings

__all__ = ['last', 'post']

if not getattr(settings, 'EVENT_DAEMON_USE', False):
    def post(channel, message):
        return 0

    def last():
        return 0
elif hasattr(settings, 'EVENT_DAEMON_AMQP'):
    from .event_poster_amqp import last, post
else:
    from .event_poster_ws import last, post
from collections import defaultdict
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.functional import SimpleLazyObject
from .models import Profile, MiscConfig


def get_profile(request):
    if request.user.is_authenticated():
        return Profile.objects.get_or_create(user=request.user)[0]
    return None


def user_profile(request):
    return {'profile': SimpleLazyObject(lambda: get_profile(request))}


def comet_location(request):
    return {'EVENT_DAEMON_LOCATION': settings.EVENT_DAEMON_GET,
            'EVENT_DAEMON_POLL_LOCATION': settings.EVENT_DAEMON_POLL}


def __tab(request):
    if request.path == '/':
        return 'home'
    elif '/submi' in request.path:
        return 'submit'
    elif request.path.startswith('/problem'):
        return 'problem'
    elif request.path.startswith('/user'):
        return 'user'
    elif request.path == '/about/':
        return 'about'


def general_info(request):
    return {'nav_tab': __tab(request)}


def site(request):
    return {'site': Site.objects.get_current()}


def __get_config(key):
    try:
        return MiscConfig.objects.get(key=key).value
    except MiscConfig.DoesNotExist:
        return ''


def misc_config(request):
    return {'misc_config': defaultdict(__get_config)}
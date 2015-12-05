from functools import partial

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.utils.functional import SimpleLazyObject, new_method_proxy

from .models import Profile, MiscConfig, NavigationBar


class FixedSimpleLazyObject(SimpleLazyObject):
    if not hasattr(SimpleLazyObject, '__iter__'):
        __iter__ = new_method_proxy(iter)


def get_resource(request):
    use_https = getattr(settings, 'DMOJ_SSL', 0)
    if use_https == 1:
        scheme = 'https' if request.is_secure() else 'http'
    elif use_https > 1:
        scheme = 'https'
    else:
        scheme = 'http'
    return {
        'PYGMENT_THEME': getattr(settings, 'PYGMENT_THEME', None),
        'INLINE_JQUERY': getattr(settings, 'INLINE_JQUERY', True),
        'INLINE_FONTAWESOME': getattr(settings, 'INLINE_FONTAWESOME', True),
        'JQUERY_JS': getattr(settings, 'JQUERY_JS', '//ajax.googleapis.com/ajax/libs/jquery/2.1.4/jquery.min.js'),
        'FONTAWESOME_CSS': getattr(settings, 'FONTAWESOME_CSS',
                                   '//maxcdn.bootstrapcdn.com/font-awesome/4.3.0/css/font-awesome.min.css'),
        'DMOJ_SCHEME': scheme,
    }


def get_profile(request):
    if request.user.is_authenticated():
        return Profile.objects.get_or_create(user=request.user)[0]
    return None


def comet_location(request):
    if request.is_secure():
        websocket = getattr(settings, 'EVENT_DAEMON_GET_SSL', settings.EVENT_DAEMON_GET)
        poll = getattr(settings, 'EVENT_DAEMON_POLL_SSL', settings.EVENT_DAEMON_POLL)
    else:
        websocket = settings.EVENT_DAEMON_GET
        poll = settings.EVENT_DAEMON_POLL
    return {'EVENT_DAEMON_LOCATION': websocket,
            'EVENT_DAEMON_POLL_LOCATION': poll}


def __nav_tab(path):
    result = list(NavigationBar.objects.extra(where=['%s REGEXP BINARY regex'], params=[path])[:1])
    return result[0].get_ancestors(include_self=True).values_list('key', flat=True) if result else []


def general_info(request):
    path = request.get_full_path()
    return {
        'nav_tab': FixedSimpleLazyObject(partial(__nav_tab, request.path)),
        'nav_bar': NavigationBar.objects.all(),
        'LOGIN_RETURN_PATH': '' if path.startswith('/accounts/') else path
    }


def site(request):
    return {'site': Site.objects.get_current()}


class MiscConfigDict(dict):
    def __missing__(self, key):
        cache_key = 'misc_config:%s' % key
        value = cache.get(cache_key)
        if value is None:
            try:
                value = MiscConfig.objects.get(key=key).value
            except MiscConfig.DoesNotExist:
                value = ''
            cache.set(cache_key, value, 86400)
        self[key] = value
        return value


def misc_config(request):
    return {'misc_config': MiscConfigDict()}


def contest(request):
    if request.user.is_authenticated():
        contest_profile = request.user.profile.contest
        in_contest = contest_profile.current is not None
        participation = contest_profile.current
    else:
        in_contest = False
        participation = None
    return {'IN_CONTEST': in_contest, 'CONTEST': participation}


def site_name(request):
    return {'SITE_NAME': getattr(settings, 'SITE_NAME', 'DMOJ'),
            'SITE_LONG_NAME': getattr(settings, 'SITE_LONG_NAME', getattr(settings, 'SITE_NAME', 'DMOJ')),
            'SITE_ADMIN_EMAIL': getattr(settings, 'SITE_ADMIN_EMAIL', False)}

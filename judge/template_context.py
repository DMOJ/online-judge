from functools import partial

from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.utils.functional import SimpleLazyObject, new_method_proxy

from judge.utils.caniuse import CanIUse, SUPPORT
from .models import MiscConfig, NavigationBar, Profile


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
        'DMOJ_CANONICAL': getattr(settings, 'DMOJ_CANONICAL', ''),
    }


def get_profile(request):
    if request.user.is_authenticated:
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
        'LOGIN_RETURN_PATH': '' if path.startswith('/accounts/') else path,
        'perms': PermWrapper(request.user),
    }


def site(request):
    return {'site': get_current_site(request)}


class MiscConfigDict(dict):
    __slots__ = ('language', 'site')

    def __init__(self, language='', domain=None):
        self.language = language
        self.site = domain
        super(MiscConfigDict, self).__init__()

    def __missing__(self, key):
        cache_key = 'misc_config:%s:%s:%s' % (self.site, self.language, key)
        value = cache.get(cache_key)
        if value is None:
            keys = ['%s.%s' % (key, self.language), key] if self.language else [key]
            if self.site is not None:
                keys = ['%s:%s' % (self.site, key) for key in keys] + keys
            map = dict(MiscConfig.objects.values_list('key', 'value').filter(key__in=keys))
            for item in keys:
                if item in map:
                    value = map[item]
                    break
            else:
                value = ''
            cache.set(cache_key, value, 86400)
        self[key] = value
        return value


def misc_config(request):
    domain = get_current_site(request).domain
    return {'misc_config': MiscConfigDict(domain=domain),
            'i18n_config': MiscConfigDict(language=request.LANGUAGE_CODE, domain=domain)}


def site_name(request):
    return {'SITE_NAME': getattr(settings, 'SITE_NAME', 'DMOJ'),
            'SITE_LONG_NAME': getattr(settings, 'SITE_LONG_NAME', getattr(settings, 'SITE_NAME', 'DMOJ')),
            'SITE_ADMIN_EMAIL': getattr(settings, 'SITE_ADMIN_EMAIL', False)}


def math_setting(request):
    caniuse = CanIUse(request.META.get('HTTP_USER_AGENT', ''))

    if request.user.is_authenticated:
        engine = request.profile.math_engine
    else:
        engine = getattr(settings, 'MATHOID_DEFAULT_TYPE', 'auto')
    if engine == 'auto':
        engine = 'mml' if bool(getattr(settings, 'MATHOID_URL', False)) and caniuse.mathml == SUPPORT else 'jax'
    return {'MATH_ENGINE': engine, 'REQUIRE_JAX': engine == 'jax', 'caniuse': caniuse}

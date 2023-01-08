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
    use_https = settings.DMOJ_SSL
    if use_https == 1:
        scheme = 'https' if request.is_secure() else 'http'
    elif use_https > 1:
        scheme = 'https'
    else:
        scheme = 'http'
    return {
        'STYLE_CSS': 'dark/style.css' if 'dark' in request.GET else 'style.css',
        'INLINE_JQUERY': settings.INLINE_JQUERY,
        'INLINE_FONTAWESOME': settings.INLINE_FONTAWESOME,
        'JQUERY_JS': settings.JQUERY_JS,
        'FONTAWESOME_CSS': settings.FONTAWESOME_CSS,
        'DMOJ_SCHEME': scheme,
        'DMOJ_CANONICAL': settings.DMOJ_CANONICAL,
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
        'HAS_WEBAUTHN': bool(settings.WEBAUTHN_RP_ID),
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
    return {'SITE_NAME': settings.SITE_NAME,
            'SITE_LONG_NAME': settings.SITE_LONG_NAME,
            'SITE_ADMIN_EMAIL': settings.SITE_ADMIN_EMAIL}


def math_setting(request):
    caniuse = CanIUse(request.META.get('HTTP_USER_AGENT', ''))

    # Middleware populating `profile` may not have loaded at this point if we're called from an error context.
    if hasattr(request.user, 'profile'):
        engine = request.profile.math_engine
    else:
        engine = settings.MATHOID_DEFAULT_TYPE
    if engine == 'auto':
        engine = 'mml' if bool(settings.MATHOID_URL) and caniuse.mathml == SUPPORT else 'jax'
    return {'MATH_ENGINE': engine, 'REQUIRE_JAX': engine == 'jax', 'caniuse': caniuse}

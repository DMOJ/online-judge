import re

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import Resolver404, resolve, reverse
from django.utils.http import urlquote

from judge.models import Profile


class ShortCircuitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            callback, args, kwargs = resolve(request.path_info, getattr(request, 'urlconf', None))
        except Resolver404:
            callback, args, kwargs = None, None, None

        if getattr(callback, 'short_circuit_middleware', False):
            return callback(request, *args, **kwargs)
        return self.get_response(request)


class DMOJLoginMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = request.profile = request.user.profile
            login_2fa_path = reverse('login_2fa')
            if (profile.is_totp_enabled and not request.session.get('2fa_passed', False) and
                    request.path not in (login_2fa_path, reverse('auth_logout')) and
                    not request.path.startswith(settings.STATIC_URL)):
                return HttpResponseRedirect(login_2fa_path + '?next=' + urlquote(request.get_full_path()))
        else:
            request.profile = None
        return self.get_response(request)


class DMOJImpersonationMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_impersonate:
            request.no_profile_update = True
            request.profile = request.user.profile
        return self.get_response(request)


class ContestMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        profile = request.profile
        if profile:
            profile.update_contest()
            request.participation = profile.current_contest
            request.in_contest = request.participation is not None
        else:
            request.in_contest = False
            request.participation = None
        return self.get_response(request)


class APIMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        full_token = request.META.get('HTTP_AUTHORIZATION', None)
        if full_token:
            if re.search(settings.DMOJ_API_HEADER_PATTERN, full_token):
                token = full_token.split()[-1]
                try:
                    request.user = Profile.objects.get(api_token=token).user
                except Profile.DoesNotExist:
                    return HttpResponse('Invalid token', status=401)
            else:
                return HttpResponse('Invalid authorization header', status=400)

        response = self.get_response(request)
        return response

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse, resolve
from django.utils.http import urlquote


class ECOOForceLoginMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            return self.get_response(request)

        url_name = resolve(request.path_info).url_name
        if (url_name.startswith('password_') or
            url_name in ('auth_login', 'auth_logout', 'login_2fa', 'home')):
            return self.get_response(request)
        
        login_path = reverse('auth_login')
        return HttpResponseRedirect(login_path + '?next=' + urlquote(request.get_full_path()))


class DMOJLoginMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = request.profile = request.user.profile
            login_2fa_path = reverse('login_2fa')
            if (profile.is_totp_enabled and not request.session.get('2fa_passed', False) and
                    request.path != login_2fa_path and not request.path.startswith(settings.STATIC_URL)):
                return HttpResponseRedirect(login_2fa_path + '?next=' + urlquote(request.get_full_path()))
        else:
            request.profile = None
        return self.get_response(request)


class DMOJImpersonationMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_impersonate:
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

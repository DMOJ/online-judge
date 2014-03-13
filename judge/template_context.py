from django.utils.functional import SimpleLazyObject
from .models import Profile


def get_profile(request):
    if request.user.is_authenticated():
        return Profile.objects.get_or_create(user=request.user)[0]
    return None


def user_profile(request):
    return {'profile': SimpleLazyObject(lambda: get_profile(request))}


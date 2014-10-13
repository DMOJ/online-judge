from judge.models import Profile
from django.utils.timezone import now


class LogUserAccessMiddleware(object):
    def process_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated():
            # Decided on using REMOTE_ADDR as nginx will translate it to the external IP that hits it.
            Profile.objects.filter(user_id=request.user.pk).update(last_access=now(),
                                                                   ip=request.META.get('REMOTE_ADDR'))

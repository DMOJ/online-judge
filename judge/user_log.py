from judge.models import Profile
from django.utils.timezone import now


class LogUserAccessMiddleware(object):
    def process_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            updates = {'last_access': now()}
            # Decided on using REMOTE_ADDR as nginx will translate it to the external IP that hits it.
            if request.META.get('REMOTE_ADDR'):
                updates['ip'] = request.META.get('REMOTE_ADDR')
            Profile.objects.filter(user_id=request.user.pk).update(**updates)

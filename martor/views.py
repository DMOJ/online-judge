import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from .utils import LazyEncoder


@login_required
def markdown_search_user(request):
    """
    Json usernames of the users registered & actived.

    url(method=get):
        /martor/search-user/?username={username}

    Response:
        error:
            - `status` is status code (204)
            - `error` is error message.
        success:
            - `status` is status code (204)
            - `data` is list dict of usernames.
                { 'status': 200,
                  'data': [
                    {'usernane': 'john'},
                    {'usernane': 'albert'}]
                }
    """
    data = {}
    username = request.GET.get('username')
    if username is not None \
            and username != '' \
            and ' ' not in username:
        users = User.objects.filter(username__icontains=username, is_active=True)
        if users:
            data.update({
                'status': 200,
                'data': [{'username': u.username} for u in users],
            })
            return HttpResponse(
                json.dumps(data, cls=LazyEncoder),
                content_type='application/json')
        data.update({
            'status': 204,
            'error': _('No users registered as `%(username)s` '
                       'or user is unactived.') % {'username': username},
        })
    else:
        data.update({
            'status': 204,
            'error': _('Validation Failed for field `username`'),
        })
    return HttpResponse(
        json.dumps(data, cls=LazyEncoder),
        content_type='application/json')

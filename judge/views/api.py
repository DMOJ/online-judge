from django.shortcuts import *

import json
from judge.models import Contest
from judge.templatetags.timedelta import nice_repr


def api_contest_list(request):
    js = {}
    for c in Contest.objects.filter(is_public=True):
        js[c.key] = {
            'name': c.name,
            'free_start': c.free_start,
            'start_time': c.start_time.isoformat() if c.start_time is not None else None,
            'time_limit': nice_repr(c.time_limit, 'concise'),
            'ongoing': c.ongoing
        }
    jso = json.dumps(js)
    return HttpResponse(jso, mimetype='application/json')

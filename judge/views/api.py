from django.shortcuts import *
import traceback
import json
from judge.models import Contest


def api_contest_list(request):
    js = {}
    for c in Contest.objects.filter(is_public=True):
        c[c.name] = {
            "description": c.description,
            "ongoing": c.ongoing
        }
    jso = json.dumps(js)
    return HttpResponse(jso, mimetype='application/json')

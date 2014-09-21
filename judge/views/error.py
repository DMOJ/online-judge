from django.shortcuts import *
import sys
import traceback

def error(request, context, status):
    template = loader.get_template('error.jade')
    return HttpResponse(template.render(RequestContext(request, context)), status=status)


def error404(request):
    return error(request, {'id': 'page_out_of_bounds',
                           'description': 'bad page %s' % request.path,
                           'code': 404}, 404)


def error403(request):
    return error(request, {'id': 'unauthorized_access',
                           'description': 'no permission for %s' % request.path,
                           'code': 403}, 403)


def error500(request):
    return error(request, {'id': 'invalid_state',
                           'description': 'corrupt page %s' % request.path,
                           'traceback': traceback.format(sys.exc_info()[2]),
                           'code': 500}, 500)
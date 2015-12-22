import traceback

from django.shortcuts import render
from django.utils.translation import ugettext as _


def error(request, context, status):
    return render(request, 'error.jade', context=context, status=status)


def error404(request):
    # TODO: "panic: go back"
    return render(request, 'generic_message.jade', {
        'title': _('404 error'),
        'message': _('Could not find page "%s"') % request.path
    }, status=404)


def error403(request):
    return error(request, {'id': 'unauthorized_access',
                           'description': _('no permission for %s') % request.path,
                           'code': 403}, 403)


def error500(request):
    return error(request, {'id': 'invalid_state',
                           'description': _('corrupt page %s') % request.path,
                           'traceback': traceback.format_exc(),
                           'code': 500}, 500)

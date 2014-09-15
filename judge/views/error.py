from django.shortcuts import *


def error404(request):
    return render_to_response('error.html',
                              {'id': 'SIGSEGV: page_out_of_bounds',
                               'description': 'bad page "%s"' % request.path,
                               'code': 404},
                              context_instance=RequestContext(request))


def error403(request):
    return render_to_response('error.html',
                              {'id': 'SIGINT: unautharized_access',
                               'description': 'bad page "%s"' % request.path,
                               'code': 403},
                              context_instance=RequestContext(request))


def error500(request):
    return render_to_response('error.html',
                              {'id': 'SIGILL: invalid_state',
                               'description': 'bad page "%s"' % request.path,
                               'code': 500},
                              context_instance=RequestContext(request))
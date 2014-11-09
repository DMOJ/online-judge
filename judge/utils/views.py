from django.contrib.auth.decorators import login_required
from django.shortcuts import render

__author__ = 'Quantum'


def generic_message(request, title, message, status=None):
    return render(request, 'generic_message.jade', {
        'message': message,
        'title': title
    }, status=status)


class TitleMixin(object):
    title = '(untitled)'

    def get_context_data(self, **kwargs):
        context = super(TitleMixin, self).get_context_data(**kwargs)
        context['title'] = self.get_title()
        return context

    def get_title(self):
        return self.title


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(view)
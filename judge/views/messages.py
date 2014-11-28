from itertools import chain
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Count, Max
from django.http import HttpResponseRedirect, Http404
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, View, UpdateView
from django.views.generic.detail import SingleObjectMixin

from judge.forms import EditOrganizationForm, NewOrganizationForm, NewMessageForm
from judge.models import Organization, PrivateMessage, Profile
from judge.utils.ranker import ranker
from judge.utils.views import generic_message, TitleMixin, LoginRequiredMixin


class NewMessage(LoginRequiredMixin, TitleMixin, CreateView):
    template_name = 'messages/new.jade'
    model = PrivateMessage
    form_class = NewMessageForm
    title = 'New Message'

    def get_context_data(self, **kwargs):
        context = super(NewMessage, self).get_context_data(**kwargs)
        profile = Profile.objects.filter(user__username=self.target)
        context['target'] = profile
        return context

    def form_valid(self, form):
        form.instance.registrant = self.request.user.profile
        return super(NewMessage, self).form_valid(form)

    def get(self, request, *args, **kwargs):
        self.target = request.GET.get('target') if 'target' in request.GET else None
        return super(NewMessage, self).get(request, *args, **kwargs)


class MessageList(LoginRequiredMixin, TitleMixin, ListView):
    model = PrivateMessage
    template_name = 'messages/list.jade'
    title = 'Inbox'

    def get_context_data(self, **kwargs):
        context = super(MessageList, self).get_context_data(**kwargs)
        profile = self.request.user.user.profile
        context['outgoing'] = PrivateMessage.objects.filter(sender=profile).order_by('-key')
        context['incoming'] = PrivateMessage.objects.filter(target=profile).order_by('-key')
        return context

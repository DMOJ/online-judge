from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _, ugettext
from django.views.generic import FormView
from django.views.generic.detail import SingleObjectMixin, DetailView

from judge.models import Ticket, TicketMessage, Problem
from judge.utils.views import TitleMixin


class TicketView(DetailView):
    model = Ticket
    pk_url_kwarg = 'id'
    template_name = 'ticket/ticket.jade'


class TicketForm(forms.Form):
    title = forms.CharField(max_length=100, label=_('ticket title'))
    body = forms.CharField(label=_('ticket body'))


class NewTicketView(LoginRequiredMixin, SingleObjectMixin, FormView):
    form_class = TicketForm
    template_name = 'ticket/new.jade'

    def get_assignees(self):
        return []

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(NewTicketView, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(NewTicketView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        ticket = Ticket(user=self.request.user.profile, title=form.cleaned_data['title'])
        ticket.linked_item = self.object
        ticket.save()
        TicketMessage(ticket=ticket, user=ticket.user, body=form.cleaned_data['body']).save()
        ticket.assignees.set(self.get_assignees())
        return HttpResponseRedirect(reverse('ticket', args=[ticket.id]))


class NewProblemTicketView(TitleMixin, NewTicketView):
    model = Problem
    slug_field = slug_url_kwarg = 'code'

    def get_title(self):
        return ugettext('New ticket for %s') % self.object.name

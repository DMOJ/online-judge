import json

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.db.models import Q
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.http import Http404
from django.template.defaultfilters import truncatechars
from django.template.loader import get_template
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.utils.html import escape, format_html, linebreaks
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy, ugettext as _
from django.views import View
from django.views.generic import FormView, ListView
from django.views.generic.detail import SingleObjectMixin

from judge import event_poster as event
from judge.models import Profile
from judge.models import Ticket, TicketMessage, Problem
from judge.utils.diggpaginator import DiggPaginator
from judge.utils.problems import editable_problems
from judge.utils.tickets import own_ticket_filter, filter_visible_tickets
from judge.utils.views import TitleMixin, paginate_query_context
from judge.widgets import HeavyPreviewPageDownWidget

ticket_widget = (forms.Textarea() if HeavyPreviewPageDownWidget is None else
                 HeavyPreviewPageDownWidget(preview=reverse_lazy('ticket_preview'),
                                            preview_timeout=1000, hide_preview_button=True))


class TicketForm(forms.Form):
    title = forms.CharField(max_length=100, label=ugettext_lazy('Ticket title'))
    body = forms.CharField(widget=ticket_widget)

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(TicketForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'placeholder': _('Ticket title')})
        self.fields['body'].widget.attrs.update({'placeholder': _('Issue description')})

    def clean(self):
        if self.request is not None and self.request.user.is_authenticated:
            profile = self.request.user.profile
            if profile.mute:
                raise ValidationError(_('Your part is silent, little toad.'))
        return super(TicketForm, self).clean()


class SingleObjectFormView(SingleObjectMixin, FormView):
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(SingleObjectFormView, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(SingleObjectFormView, self).get(request, *args, **kwargs)


class NewTicketView(LoginRequiredMixin, SingleObjectFormView):
    form_class = TicketForm
    template_name = 'ticket/new.html'

    def get_assignees(self):
        return []

    def form_valid(self, form):
        ticket = Ticket(user=self.request.user.profile, title=form.cleaned_data['title'])
        ticket.linked_item = self.object
        ticket.save()
        message = TicketMessage(ticket=ticket, user=ticket.user, body=form.cleaned_data['body'])
        message.save()
        ticket.assignees.set(self.get_assignees())
        if event.real:
            event.post('tickets', {
                'type': 'new-ticket', 'id': ticket.id,
                'message': message.id, 'user': ticket.user_id,
                'assignees': list(ticket.assignees.values_list('id', flat=True)),
            })
        return HttpResponseRedirect(reverse('ticket', args=[ticket.id]))


class NewProblemTicketView(TitleMixin, NewTicketView):
    model = Problem
    slug_field = 'code'
    slug_url_kwarg = 'problem'
    template_name = 'ticket/new_problem.html'

    def get_assignees(self):
        return self.object.authors.all()

    def get_title(self):
        return _('New ticket for %s') % self.object.name

    def get_content_title(self):
        return mark_safe(escape(_('New ticket for %s')) %
                         format_html(u'<a href="{0}">{1}</a>', reverse('problem_detail', args=[self.object.code]),
                                     self.object.translated_name(self.request.LANGUAGE_CODE)))


class TicketCommentForm(forms.Form):
    body = forms.CharField(widget=ticket_widget)


class TicketMixin(object):
    model = Ticket

    def get_object(self, queryset=None):
        ticket = super(TicketMixin, self).get_object(queryset)
        profile_id = self.request.user.profile.id
        if self.request.user.has_perm('judge.change_ticket'):
            return ticket
        if ticket.user_id == profile_id:
            return ticket
        if ticket.assignees.filter(id=profile_id).exists():
            return ticket
        linked = ticket.linked_item
        if isinstance(linked, Problem) and linked.is_editable_by(self.request.user):
            return ticket
        raise PermissionDenied()


class TicketView(TitleMixin, LoginRequiredMixin, TicketMixin, SingleObjectFormView):
    form_class = TicketCommentForm
    template_name = 'ticket/ticket.html'
    context_object_name = 'ticket'

    def form_valid(self, form):
        message = TicketMessage(user=self.request.user.profile,
                                body=form.cleaned_data['body'],
                                ticket=self.object)
        message.save()
        if event.real:
            event.post('tickets', {
                'type': 'ticket-message', 'id': self.object.id,
                'message': message.id, 'user': self.object.user_id,
                'assignees': list(self.object.assignees.values_list('id', flat=True)),
            })
        return HttpResponseRedirect('%s#message-%d' % (reverse('ticket', args=[self.object.id]), message.id))

    def get_title(self):
        return _('%(title)s - Ticket %(id)d') % {'title': self.object.title, 'id': self.object.id}

    def get_context_data(self, **kwargs):
        context = super(TicketView, self).get_context_data(**kwargs)
        context['messages'] = self.object.messages.select_related('user__user')
        context['assignees'] = self.object.assignees.select_related('user')
        context['last_msg'] = event.last()
        return context


class TicketStatusChangeView(LoginRequiredMixin, TicketMixin, SingleObjectMixin, View):
    open = None

    def post(self, request, *args, **kwargs):
        if self.open is None:
            raise ImproperlyConfigured('Need to define open')
        ticket = self.get_object()
        if ticket.is_open != self.open:
            ticket.is_open = self.open
            ticket.save()
            if event.real:
                event.post('tickets', {
                    'type': 'ticket-status', 'id': ticket.id,
                    'open': self.open, 'user': ticket.user_id,
                    'assignees': list(ticket.assignees.values_list('id', flat=True)),
                    'title': ticket.title
                })
                event.post('ticket-%d' % ticket.id, {
                    'type': 'ticket-status', 'open': self.open
                })
        return HttpResponse(status=204)


class TicketNotesForm(forms.Form):
    notes = forms.CharField(widget=forms.Textarea(), required=False)


class TicketNotesEditView(LoginRequiredMixin, TicketMixin, SingleObjectMixin, FormView):
    template_name = 'ticket/edit-notes.html'
    form_class = TicketNotesForm
    object = None

    def get_initial(self):
        return {'notes': self.get_object().notes}

    def form_valid(self, form):
        ticket = self.get_object()
        ticket.notes = notes = form.cleaned_data['notes']
        ticket.save()
        if notes:
            return HttpResponse(linebreaks(notes, autoescape=True))
        else:
            return HttpResponse()

    def form_invalid(self, form):
        return HttpResponseBadRequest()


class TicketList(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = 'ticket/list.html'
    context_object_name = 'tickets'
    paginate_by = 50
    paginator_class = DiggPaginator

    @cached_property
    def user(self):
        return self.request.user

    @cached_property
    def profile(self):
        return self.user.profile

    @cached_property
    def can_edit_all(self):
        return self.request.user.has_perm('judge.change_ticket')

    @cached_property
    def filter_users(self):
        return self.request.GET.getlist('user')

    @cached_property
    def filter_assignees(self):
        return self.request.GET.getlist('assignee')

    def GET_with_session(self, key):
        if not self.request.GET:
            return self.request.session.get(key, False)
        return self.request.GET.get(key, None) == '1'

    def _get_queryset(self):
        return Ticket.objects.select_related('user__user').prefetch_related('assignees__user').order_by('-id')

    def get_queryset(self):
        queryset = self._get_queryset()
        if self.GET_with_session('own'):
            queryset = queryset.filter(own_ticket_filter(self.profile.id))
        elif not self.can_edit_all:
            queryset = filter_visible_tickets(queryset, self.user, self.profile)
        if self.filter_assignees:
            queryset = queryset.filter(assignees__user__username__in=self.filter_assignees)
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super(TicketList, self).get_context_data(**kwargs)

        page = context['page_obj']
        context['title'] = _('Tickets - Page %(number)d of %(total)d') % {
            'number': page.number,
            'total': page.paginator.num_pages,
        }
        context['can_edit_all'] = self.can_edit_all
        context['filter_status'] = {
            'own': self.GET_with_session('own'), 'user': self.filter_users, 'assignee': self.filter_assignees,
            'user_id': json.dumps(list(Profile.objects.filter(user__username__in=self.filter_users)
                                       .values_list('id', flat=True))),
            'assignee_id': json.dumps(list(Profile.objects.filter(user__username__in=self.filter_assignees)
                                           .values_list('id', flat=True))),
            'own_id': self.profile.id if self.GET_with_session('own') else 'null',
        }
        context['last_msg'] = event.last()
        context.update(paginate_query_context(self.request))
        return context

    def post(self, request, *args, **kwargs):
        to_update = ('own',)
        for key in to_update:
            if key in request.GET:
                val = request.GET.get(key) == '1'
                request.session[key] = val
            else:
                request.session.pop(key, None)
        return HttpResponseRedirect(request.get_full_path())


class ProblemTicketListView(TicketList):
    def _get_queryset(self):
        if 'problem' not in self.kwargs:
            raise Http404()
        problem = Problem.objects.get(code=self.kwargs['problem'])
        if not self.request.user.is_authenticated or not problem.is_editable_by(self.request.user):
            raise Http404()
        return problem.tickets.all()


class TicketListDataAjax(TicketMixin, SingleObjectMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            self.kwargs['pk'] = request.GET['id']
        except KeyError:
            return HttpResponseBadRequest()
        ticket = self.get_object()
        message = ticket.messages.first()
        return JsonResponse({
            'row': get_template('ticket/row.html').render({'ticket': ticket}, request),
            'notification': {
                'title': _('New Ticket: %s') % ticket.title,
                'body': '%s\n%s' % (_('#%(id)d, assigned to: %(users)s') % {
                    'id': ticket.id, 'users': (_(', ').join(ticket.assignees.values_list('user__username', flat=True))
                                               or _('no one')),
                }, truncatechars(message.body, 200)),
            }
        })

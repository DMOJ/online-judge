import json

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured, PermissionDenied, ValidationError
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import truncatechars
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy
from django.utils.functional import cached_property
from django.utils.html import escape, format_html, linebreaks
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _, gettext_lazy
from django.views import View
from django.views.generic import ListView
from django.views.generic.detail import SingleObjectMixin

from judge import event_poster as event
from judge.models import Problem, Profile, Ticket, TicketMessage
from judge.utils.diggpaginator import DiggPaginator
from judge.utils.tickets import filter_visible_tickets, own_ticket_filter
from judge.utils.views import SingleObjectFormView, TitleMixin, paginate_query_context
from judge.views.problem import ProblemMixin
from judge.widgets import HeavyPreviewPageDownWidget

ticket_widget = (forms.Textarea() if HeavyPreviewPageDownWidget is None else
                 HeavyPreviewPageDownWidget(preview=reverse_lazy('ticket_preview'),
                                            preview_timeout=1000, hide_preview_button=True))


class TicketForm(forms.Form):
    title = forms.CharField(max_length=100, label=gettext_lazy('Ticket title'))
    body = forms.CharField(widget=ticket_widget)

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(TicketForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'placeholder': _('Ticket title')})
        self.fields['body'].widget.attrs.update({'placeholder': _('Issue description')})

    def clean(self):
        if self.request is not None and self.request.user.is_authenticated:
            profile = self.request.profile
            if profile.mute:
                raise ValidationError(_('Your part is silent, little toad.'))
            if not self.request.in_contest and not profile.has_any_solves:
                raise ValidationError(_('You must solve at least one problem before you can create a ticket.'))
        return super(TicketForm, self).clean()


class NewTicketView(LoginRequiredMixin, SingleObjectFormView):
    form_class = TicketForm
    template_name = 'ticket/new.html'

    def get_assignees(self):
        return []

    def get_form_kwargs(self):
        kwargs = super(NewTicketView, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        ticket = Ticket(user=self.request.profile, title=form.cleaned_data['title'])
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


class NewProblemTicketView(ProblemMixin, TitleMixin, NewTicketView):
    template_name = 'ticket/new_problem.html'

    def get_assignees(self):
        if self.request.in_contest:
            contest = self.request.participation.contest
            if self.object.contests.filter(contest=contest).exists():
                return contest.authors.all()
        return self.object.authors.all()

    def get_title(self):
        return _('New ticket for %s') % self.object.name

    def get_content_title(self):
        return mark_safe(escape(_('New ticket for %s')) %
                         format_html('<a href="{0}">{1}</a>', reverse('problem_detail', args=[self.object.code]),
                                     self.object.translated_name(self.request.LANGUAGE_CODE)))

    def form_valid(self, form):
        if not self.object.is_accessible_by(self.request.user):
            raise Http404()
        return super().form_valid(form)


class TicketCommentForm(forms.Form):
    body = forms.CharField(widget=ticket_widget)


class TicketMixin(LoginRequiredMixin):
    model = Ticket

    def get_object(self, queryset=None):
        ticket = super(TicketMixin, self).get_object(queryset)
        profile_id = self.request.profile.id
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


class TicketView(TitleMixin, TicketMixin, SingleObjectFormView):
    form_class = TicketCommentForm
    template_name = 'ticket/ticket.html'
    context_object_name = 'ticket'

    def form_valid(self, form):
        message = TicketMessage(user=self.request.profile,
                                body=form.cleaned_data['body'],
                                ticket=self.object)
        message.save()
        if event.real:
            event.post('tickets', {
                'type': 'ticket-message', 'id': self.object.id,
                'message': message.id, 'user': self.object.user_id,
                'assignees': list(self.object.assignees.values_list('id', flat=True)),
            })
            event.post('ticket-%d' % self.object.id, {
                'type': 'ticket-message', 'message': message.id,
            })
        return HttpResponseRedirect('%s#message-%d' % (reverse('ticket', args=[self.object.id]), message.id))

    def get_title(self):
        return _('%(title)s - Ticket %(id)d') % {'title': self.object.title, 'id': self.object.id}

    def get_context_data(self, **kwargs):
        context = super(TicketView, self).get_context_data(**kwargs)
        context['ticket_messages'] = self.object.messages.select_related('user__user')
        context['assignees'] = self.object.assignees.select_related('user')
        context['last_msg'] = event.last()
        return context


class TicketStatusChangeView(TicketMixin, SingleObjectMixin, View):
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
                    'title': ticket.title,
                })
                event.post('ticket-%d' % ticket.id, {
                    'type': 'ticket-status', 'open': self.open,
                })
        return HttpResponse(status=204)


class TicketNotesForm(forms.Form):
    notes = forms.CharField(widget=forms.Textarea(), required=False)


class TicketNotesEditView(TicketMixin, SingleObjectFormView):
    template_name = 'ticket/edit-notes.html'
    form_class = TicketNotesForm
    context_object_name = 'ticket'

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
    def profile(self):
        return self.request.profile

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
        if self.GET_with_session('open'):
            queryset = queryset.filter(is_open=True)
        if self.GET_with_session('own'):
            queryset = queryset.filter(own_ticket_filter(self.profile.id))
        elif not self.can_edit_all:
            queryset = filter_visible_tickets(queryset, self.request.user)
        if self.filter_assignees:
            queryset = queryset.filter(assignees__user__username__in=self.filter_assignees)
        if self.filter_users:
            queryset = queryset.filter(user__user__username__in=self.filter_users)
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
            'open': self.GET_with_session('open'),
            'own': self.GET_with_session('own'),
            'user': self.filter_users,
            'assignee': self.filter_assignees,
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
        to_update = ('open', 'own')
        for key in to_update:
            if key in request.GET:
                val = request.GET.get(key) == '1'
                request.session[key] = val
            else:
                request.session.pop(key, None)
        return HttpResponseRedirect(request.get_full_path())


class ProblemTicketListView(TicketList):
    def _get_queryset(self):
        problem = get_object_or_404(Problem, code=self.kwargs.get('problem'))
        if problem.is_editable_by(self.request.user):
            return problem.tickets.order_by('-id')
        elif problem.is_accessible_by(self.request.user):
            return problem.tickets.filter(own_ticket_filter(self.profile.id)).order_by('-id')
        raise Http404()


class TicketListDataAjax(TicketMixin, SingleObjectMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            self.kwargs['pk'] = int(request.GET['id'])
        except (KeyError, ValueError):
            return HttpResponseBadRequest()
        ticket = self.get_object()
        message = ticket.messages.first()
        return JsonResponse({
            'row': get_template('ticket/row.html').render({'ticket': ticket}, request),
            'notification': {
                'title': _('New Ticket: %s') % ticket.title,
                'body': '%s\n%s' % (_('#%(id)d, assigned to: %(users)s') % {
                    'id': ticket.id,
                    'users': (_(', ').join(ticket.assignees.values_list('user__username', flat=True)) or _('no one')),
                }, truncatechars(message.body, 200)),
            },
        })


class TicketMessageDataAjax(TicketMixin, SingleObjectMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            message_id = int(request.GET['message'])
        except (KeyError, ValueError):
            return HttpResponseBadRequest()
        ticket = self.get_object()
        try:
            message = ticket.messages.get(id=message_id)
        except TicketMessage.DoesNotExist:
            return HttpResponseBadRequest()
        return JsonResponse({
            'message': get_template('ticket/message.html').render({'message': message, 'ticket': ticket}, request),
            'notification': {
                'title': _('New Ticket Message For: %s') % ticket.title,
                'body': truncatechars(message.body, 200),
            },
        })

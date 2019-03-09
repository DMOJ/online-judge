from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.http import Http404, HttpResponsePermanentRedirect
from django.templatetags.static import static
from django.urls import reverse
from django.utils.functional import lazystr
from django.utils.translation import ugettext_lazy as _
from django.views.generic import RedirectView

from judge.forms import CustomAuthenticationForm
from judge.sitemap import BlogPostSitemap, ContestSitemap, HomePageSitemap, ProblemSitemap, UrlSitemap, UserSitemap
from judge.views import blog, contests, language, license, preview, problem, problem_manage, ranked_submission, \
    stats, status, submission, tasks, ticket, totp, user, widgets
from judge.views.problem_data import ProblemDataView, ProblemSubmissionDiff, \
    problem_data_file, problem_init_view
from judge.views.select2 import AssigneeSelect2View, CommentSelect2View, ContestSelect2View, \
    ContestUserSearchSelect2View, OrganizationSelect2View, ProblemSelect2View, TicketUserSelect2View, \
    UserSearchSelect2View, UserSelect2View

admin.autodiscover()

register_patterns = [
    url(r'^login/$', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        extra_context={'title': _('Login')},
        authentication_form=CustomAuthenticationForm,
        redirect_authenticated_user=True,
    ), name='auth_login'),
    url(r'^logout/$', user.UserLogoutView.as_view(), name='auth_logout'),
    url(r'^password/change/$', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change_form.html',
    ), name='password_change'),
    url(r'^password/change/done/$', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html',
    ), name='password_change_done'),
    url(r'^password/reset/$', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset.html',
        html_email_template_name='registration/password_reset_email.html',
        email_template_name='registration/password_reset_email.txt',
    ), name='password_reset'),
    url(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
        ), name='password_reset_confirm'),
    url(r'^password/reset/complete/$', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html',
    ), name='password_reset_complete'),
    url(r'^password/reset/done/$', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html',
    ), name='password_reset_done'),

    url(r'^2fa/$', totp.TOTPLoginView.as_view(), name='login_2fa'),
    url(r'^2fa/enable/$', totp.TOTPEnableView.as_view(), name='enable_2fa'),
    url(r'^2fa/disable/$', totp.TOTPDisableView.as_view(), name='disable_2fa'),
]


def exception(request):
    if not request.user.is_superuser:
        raise Http404()
    raise RuntimeError('@Xyene asked me to cause this')


def paged_list_view(view, name):
    return include([
        url(r'^$', view.as_view(), name=name),
        url(r'^(?P<page>\d+)$', view.as_view(), name=name),
    ])


urlpatterns = [
    url(r'^$', blog.PostList.as_view(template_name='home.html', title=_('Home')), kwargs={'page': 1}, name='home'),
    url(r'^admin/', admin.site.urls),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^accounts/', include(register_patterns)),
    url(r'^', include('social_django.urls')),

    url(r'^problems/$', problem.ProblemList.as_view(), name='problem_list'),
    url(r'^problems/random/$', problem.RandomProblem.as_view(), name='problem_random'),

    url(r'^problem/(?P<problem>[^/]+)', include([
        url(r'^$', problem.ProblemDetail.as_view(), name='problem_detail'),
        url(r'^/editorial$', problem.ProblemSolution.as_view(), name='problem_editorial'),
        url(r'^/raw$', problem.ProblemRaw.as_view(), name='problem_raw'),
        url(r'^/pdf$', problem.ProblemPdfView.as_view(), name='problem_pdf'),
        url(r'^/pdf/(?P<language>[a-z-]+)$', problem.ProblemPdfView.as_view(), name='problem_pdf'),
        url(r'^/clone', problem.ProblemClone.as_view(), name='problem_clone'),
        url(r'^/submit$', problem.problem_submit, name='problem_submit'),
        url(r'^/resubmit/(?P<submission>\d+)$', problem.problem_submit, name='problem_submit'),

        url(r'^/rank/', paged_list_view(ranked_submission.RankedSubmissions, 'ranked_submissions')),
        url(r'^/submissions/', paged_list_view(submission.ProblemSubmissions, 'chronological_submissions')),
        url(r'^/submissions/(?P<user>\w+)/', paged_list_view(submission.UserProblemSubmissions, 'user_submissions')),

        url(r'^/$', lambda _, problem: HttpResponsePermanentRedirect(reverse('problem_detail', args=[problem]))),

        url(r'^/test_data$', ProblemDataView.as_view(), name='problem_data'),
        url(r'^/test_data/init$', problem_init_view, name='problem_data_init'),
        url(r'^/test_data/diff$', ProblemSubmissionDiff.as_view(), name='problem_submission_diff'),
        url(r'^/data/(?P<path>.+)$', problem_data_file, name='problem_data_file'),

        url(r'^/tickets$', ticket.ProblemTicketListView.as_view(), name='problem_ticket_list'),
        url(r'^/tickets/new$', ticket.NewProblemTicketView.as_view(), name='new_problem_ticket'),

        url(r'^/manage/submission', include([
            url('^$', problem_manage.ManageProblemSubmissionView.as_view(), name='problem_manage_submissions'),
            url('^/rejudge$', problem_manage.RejudgeSubmissionsView.as_view(), name='problem_submissions_rejudge'),
            url('^/rejudge/preview$', problem_manage.PreviewRejudgeSubmissionsView.as_view(),
                name='problem_submissions_rejudge_preview'),
            url('^/rejudge/success/(?P<task_id>[A-Za-z0-9-]*)$', problem_manage.rejudge_success,
                name='problem_submissions_rejudge_success'),
            url('^/rescore/all$', problem_manage.RescoreAllSubmissionsView.as_view(),
                name='problem_submissions_rescore_all'),
            url('^/rescore/success/(?P<task_id>[A-Za-z0-9-]*)$', problem_manage.rescore_success,
                name='problem_submissions_rescore_success'),
        ])),
    ])),

    url(r'^submissions/', paged_list_view(submission.AllSubmissions, 'all_submissions')),
    url(r'^submissions/user/(?P<user>\w+)/', paged_list_view(submission.AllUserSubmissions, 'all_user_submissions')),

    url(r'^src/(?P<submission>\d+)$', submission.SubmissionSource.as_view(), name='submission_source'),
    url(r'^src/(?P<submission>\d+)/raw$', submission.SubmissionSourceRaw.as_view(), name='submission_source_raw'),

    url(r'^submission/(?P<submission>\d+)', include([
        url(r'^$', submission.SubmissionStatus.as_view(), name='submission_status'),
        url(r'^/abort$', submission.abort_submission, name='submission_abort'),
        url(r'^/html$', submission.single_submission),
    ])),

    url(r'^users/', include([
        url(r'^$', user.users, name='user_list'),
        url(r'^(?P<page>\d+)$', lambda request, page:
            HttpResponsePermanentRedirect('%s?page=%s' % (reverse('user_list'), page))),
        url(r'^find$', user.user_ranking_redirect, name='user_ranking_redirect'),
    ])),

    url(r'^user$', user.UserAboutPage.as_view(), name='user_page'),
    url(r'^edit/profile/$', user.edit_profile, name='user_edit_profile'),
    url(r'^user/(?P<user>\w+)', include([
        url(r'^$', user.UserAboutPage.as_view(), name='user_page'),
        url(r'^/solved', include([
            url(r'^$', user.UserProblemsPage.as_view(), name='user_problems'),
            url(r'/ajax$', user.UserPerformancePointsAjax.as_view(), name='user_pp_ajax'),
        ])),
        url(r'^/submissions/', paged_list_view(submission.AllUserSubmissions, 'all_user_submissions_old')),
        url(r'^/submissions/', lambda _, user:
            HttpResponsePermanentRedirect(reverse('all_user_submissions', args=[user]))),

        url(r'^/$', lambda _, user: HttpResponsePermanentRedirect(reverse('user_page', args=[user]))),
    ])),

    url(r'^contests/', paged_list_view(contests.ContestList, 'contest_list')),
    url(r'^contests/(?P<year>\d+)/(?P<month>\d+)/$', contests.ContestCalendar.as_view(), name='contest_calendar'),
    url(r'^contests/tag/(?P<name>[a-z-]+)', include([
        url(r'^$', contests.ContestTagDetail.as_view(), name='contest_tag'),
        url(r'^/ajax$', contests.ContestTagDetailAjax.as_view(), name='contest_tag_ajax'),
    ])),

    url(r'^contest/(?P<contest>\w+)', include([
        url(r'^$', contests.ContestDetail.as_view(), name='contest_view'),
        url(r'^/moss$', contests.ContestMossView.as_view(), name='contest_moss'),
        url(r'^/moss/delete$', contests.ContestMossDelete.as_view(), name='contest_moss_delete'),
        url(r'^/clone$', contests.ContestClone.as_view(), name='contest_clone'),
        url(r'^/ranking/$', contests.ContestRanking.as_view(), name='contest_ranking'),
        url(r'^/ranking/ajax$', contests.contest_ranking_ajax, name='contest_ranking_ajax'),
        url(r'^/join$', contests.ContestJoin.as_view(), name='contest_join'),
        url(r'^/leave$', contests.ContestLeave.as_view(), name='contest_leave'),
        url(r'^/stats$', contests.ContestStats.as_view(), name='contest_stats'),

        url(r'^/rank/(?P<problem>\w+)/',
            paged_list_view(ranked_submission.ContestRankedSubmission, 'contest_ranked_submissions')),

        url(r'^/submissions/(?P<user>\w+)/(?P<problem>\w+)/',
            paged_list_view(submission.UserContestSubmissions, 'contest_user_submissions')),

        url(r'^/participations$', contests.ContestParticipationList.as_view(), name='contest_participation_own'),
        url(r'^/participations/(?P<user>\w+)$',
            contests.ContestParticipationList.as_view(), name='contest_participation'),
        url(r'^/participation/disqualify$', contests.ContestParticipationDisqualify.as_view(),
            name='contest_participation_disqualify'),

        url(r'^/$', lambda _, contest: HttpResponsePermanentRedirect(reverse('contest_view', args=[contest]))),
    ])),

    url(r'^runtimes/$', language.LanguageList.as_view(), name='runtime_list'),
    url(r'^runtimes/matrix/$', status.version_matrix, name='version_matrix'),
    url(r'^status/$', status.status_all, name='status_all'),

    url(r'^blog/', paged_list_view(blog.PostList, 'blog_post_list')),
    url(r'^post/(?P<id>\d+)-(?P<slug>.*)$', blog.PostView.as_view(), name='blog_post'),

    url(r'^license/(?P<key>[-\w.]+)$', license.LicenseDetail.as_view(), name='license'),

    url(r'^widgets/', include([
        url(r'^rejudge$', widgets.rejudge_submission, name='submission_rejudge'),
        url(r'^single_submission$', submission.single_submission_query, name='submission_single_query'),
        url(r'^submission_testcases$', submission.SubmissionTestCaseQuery.as_view(), name='submission_testcases_query'),
        url(r'^detect_timezone$', widgets.DetectTimezone.as_view(), name='detect_timezone'),
        url(r'^status-table$', status.status_table, name='status_table'),

        url(r'^template$', problem.LanguageTemplateAjax.as_view(), name='language_template_ajax'),

        url(r'^select2/', include([
            url(r'^user_search$', UserSearchSelect2View.as_view(), name='user_search_select2_ajax'),
            url(r'^contest_users/(?P<contest>\w+)$', ContestUserSearchSelect2View.as_view(),
                name='contest_user_search_select2_ajax'),
            url(r'^ticket_user$', TicketUserSelect2View.as_view(), name='ticket_user_select2_ajax'),
            url(r'^ticket_assignee$', AssigneeSelect2View.as_view(), name='ticket_assignee_select2_ajax'),
        ])),

        url(r'^preview/', include([
            url(r'^problem$', preview.ProblemMarkdownPreviewView.as_view(), name='problem_preview'),
            url(r'^blog$', preview.BlogMarkdownPreviewView.as_view(), name='blog_preview'),
            url(r'^contest$', preview.ContestMarkdownPreviewView.as_view(), name='contest_preview'),
            url(r'^comment$', preview.CommentMarkdownPreviewView.as_view(), name='comment_preview'),
            url(r'^profile$', preview.ProfileMarkdownPreviewView.as_view(), name='profile_preview'),
            url(r'^organization$', preview.OrganizationMarkdownPreviewView.as_view(), name='organization_preview'),
            url(r'^solution$', preview.SolutionMarkdownPreviewView.as_view(), name='solution_preview'),
            url(r'^license$', preview.LicenseMarkdownPreviewView.as_view(), name='license_preview'),
            url(r'^ticket$', preview.TicketMarkdownPreviewView.as_view(), name='ticket_preview'),
        ])),
    ])),

    url(r'^stats/', include([
        url('^language/', include([
            url('^$', stats.language, name='language_stats'),
            url('^data/all/$', stats.language_data, name='language_stats_data_all'),
            url('^data/ac/$', stats.ac_language_data, name='language_stats_data_ac'),
            url('^data/status/$', stats.status_data, name='stats_data_status'),
            url('^data/ac_rate/$', stats.ac_rate, name='language_stats_data_ac_rate'),
        ])),
    ])),

    url(r'^tickets/', include([
        url(r'^$', ticket.TicketList.as_view(), name='ticket_list'),
        url(r'^ajax$', ticket.TicketListDataAjax.as_view(), name='ticket_ajax'),
    ])),

    url(r'^ticket/(?P<pk>\d+)', include([
        url(r'^$', ticket.TicketView.as_view(), name='ticket'),
        url(r'^/ajax$', ticket.TicketMessageDataAjax.as_view(), name='ticket_message_ajax'),
        url(r'^/open$', ticket.TicketStatusChangeView.as_view(open=True), name='ticket_open'),
        url(r'^/close$', ticket.TicketStatusChangeView.as_view(open=False), name='ticket_close'),
        url(r'^/notes$', ticket.TicketNotesEditView.as_view(), name='ticket_notes'),
    ])),

    url(r'^sitemap\.xml$', sitemap, {'sitemaps': {
        'problem': ProblemSitemap,
        'user': UserSitemap,
        'home': HomePageSitemap,
        'contest': ContestSitemap,
        'blog': BlogPostSitemap,
        'pages': UrlSitemap([
            {'location': '/about/', 'priority': 0.9},
        ]),
    }}),

    url(r'^judge-select2/', include([
        url(r'^profile/$', UserSelect2View.as_view(), name='profile_select2'),
        url(r'^organization/$', OrganizationSelect2View.as_view(), name='organization_select2'),
        url(r'^problem/$', ProblemSelect2View.as_view(), name='problem_select2'),
        url(r'^contest/$', ContestSelect2View.as_view(), name='contest_select2'),
        url(r'^comment/$', CommentSelect2View.as_view(), name='comment_select2'),
    ])),

    url(r'^tasks/', include([
        url(r'^status/(?P<task_id>[A-Za-z0-9-]*)$', tasks.task_status, name='task_status'),
        url(r'^ajax_status$', tasks.task_status_ajax, name='task_status_ajax'),
        url(r'^success$', tasks.demo_success),
        url(r'^failure$', tasks.demo_failure),
        url(r'^progress$', tasks.demo_progress),
    ])),
]

favicon_paths = ['apple-touch-icon-180x180.png', 'apple-touch-icon-114x114.png', 'android-chrome-72x72.png',
                 'apple-touch-icon-57x57.png', 'apple-touch-icon-72x72.png', 'apple-touch-icon.png', 'mstile-70x70.png',
                 'android-chrome-36x36.png', 'apple-touch-icon-precomposed.png', 'apple-touch-icon-76x76.png',
                 'apple-touch-icon-60x60.png', 'android-chrome-96x96.png', 'mstile-144x144.png', 'mstile-150x150.png',
                 'safari-pinned-tab.svg', 'android-chrome-144x144.png', 'apple-touch-icon-152x152.png',
                 'favicon-96x96.png',
                 'favicon-32x32.png', 'favicon-16x16.png', 'android-chrome-192x192.png', 'android-chrome-48x48.png',
                 'mstile-310x150.png', 'apple-touch-icon-144x144.png', 'browserconfig.xml', 'manifest.json',
                 'apple-touch-icon-120x120.png', 'mstile-310x310.png']

for favicon in favicon_paths:
    urlpatterns.append(url(r'^%s$' % favicon, RedirectView.as_view(
        url=lazystr(lambda: static('icons/' + favicon)),
    )))

handler404 = 'judge.views.error.error404'
handler403 = 'judge.views.error.error403'
handler500 = 'judge.views.error.error500'

if 'newsletter' in settings.INSTALLED_APPS:
    urlpatterns.append(url(r'^newsletter/', include('newsletter.urls')))
if 'impersonate' in settings.INSTALLED_APPS:
    urlpatterns.append(url(r'^impersonate/', include('impersonate.urls')))

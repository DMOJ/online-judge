from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.http import Http404, HttpResponsePermanentRedirect
from django.templatetags.static import static
from django.urls import path, reverse, re_path, include
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import RedirectView
from martor.views import markdown_search_user

from judge.feed import AtomBlogFeed, AtomCommentFeed, AtomProblemFeed, BlogFeed, CommentFeed, ProblemFeed
from judge.sitemap import BlogPostSitemap, ContestSitemap, HomePageSitemap, OrganizationSitemap, ProblemSitemap, \
    SolutionSitemap, UrlSitemap, UserSitemap
from judge.views import TitledTemplateView, api, blog, comment, contests, language, license, mailgun, organization, \
    preview, problem, problem_manage, ranked_submission, register, stats, status, submission, tasks, ticket, \
    two_factor, user, widgets
from judge.views.problem_data import ProblemDataView, ProblemSubmissionDiff, \
    problem_data_file, problem_init_view
from judge.views.register import ActivationView, RegistrationView
from judge.views.select2 import AssigneeSelect2View, CommentSelect2View, ContestSelect2View, \
    ContestUserSearchSelect2View, OrganizationSelect2View, ProblemSelect2View, TicketUserSelect2View, \
    UserSearchSelect2View, UserSelect2View
from judge.views.widgets import martor_image_uploader

admin.autodiscover()

register_patterns = [
    path('activate/complete/',
        TitledTemplateView.as_view(template_name='registration/activation_complete.html',
                                   title='Activation Successful!'),
        name='registration_activation_complete'),
    # Activation keys get matched by \w+ instead of the more specific
    # [a-fA-F0-9]{40} because a bad activation key should still get to the view;
    # that way it can return a sensible "invalid key" message instead of a
    # confusing 404.
    re_path(r'^activate/(?P<activation_key>\w+)/$',
        ActivationView.as_view(title='Activation key invalid'),
        name='registration_activate'),
    path('register/',
        RegistrationView.as_view(title='Register'),
        name='registration_register'),
    path('register/complete/',
        TitledTemplateView.as_view(template_name='registration/registration_complete.html',
                                   title='Registration Completed'),
        name='registration_complete'),
    path('register/closed/',
        TitledTemplateView.as_view(template_name='registration/registration_closed.html',
                                   title='Registration not allowed'),
        name='registration_disallowed'),
    path('login/', user.CustomLoginView.as_view(), name='auth_login'),
    path('logout/', user.UserLogoutView.as_view(), name='auth_logout'),
    path('password/change/', user.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password/change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html',
    ), name='password_change_done'),
    path('password/reset/', user.CustomPasswordResetView.as_view(
        template_name='registration/password_reset.html',
        html_email_template_name='registration/password_reset_email.html',
        email_template_name='registration/password_reset_email.txt',
    ), name='password_reset'),
    re_path(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
        ), name='password_reset_confirm'),
    path('password/reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html',
    ), name='password_reset_complete'),
    path('password/reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html',
    ), name='password_reset_done'),
    path('social/error/', register.social_auth_error, name='social_auth_error'),

    path('2fa/', two_factor.TwoFactorLoginView.as_view(), name='login_2fa'),
    path('2fa/enable/', two_factor.TOTPEnableView.as_view(), name='enable_2fa'),
    path('2fa/refresh/', two_factor.TOTPRefreshView.as_view(), name='refresh_2fa'),
    path('2fa/disable/', two_factor.TOTPDisableView.as_view(), name='disable_2fa'),
    path('2fa/webauthn/attest/', two_factor.WebAuthnAttestationView.as_view(), name='webauthn_attest'),
    path('2fa/webauthn/assert/', two_factor.WebAuthnAttestView.as_view(), name='webauthn_assert'),
    re_path(r'^2fa/webauthn/delete/(?P<pk>\d+)$', two_factor.WebAuthnDeleteView.as_view(), name='webauthn_delete'),
    path('2fa/scratchcode/generate/', user.generate_scratch_codes, name='generate_scratch_codes'),

    re_path(r'api/token/generate/$', user.generate_api_token, name='generate_api_token'),
    re_path(r'api/token/remove/$', user.remove_api_token, name='remove_api_token'),
]


def exception(request):
    if not request.user.is_superuser:
        raise Http404()
    raise RuntimeError('@Xyene asked me to cause this')


def paged_list_view(view, name):
    return include([
        path('', view.as_view(), name=name),
        re_path(r'^(?P<page>\d+)$', view.as_view(), name=name),
    ])


urlpatterns = [
    path('', blog.PostList.as_view(template_name='home.html', title=_('Home')), kwargs={'page': 1}, name='home'),
    path('500/', exception),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^i18n/', include('django.conf.urls.i18n')),
    re_path(r'^accounts/', include(register_patterns)),
    re_path(r'^', include('social_django.urls')),

    path('problems/', problem.ProblemList.as_view(), name='problem_list'),
    path('problems/random/', problem.RandomProblem.as_view(), name='problem_random'),

    re_path(r'^problem/(?P<problem>[^/]+)', include([
        path('', problem.ProblemDetail.as_view(), name='problem_detail'),
        path('/editorial', problem.ProblemSolution.as_view(), name='problem_editorial'),
        path('/pdf', problem.ProblemPdfView.as_view(), name='problem_pdf'),
        re_path(r'^/pdf/(?P<language>[a-z-]+)$', problem.ProblemPdfView.as_view(), name='problem_pdf'),
        re_path(r'^/clone', problem.ProblemClone.as_view(), name='problem_clone'),
        path('/submit', problem.ProblemSubmit.as_view(), name='problem_submit'),
        re_path(r'^/resubmit/(?P<submission>\d+)$', problem.ProblemSubmit.as_view(), name='problem_submit'),

        re_path(r'^/rank/', paged_list_view(ranked_submission.RankedSubmissions, 'ranked_submissions')),
        re_path(r'^/submissions/', paged_list_view(submission.ProblemSubmissions, 'chronological_submissions')),
        re_path(r'^/submissions/(?P<user>[\w-]+)/', paged_list_view(submission.UserProblemSubmissions, 'user_submissions')),

        re_path(r'^/$', lambda _, problem: HttpResponsePermanentRedirect(reverse('problem_detail', args=[problem]))),

        path('/test_data', ProblemDataView.as_view(), name='problem_data'),
        path('/test_data/init', problem_init_view, name='problem_data_init'),
        path('/test_data/diff', ProblemSubmissionDiff.as_view(), name='problem_submission_diff'),
        re_path(r'^/data/(?P<path>.+)$', problem_data_file, name='problem_data_file'),

        path('/tickets', ticket.ProblemTicketListView.as_view(), name='problem_ticket_list'),
        path('/tickets/new', ticket.NewProblemTicketView.as_view(), name='new_problem_ticket'),

        re_path(r'^/manage/submission', include([
            path('', problem_manage.ManageProblemSubmissionView.as_view(), name='problem_manage_submissions'),
            path('/rejudge', problem_manage.RejudgeSubmissionsView.as_view(), name='problem_submissions_rejudge'),
            path('/rejudge/preview', problem_manage.PreviewRejudgeSubmissionsView.as_view(),
                name='problem_submissions_rejudge_preview'),
            re_path(r'^/rejudge/success/(?P<task_id>[A-Za-z0-9-]*)$', problem_manage.rejudge_success,
                name='problem_submissions_rejudge_success'),
            path('/rescore/all', problem_manage.RescoreAllSubmissionsView.as_view(),
                name='problem_submissions_rescore_all'),
            re_path(r'^/rescore/success/(?P<task_id>[A-Za-z0-9-]*)$', problem_manage.rescore_success,
                name='problem_submissions_rescore_success'),
        ])),
    ])),

    re_path(r'^submissions/', paged_list_view(submission.AllSubmissions, 'all_submissions')),
    re_path(r'^submissions/user/(?P<user>[\w-]+)/', paged_list_view(submission.AllUserSubmissions, 'all_user_submissions')),

    re_path(r'^src/(?P<submission>\d+)$', submission.SubmissionSource.as_view(), name='submission_source'),
    re_path(r'^src/(?P<submission>\d+)/raw$', submission.SubmissionSourceRaw.as_view(), name='submission_source_raw'),

    re_path(r'^submission/(?P<submission>\d+)', include([
        re_path(r'^$', submission.SubmissionStatus.as_view(), name='submission_status'),
        path('/abort', submission.abort_submission, name='submission_abort'),
    ])),

    re_path(r'^users/', include([
        path('', user.users, name='user_list'),
        re_path(r'^(?P<page>\d+)$', lambda request, page:
            HttpResponsePermanentRedirect('%s?page=%s' % (reverse('user_list'), page))),
        path('find', user.user_ranking_redirect, name='user_ranking_redirect'),
    ])),

    path('user', user.UserAboutPage.as_view(), name='user_page'),
    path('edit/profile/', user.edit_profile, name='user_edit_profile'),
    path('data/prepare/', user.UserPrepareData.as_view(), name='user_prepare_data'),
    path('data/download/', user.UserDownloadData.as_view(), name='user_download_data'),
    re_path(r'^user/(?P<user>[\w-]+)', include([
        path('', user.UserAboutPage.as_view(), name='user_page'),
        re_path(r'^/solved', include([
            path('', user.UserProblemsPage.as_view(), name='user_problems'),
            re_path(r'/ajax$', user.UserPerformancePointsAjax.as_view(), name='user_pp_ajax'),
        ])),
        re_path(r'^/submissions/', paged_list_view(submission.AllUserSubmissions, 'all_user_submissions_old')),
        re_path(r'^/submissions/', lambda _, user:
            HttpResponsePermanentRedirect(reverse('all_user_submissions', args=[user]))),

        re_path(r'^/$', lambda _, user: HttpResponsePermanentRedirect(reverse('user_page', args=[user]))),
    ])),

    path('comments/upvote/', comment.upvote_comment, name='comment_upvote'),
    path('comments/downvote/', comment.downvote_comment, name='comment_downvote'),
    path('comments/hide/', comment.comment_hide, name='comment_hide'),
    re_path(r'^comments/(?P<id>\d+)/', include([
        path('edit', comment.CommentEdit.as_view(), name='comment_edit'),
        path('history/ajax', comment.CommentRevisionAjax.as_view(), name='comment_revision_ajax'),
        path('edit/ajax', comment.CommentEditAjax.as_view(), name='comment_edit_ajax'),
        path('votes/ajax', comment.CommentVotesAjax.as_view(), name='comment_votes_ajax'),
        path('render', comment.CommentContent.as_view(), name='comment_content'),
    ])),

    re_path(r'^contests/', paged_list_view(contests.ContestList, 'contest_list')),
    path('contests.ics', contests.ContestICal.as_view(), name='contest_ical'),
    re_path(r'^contests/(?P<year>\d+)/(?P<month>\d+)/$', contests.ContestCalendar.as_view(), name='contest_calendar'),
    re_path(r'^contests/tag/(?P<name>[a-z-]+)', include([
        path('', contests.ContestTagDetail.as_view(), name='contest_tag'),
        path('/ajax', contests.ContestTagDetailAjax.as_view(), name='contest_tag_ajax'),
    ])),

    re_path(r'^contest/(?P<contest>\w+)', include([
        path('', contests.ContestDetail.as_view(), name='contest_view'),
        path('/moss', contests.ContestMossView.as_view(), name='contest_moss'),
        path('/moss/delete', contests.ContestMossDelete.as_view(), name='contest_moss_delete'),
        path('/clone', contests.ContestClone.as_view(), name='contest_clone'),
        path('/ranking/', contests.ContestRanking.as_view(), name='contest_ranking'),
        path('/ranking/ajax', contests.contest_ranking_ajax, name='contest_ranking_ajax'),
        path('/join', contests.ContestJoin.as_view(), name='contest_join'),
        path('/leave', contests.ContestLeave.as_view(), name='contest_leave'),
        path('/stats', contests.ContestStats.as_view(), name='contest_stats'),

        re_path(r'^/rank/(?P<problem>\w+)/',
            paged_list_view(ranked_submission.ContestRankedSubmission, 'contest_ranked_submissions')),

        re_path(r'^/submissions/(?P<user>[\w-]+)/',
            paged_list_view(submission.UserAllContestSubmissions, 'contest_all_user_submissions')),
        re_path(r'^/submissions/(?P<user>[\w-]+)/(?P<problem>\w+)/',
            paged_list_view(submission.UserContestSubmissions, 'contest_user_submissions')),

        path('/participations', contests.ContestParticipationList.as_view(), name='contest_participation_own'),
        re_path(r'^/participations/(?P<user>[\w-]+)$',
            contests.ContestParticipationList.as_view(), name='contest_participation'),
        path('/participation/disqualify', contests.ContestParticipationDisqualify.as_view(),
            name='contest_participation_disqualify'),

        re_path(r'^/$', lambda _, contest: HttpResponsePermanentRedirect(reverse('contest_view', args=[contest]))),
    ])),

    path('organizations/', organization.OrganizationList.as_view(), name='organization_list'),
    re_path(r'^organization/(?P<pk>\d+)-(?P<slug>[\w-]*)', include([
        path('', organization.OrganizationHome.as_view(), name='organization_home'),
        path('/users', organization.OrganizationUsers.as_view(), name='organization_users'),
        path('/join', organization.JoinOrganization.as_view(), name='join_organization'),
        path('/leave', organization.LeaveOrganization.as_view(), name='leave_organization'),
        path('/edit', organization.EditOrganization.as_view(), name='edit_organization'),
        path('/kick', organization.KickUserWidgetView.as_view(), name='organization_user_kick'),

        path('/request', organization.RequestJoinOrganization.as_view(), name='request_organization'),
        re_path(r'^/request/(?P<rpk>\d+)$', organization.OrganizationRequestDetail.as_view(),
            name='request_organization_detail'),
        re_path(r'^/requests/', include([
            path('pending', organization.OrganizationRequestView.as_view(), name='organization_requests_pending'),
            path('log', organization.OrganizationRequestLog.as_view(), name='organization_requests_log'),
            path('approved', organization.OrganizationRequestLog.as_view(states=('A',), tab='approved'),
                name='organization_requests_approved'),
            path('rejected', organization.OrganizationRequestLog.as_view(states=('R',), tab='rejected'),
                name='organization_requests_rejected'),
        ])),

        re_path(r'^/$', lambda _, pk, slug: HttpResponsePermanentRedirect(reverse('organization_home', args=[pk, slug]))),
    ])),

    path('runtimes/', language.LanguageList.as_view(), name='runtime_list'),
    path('runtimes/matrix/', status.version_matrix, name='version_matrix'),
    path('status/', status.status_all, name='status_all'),

    re_path(r'^api/', include([
        path('contest/list', api.api_v1_contest_list),
        re_path(r'^contest/info/(\w+)$', api.api_v1_contest_detail),
        path('problem/list', api.api_v1_problem_list),
        re_path(r'^problem/info/(\w+)$', api.api_v1_problem_info),
        path('user/list', api.api_v1_user_list),
        re_path(r'^user/info/([\w-]+)$', api.api_v1_user_info),
        re_path(r'^user/submissions/([\w-]+)$', api.api_v1_user_submissions),
        re_path(r'^user/ratings/(\d+)$', api.api_v1_user_ratings),
        re_path(r'^v2/', include([
            path('contests', api.api_v2.APIContestList.as_view()),
            re_path(r'^contest/(?P<contest>\w+)$', api.api_v2.APIContestDetail.as_view()),
            path('problems', api.api_v2.APIProblemList.as_view()),
            re_path(r'^problem/(?P<problem>\w+)$', api.api_v2.APIProblemDetail.as_view()),
            path('users', api.api_v2.APIUserList.as_view()),
            re_path(r'^user/(?P<user>[\w-]+)$', api.api_v2.APIUserDetail.as_view()),
            path('submissions', api.api_v2.APISubmissionList.as_view()),
            re_path(r'^submission/(?P<submission>\d+)$', api.api_v2.APISubmissionDetail.as_view()),
            path('organizations', api.api_v2.APIOrganizationList.as_view()),
            path('participations', api.api_v2.APIContestParticipationList.as_view()),
            path('languages', api.api_v2.APILanguageList.as_view()),
            path('judges', api.api_v2.APIJudgeList.as_view()),
        ])),
    ])),

    re_path(r'^blog/', paged_list_view(blog.PostList, 'blog_post_list')),
    re_path(r'^post/(?P<id>\d+)-(?P<slug>.*)$', blog.PostView.as_view(), name='blog_post'),

    re_path(r'^license/(?P<key>[-\w.]+)$', license.LicenseDetail.as_view(), name='license'),

    path('mailgun/mail_activate/', mailgun.MailgunActivationView.as_view(), name='mailgun_activate'),

    re_path(r'^widgets/', include([
        path('rejudge', widgets.rejudge_submission, name='submission_rejudge'),
        path('single_submission', submission.single_submission, name='submission_single_query'),
        path('submission_testcases', submission.SubmissionTestCaseQuery.as_view(), name='submission_testcases_query'),
        path('detect_timezone', widgets.DetectTimezone.as_view(), name='detect_timezone'),
        path('status-table', status.status_table, name='status_table'),

        path('template', problem.LanguageTemplateAjax.as_view(), name='language_template_ajax'),

        re_path(r'^select2/', include([
            path('user_search', UserSearchSelect2View.as_view(), name='user_search_select2_ajax'),
            re_path(r'^contest_users/(?P<contest>\w+)$', ContestUserSearchSelect2View.as_view(),
                name='contest_user_search_select2_ajax'),
            path('ticket_user', TicketUserSelect2View.as_view(), name='ticket_user_select2_ajax'),
            path('ticket_assignee', AssigneeSelect2View.as_view(), name='ticket_assignee_select2_ajax'),
        ])),

        re_path(r'^preview/', include([
            path('default', preview.DefaultMarkdownPreviewView.as_view(), name='default_preview'),
            path('problem', preview.ProblemMarkdownPreviewView.as_view(), name='problem_preview'),
            path('blog', preview.BlogMarkdownPreviewView.as_view(), name='blog_preview'),
            path('contest', preview.ContestMarkdownPreviewView.as_view(), name='contest_preview'),
            path('comment', preview.CommentMarkdownPreviewView.as_view(), name='comment_preview'),
            path('flatpage', preview.FlatPageMarkdownPreviewView.as_view(), name='flatpage_preview'),
            path('profile', preview.ProfileMarkdownPreviewView.as_view(), name='profile_preview'),
            path('organization', preview.OrganizationMarkdownPreviewView.as_view(), name='organization_preview'),
            path('solution', preview.SolutionMarkdownPreviewView.as_view(), name='solution_preview'),
            path('license', preview.LicenseMarkdownPreviewView.as_view(), name='license_preview'),
            path('ticket', preview.TicketMarkdownPreviewView.as_view(), name='ticket_preview'),
        ])),

        path('martor/', include([
            path('upload-image', martor_image_uploader, name='martor_image_uploader'),
            path('search-user', markdown_search_user, name='martor_search_user'),
        ])),
    ])),

    re_path(r'^feed/', include([
        path('problems/rss/', ProblemFeed(), name='problem_rss'),
        path('problems/atom/', AtomProblemFeed(), name='problem_atom'),
        path('comment/rss/', CommentFeed(), name='comment_rss'),
        path('comment/atom/', AtomCommentFeed(), name='comment_atom'),
        path('blog/rss/', BlogFeed(), name='blog_rss'),
        path('blog/atom/', AtomBlogFeed(), name='blog_atom'),
    ])),

    re_path(r'^stats/', include([
        re_path('^language/', include([
            path('', stats.language, name='language_stats'),
            path('data/all/', stats.language_data, name='language_stats_data_all'),
            path('data/ac/', stats.ac_language_data, name='language_stats_data_ac'),
            path('data/status/', stats.status_data, name='stats_data_status'),
            path('data/ac_rate/', stats.ac_rate, name='language_stats_data_ac_rate'),
        ])),
    ])),

    re_path(r'^tickets/', include([
        path('', ticket.TicketList.as_view(), name='ticket_list'),
        path('ajax', ticket.TicketListDataAjax.as_view(), name='ticket_ajax'),
    ])),

    re_path(r'^ticket/(?P<pk>\d+)', include([
        path('', ticket.TicketView.as_view(), name='ticket'),
        path('/ajax', ticket.TicketMessageDataAjax.as_view(), name='ticket_message_ajax'),
        path('/open', ticket.TicketStatusChangeView.as_view(open=True), name='ticket_open'),
        path('/close', ticket.TicketStatusChangeView.as_view(open=False), name='ticket_close'),
        path('/notes', ticket.TicketNotesEditView.as_view(), name='ticket_notes'),
    ])),

    re_path(r'^sitemap\.xml$', sitemap, {'sitemaps': {
        'problem': ProblemSitemap,
        'user': UserSitemap,
        'home': HomePageSitemap,
        'contest': ContestSitemap,
        'organization': OrganizationSitemap,
        'blog': BlogPostSitemap,
        'solutions': SolutionSitemap,
        'pages': UrlSitemap([
            {'location': '/about/', 'priority': 0.9},
        ]),
    }}),

    re_path(r'^judge-select2/', include([
        path('profile/', UserSelect2View.as_view(), name='profile_select2'),
        path('organization/', OrganizationSelect2View.as_view(), name='organization_select2'),
        path('problem/', ProblemSelect2View.as_view(), name='problem_select2'),
        path('contest/', ContestSelect2View.as_view(), name='contest_select2'),
        path('comment/', CommentSelect2View.as_view(), name='comment_select2'),
    ])),

    re_path(r'^tasks/', include([
        re_path(r'^status/(?P<task_id>[A-Za-z0-9-]*)$', tasks.task_status, name='task_status'),
        path('ajax_status', tasks.task_status_ajax, name='task_status_ajax'),
        path('success', tasks.demo_success),
        path('failure', tasks.demo_failure),
        path('progress', tasks.demo_progress),
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

static_lazy = lazy(static, str)
for favicon in favicon_paths:
    urlpatterns.append(re_path(r'^%s$' % favicon, RedirectView.as_view(
        url=static_lazy('icons/' + favicon),
    )))

handler404 = 'judge.views.error.error404'
handler403 = 'judge.views.error.error403'
handler500 = 'judge.views.error.error500'

if 'newsletter' in settings.INSTALLED_APPS:
    urlpatterns.append(re_path(r'^newsletter/', include('newsletter.urls')))
if 'impersonate' in settings.INSTALLED_APPS:
    urlpatterns.append(re_path(r'^impersonate/', include('impersonate.urls')))

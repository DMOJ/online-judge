from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.http import Http404, HttpResponsePermanentRedirect
from django.templatetags.static import static
from django.urls import include, path, re_path, reverse
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import RedirectView
from martor.views import markdown_search_user

from judge.feed import AtomBlogFeed, AtomCommentFeed, AtomProblemFeed, BlogFeed, CommentFeed, ProblemFeed
from judge.sitemap import sitemaps
from judge.views import TitledTemplateView, api, blog, comment, contests, language, license, mailgun, organization, \
    preview, problem, problem_manage, ranked_submission, register, stats, status, submission, tasks, ticket, \
    two_factor, user, widgets
from judge.views.problem_data import ProblemDataView, ProblemSubmissionDiff, \
    problem_data_file, problem_init_view
from judge.views.register import ActivationView, RegistrationView
from judge.views.select2 import AssigneeSelect2View, ClassSelect2View, CommentSelect2View, ContestSelect2View, \
    ContestUserSearchSelect2View, OrganizationSelect2View, ProblemSelect2View, TicketUserSelect2View, \
    UserSearchSelect2View, UserSelect2View
from judge.views.widgets import martor_image_uploader

admin.autodiscover()

register_patterns = [
    path('activate/complete/',
         TitledTemplateView.as_view(template_name='registration/activation_complete.html',
                                    title=_('Activation Successful!')),
         name='registration_activation_complete'),
    # Let's use <str:activation_key>, because a bad activation key should still get to the view;
    # that way, it can return a sensible "invalid key" message instead of a confusing 404.
    path('activate/<str:activation_key>/', ActivationView.as_view(), name='registration_activate'),
    path('register/', RegistrationView.as_view(), name='registration_register'),
    path('register/complete/',
         TitledTemplateView.as_view(template_name='registration/registration_complete.html',
                                    title=_('Registration Completed')),
         name='registration_complete'),
    path('register/closed/',
         TitledTemplateView.as_view(template_name='registration/registration_closed.html',
                                    title=_('Registration Not Allowed')),
         name='registration_disallowed'),
    path('login/', user.CustomLoginView.as_view(), name='auth_login'),
    path('logout/', user.UserLogoutView.as_view(), name='auth_logout'),
    path('password/change/', user.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password/change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html',
    ), name='password_change_done'),
    path('password/reset/', user.CustomPasswordResetView.as_view(), name='password_reset'),
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
    path('email/change/', user.EmailChangeRequestView.as_view(), name='email_change'),
    path('email/change/activate/<str:activation_key>/',
         user.EmailChangeActivateView.as_view(), name='email_change_activate'),

    path('2fa/', two_factor.TwoFactorLoginView.as_view(), name='login_2fa'),
    path('2fa/enable/', two_factor.TOTPEnableView.as_view(), name='enable_2fa'),
    path('2fa/refresh/', two_factor.TOTPRefreshView.as_view(), name='refresh_2fa'),
    path('2fa/disable/', two_factor.TOTPDisableView.as_view(), name='disable_2fa'),
    path('2fa/webauthn/attest/', two_factor.WebAuthnAttestationView.as_view(), name='webauthn_attest'),
    path('2fa/webauthn/assert/', two_factor.WebAuthnAttestView.as_view(), name='webauthn_assert'),
    path('2fa/webauthn/delete/<int:pk>', two_factor.WebAuthnDeleteView.as_view(), name='webauthn_delete'),
    path('2fa/scratchcode/generate/', user.generate_scratch_codes, name='generate_scratch_codes'),

    path('api/token/generate/', user.generate_api_token, name='generate_api_token'),
    path('api/token/remove/', user.remove_api_token, name='remove_api_token'),
]


def exception(request):
    if not request.user.is_superuser:
        raise Http404()
    raise RuntimeError('@Xyene asked me to cause this')


def paged_list_view(view, name):
    return include([
        path('', view.as_view(), name=name),
        path('<int:page>', view.as_view(), name=name),
    ])


urlpatterns = [
    path('', blog.PostList.as_view(template_name='home.html', title=_('Home')), kwargs={'page': 1}, name='home'),
    path('500/', exception),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('accounts/', include(register_patterns)),
    path('', include('social_django.urls')),

    path('problems/', problem.ProblemList.as_view(), name='problem_list'),
    path('problems/random/', problem.RandomProblem.as_view(), name='problem_random'),

    path('problem/<str:problem>', include([
        path('', problem.ProblemDetail.as_view(), name='problem_detail'),
        path('/editorial', problem.ProblemSolution.as_view(), name='problem_editorial'),
        path('/pdf', problem.ProblemPdfView.as_view(), name='problem_pdf'),
        path('/pdf/<slug:language>', problem.ProblemPdfView.as_view(), name='problem_pdf'),
        path('/clone', problem.ProblemClone.as_view(), name='problem_clone'),
        path('/submit', problem.ProblemSubmit.as_view(), name='problem_submit'),
        path('/resubmit/<int:submission>', problem.ProblemSubmit.as_view(), name='problem_submit'),

        path('/rank/', paged_list_view(ranked_submission.RankedSubmissions, 'ranked_submissions')),
        path('/submissions/', paged_list_view(submission.ProblemSubmissions, 'chronological_submissions')),
        path('/submissions/<str:user>/', paged_list_view(submission.UserProblemSubmissions, 'user_submissions')),

        path('/', lambda _, problem: HttpResponsePermanentRedirect(reverse('problem_detail', args=[problem]))),

        path('/test_data', ProblemDataView.as_view(), name='problem_data'),
        path('/test_data/init', problem_init_view, name='problem_data_init'),
        path('/test_data/diff', ProblemSubmissionDiff.as_view(), name='problem_submission_diff'),
        path('/data/<path:path>', problem_data_file, name='problem_data_file'),

        path('/tickets', ticket.ProblemTicketListView.as_view(), name='problem_ticket_list'),
        path('/tickets/new', ticket.NewProblemTicketView.as_view(), name='new_problem_ticket'),

        path('/vote', problem.ProblemVote.as_view(), name='problem_vote'),
        path('/vote/delete', problem.DeleteProblemVote.as_view(), name='delete_problem_vote'),
        path('/vote/stats', problem.ProblemVoteStats.as_view(), name='problem_vote_stats'),

        path('/manage/submission', include([
            path('', problem_manage.ManageProblemSubmissionView.as_view(), name='problem_manage_submissions'),
            path('/rejudge', problem_manage.RejudgeSubmissionsView.as_view(), name='problem_submissions_rejudge'),
            path('/rejudge/preview', problem_manage.PreviewRejudgeSubmissionsView.as_view(),
                 name='problem_submissions_rejudge_preview'),
            path('/rejudge/success/<slug:task_id>', problem_manage.rejudge_success,
                 name='problem_submissions_rejudge_success'),
            path('/rescore/all', problem_manage.RescoreAllSubmissionsView.as_view(),
                 name='problem_submissions_rescore_all'),
            path('/rescore/success/<slug:task_id>', problem_manage.rescore_success,
                 name='problem_submissions_rescore_success'),
        ])),
    ])),

    path('submissions/', paged_list_view(submission.AllSubmissions, 'all_submissions')),
    path('submissions/user/<str:user>/', paged_list_view(submission.AllUserSubmissions, 'all_user_submissions')),

    path('src/<int:submission>', submission.SubmissionSource.as_view(), name='submission_source'),
    path('src/<int:submission>/raw', submission.SubmissionSourceRaw.as_view(), name='submission_source_raw'),

    path('submission/<int:submission>', include([
        path('', submission.SubmissionStatus.as_view(), name='submission_status'),
        path('/abort', submission.abort_submission, name='submission_abort'),
    ])),

    path('users/', include([
        path('', user.users, name='user_list'),
        path('<int:page>', lambda request, page:
             HttpResponsePermanentRedirect('%s?page=%s' % (reverse('user_list'), page))),
        path('find', user.user_ranking_redirect, name='user_ranking_redirect'),
    ])),

    path('user', user.UserAboutPage.as_view(), name='user_page'),
    path('edit/profile/', user.edit_profile, name='user_edit_profile'),
    path('data/prepare/', user.UserPrepareData.as_view(), name='user_prepare_data'),
    path('data/download/', user.UserDownloadData.as_view(), name='user_download_data'),
    path('user/<str:user>', include([
        path('', user.UserAboutPage.as_view(), name='user_page'),
        path('/solved', include([
            path('', user.UserProblemsPage.as_view(), name='user_problems'),
            path('/ajax', user.UserPerformancePointsAjax.as_view(), name='user_pp_ajax'),
        ])),
        path('/submissions/', paged_list_view(submission.AllUserSubmissions, 'all_user_submissions_old')),
        path('/submissions/', lambda _, user:
             HttpResponsePermanentRedirect(reverse('all_user_submissions', args=[user]))),

        path('/', lambda _, user: HttpResponsePermanentRedirect(reverse('user_page', args=[user]))),
    ])),

    path('comments/upvote/', comment.upvote_comment, name='comment_upvote'),
    path('comments/downvote/', comment.downvote_comment, name='comment_downvote'),
    path('comments/hide/', comment.comment_hide, name='comment_hide'),
    path('comments/<int:id>/', include([
        path('edit', comment.CommentEdit.as_view(), name='comment_edit'),
        path('history/ajax', comment.CommentRevisionAjax.as_view(), name='comment_revision_ajax'),
        path('edit/ajax', comment.CommentEditAjax.as_view(), name='comment_edit_ajax'),
        path('votes/ajax', comment.CommentVotesAjax.as_view(), name='comment_votes_ajax'),
        path('render', comment.CommentContent.as_view(), name='comment_content'),
    ])),

    path('contests/', paged_list_view(contests.ContestList, 'contest_list')),
    path('contests.ics', contests.ContestICal.as_view(), name='contest_ical'),
    path('contests/<int:year>/<int:month>/', contests.ContestCalendar.as_view(), name='contest_calendar'),
    re_path(r'^contests/tag/(?P<name>[a-z-]+)', include([
        path('', contests.ContestTagDetail.as_view(), name='contest_tag'),
        path('/ajax', contests.ContestTagDetailAjax.as_view(), name='contest_tag_ajax'),
    ])),

    path('contest/<str:contest>', include([
        path('', contests.ContestDetail.as_view(), name='contest_view'),
        path('/moss', contests.ContestMossView.as_view(), name='contest_moss'),
        path('/moss/delete', contests.ContestMossDelete.as_view(), name='contest_moss_delete'),
        path('/clone', contests.ContestClone.as_view(), name='contest_clone'),
        path('/ranking/', contests.ContestRanking.as_view(), name='contest_ranking'),
        path('/ranking/ajax', contests.contest_ranking_ajax, name='contest_ranking_ajax'),
        path('/join', contests.ContestJoin.as_view(), name='contest_join'),
        path('/leave', contests.ContestLeave.as_view(), name='contest_leave'),
        path('/stats', contests.ContestStats.as_view(), name='contest_stats'),

        path('/rank/<str:problem>/',
             paged_list_view(ranked_submission.ContestRankedSubmission, 'contest_ranked_submissions')),

        path('/submissions/<str:user>/',
             paged_list_view(submission.UserAllContestSubmissions, 'contest_all_user_submissions')),
        path('/submissions/<str:user>/<str:problem>/',
             paged_list_view(submission.UserContestSubmissions, 'contest_user_submissions')),

        path('/participations', contests.ContestParticipationList.as_view(), name='contest_participation_own'),
        path('/participations/<str:user>',
             contests.ContestParticipationList.as_view(), name='contest_participation'),
        path('/participation/disqualify', contests.ContestParticipationDisqualify.as_view(),
             name='contest_participation_disqualify'),

        path('/', lambda _, contest: HttpResponsePermanentRedirect(reverse('contest_view', args=[contest]))),
    ])),

    path('organizations/', organization.OrganizationList.as_view(), name='organization_list'),
    path('organization/<int:pk>-<slug:slug>', include([
        path('', organization.OrganizationHome.as_view(), name='organization_home'),
        path('/users', organization.OrganizationUsers.as_view(), name='organization_users'),
        path('/join', organization.JoinOrganization.as_view(), name='join_organization'),
        path('/leave', organization.LeaveOrganization.as_view(), name='leave_organization'),
        path('/edit', organization.EditOrganization.as_view(), name='edit_organization'),
        path('/kick', organization.KickUserWidgetView.as_view(), name='organization_user_kick'),

        path('/request', organization.RequestJoinOrganization.as_view(), name='request_organization'),
        path('/request/<int:rpk>', organization.OrganizationRequestDetail.as_view(),
             name='request_organization_detail'),
        path('/requests/', include([
            path('pending', organization.OrganizationRequestView.as_view(), name='organization_requests_pending'),
            path('log', organization.OrganizationRequestLog.as_view(), name='organization_requests_log'),
            path('approved', organization.OrganizationRequestLog.as_view(states=('A',), tab='approved'),
                 name='organization_requests_approved'),
            path('rejected', organization.OrganizationRequestLog.as_view(states=('R',), tab='rejected'),
                 name='organization_requests_rejected'),
        ])),

        path('/class/<int:cpk>-<slug:cslug>', include([
            path('', organization.ClassHome.as_view(), name='class_home'),
            path('/join', organization.RequestJoinClass.as_view(), name='class_join'),
        ])),

        path('/', lambda _, pk, slug: HttpResponsePermanentRedirect(reverse('organization_home', args=[pk, slug]))),
    ])),

    path('runtimes/', language.LanguageList.as_view(), name='runtime_list'),
    path('runtimes/matrix/', status.version_matrix, name='version_matrix'),
    path('status/', status.status_all, name='status_all'),

    path('api/v2/', include([
        path('contests', api.api_v2.APIContestList.as_view()),
        path('contest/<str:contest>', api.api_v2.APIContestDetail.as_view()),
        path('problems', api.api_v2.APIProblemList.as_view()),
        path('problem/<str:problem>', api.api_v2.APIProblemDetail.as_view()),
        path('users', api.api_v2.APIUserList.as_view()),
        path('user/<str:user>', api.api_v2.APIUserDetail.as_view()),
        path('submissions', api.api_v2.APISubmissionList.as_view()),
        path('submission/<int:submission>', api.api_v2.APISubmissionDetail.as_view()),
        path('organizations', api.api_v2.APIOrganizationList.as_view()),
        path('participations', api.api_v2.APIContestParticipationList.as_view()),
        path('languages', api.api_v2.APILanguageList.as_view()),
        path('judges', api.api_v2.APIJudgeList.as_view()),
    ])),

    path('blog/', paged_list_view(blog.PostList, 'blog_post_list')),
    path('post/<int:id>-<slug:slug>', blog.PostView.as_view(), name='blog_post'),

    path('license/<str:key>', license.LicenseDetail.as_view(), name='license'),

    path('mailgun/mail_activate/', mailgun.MailgunActivationView.as_view(), name='mailgun_activate'),

    path('widgets/', include([
        path('rejudge', widgets.rejudge_submission, name='submission_rejudge'),
        path('single_submission', submission.single_submission, name='submission_single_query'),
        path('submission_testcases', submission.SubmissionTestCaseQuery.as_view(), name='submission_testcases_query'),
        path('status-table', status.status_table, name='status_table'),

        path('template', problem.LanguageTemplateAjax.as_view(), name='language_template_ajax'),

        path('select2/', include([
            path('user_search', UserSearchSelect2View.as_view(), name='user_search_select2_ajax'),
            path('contest_users/<str:contest>', ContestUserSearchSelect2View.as_view(),
                 name='contest_user_search_select2_ajax'),
            path('ticket_user', TicketUserSelect2View.as_view(), name='ticket_user_select2_ajax'),
            path('ticket_assignee', AssigneeSelect2View.as_view(), name='ticket_assignee_select2_ajax'),
        ])),

        path('preview/', include([
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

    path('feed/', include([
        path('problems/rss/', ProblemFeed(), name='problem_rss'),
        path('problems/atom/', AtomProblemFeed(), name='problem_atom'),
        path('comment/rss/', CommentFeed(), name='comment_rss'),
        path('comment/atom/', AtomCommentFeed(), name='comment_atom'),
        path('blog/rss/', BlogFeed(), name='blog_rss'),
        path('blog/atom/', AtomBlogFeed(), name='blog_atom'),
    ])),

    path('stats/', include([
        path('language/', include([
            path('', stats.language, name='language_stats'),
            path('data/all/', stats.language_data, name='language_stats_data_all'),
            path('data/ac/', stats.ac_language_data, name='language_stats_data_ac'),
            path('data/status/', stats.status_data, name='stats_data_status'),
            path('data/ac_rate/', stats.ac_rate, name='language_stats_data_ac_rate'),
        ])),
    ])),

    path('tickets/', include([
        path('', ticket.TicketList.as_view(), name='ticket_list'),
        path('ajax', ticket.TicketListDataAjax.as_view(), name='ticket_ajax'),
    ])),

    path('ticket/<int:pk>', include([
        path('', ticket.TicketView.as_view(), name='ticket'),
        path('/ajax', ticket.TicketMessageDataAjax.as_view(), name='ticket_message_ajax'),
        path('/open', ticket.TicketStatusChangeView.as_view(open=True), name='ticket_open'),
        path('/close', ticket.TicketStatusChangeView.as_view(open=False), name='ticket_close'),
        path('/notes', ticket.TicketNotesEditView.as_view(), name='ticket_notes'),
    ])),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}),

    path('judge-select2/', include([
        path('profile/', UserSelect2View.as_view(), name='profile_select2'),
        path('organization/', OrganizationSelect2View.as_view(), name='organization_select2'),
        path('class/', ClassSelect2View.as_view(), name='class_select2'),
        path('problem/', ProblemSelect2View.as_view(), name='problem_select2'),
        path('contest/', ContestSelect2View.as_view(), name='contest_select2'),
        path('comment/', CommentSelect2View.as_view(), name='comment_select2'),
    ])),

    path('tasks/', include([
        path('status/<slug:task_id>', tasks.task_status, name='task_status'),
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
    urlpatterns.append(path(favicon, RedirectView.as_view(
        url=static_lazy('icons/' + favicon),
    )))

handler404 = 'judge.views.error.error404'
handler403 = 'judge.views.error.error403'
handler500 = 'judge.views.error.error500'

if 'newsletter' in settings.INSTALLED_APPS:
    urlpatterns.append(path('newsletter/', include('newsletter.urls')))
if 'impersonate' in settings.INSTALLED_APPS:
    urlpatterns.append(path('impersonate/', include('impersonate.urls')))

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from judge import views
from judge.views import organization, language, status, blog, problem
from judge.ordered_model import urls as ordered_model_urls

from judge.views import RegistrationView, ActivationView, TemplateView
from judge.sitemap import ProblemSitemap, UserSitemap, HomePageSitemap, UrlSitemap, ContestSitemap, OrganizationSitemap, \
    BlogPostSitemap

admin.autodiscover()

register_patterns = patterns('',
    url(r'^activate/complete/$',
        TemplateView.as_view(template_name='registration/activation_complete.jade',
                             title='Activation Successful!'),
        name='registration_activation_complete'),
    # Activation keys get matched by \w+ instead of the more specific
    # [a-fA-F0-9]{40} because a bad activation key should still get to the view;
    # that way it can return a sensible "invalid key" message instead of a
    # confusing 404.
    url(r'^activate/(?P<activation_key>\w+)/$',
        ActivationView.as_view(title='Activation key invalid'),
        name='registration_activate'),
    url(r'^register/$',
        RegistrationView.as_view(title='Register'),
        name='registration_register'),
    url(r'^register/complete/$',
        TemplateView.as_view(template_name='registration/registration_complete.jade',
                             title='Registration Completed'),
        name='registration_complete'),
    url(r'^register/closed/$',
        TemplateView.as_view(template_name='registration/registration_closed.html',
                             title='Registration not allowed'),
        name='registration_disallowed'),
    url(r'^login/$',
        'django.contrib.auth.views.login',
        {'template_name': 'registration/login.jade', 'extra_context': {'title': 'Login'}},
        name='auth_login'),
    url(r'^logout/$',
        'django.contrib.auth.views.logout',
        {'template_name': 'registration/logout.jade', 'extra_context': {'title': 'You have been successfully logged out.'}},
        name='auth_logout'),
    url(r'^password/change/$',
        'django.contrib.auth.views.password_change',
        {'template_name': 'registration/password_change_form.jade', 'extra_context': {'title': 'Change Password'}},
        name='password_change'),
    url(r'^password/change/done/$',
        'django.contrib.auth.views.password_change_done',
        {'template_name': 'registration/password_change_done.jade', 'extra_context': {'title': 'Password Changed'}},
        name='password_change_done'),
    url(r'^password/reset/$',
        'django.contrib.auth.views.password_reset',
        {'template_name': 'registration/password_reset.jade', 'extra_context': {'title': 'Reset Password'}},
        name='password_reset'),
    url(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        'django.contrib.auth.views.password_reset_confirm',
        {'template_name': 'registration/password_reset_confirm.jade', 'extra_context': {'title': 'Confirm Reset Password'}},
        name='password_reset_confirm'),
    url(r'^password/reset/complete/$',
        'django.contrib.auth.views.password_reset_complete',
        {'template_name': 'registration/password_reset_complete.jade', 'extra_context': {'title': 'Password Reset Complete'}},
        name='password_reset_complete'),
    url(r'^password/reset/done/$',
        'django.contrib.auth.views.password_reset_done',
        {'template_name': 'registration/password_reset_done.jade', 'extra_context': {'title': 'Password Reset Successful'}},
        name='password_reset_done'),
)


def exception(request):
    raise RuntimeError('@Xyene asked me to cause this')


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'dmopc.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', blog.PostList.as_view(template_name='home.jade', title='Home'), kwargs={'page': 1}, name='home'),
    url(r'^500/$', exception),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include(ordered_model_urls)),
    url(r'^accounts/', include(register_patterns)),

    url(r'^users/$', 'judge.views.users'),
    url(r'^user/(\w+)$', 'judge.views.user'),
    url(r'^user$', 'judge.views.user'),
    url(r'^edit/profile/$', 'judge.views.edit_profile'),

    url(r'^problems/$', problem.ProblemList.as_view(), name='problem_list'),
    url(r'^problem/(?P<code>\w+)$', problem.ProblemDetail.as_view(), name='problem_detail'),
    url(r'^problem/(?P<code>\w+)/pdf$', problem.ProblemPdfView.as_view(), name='problem_pdf'),
    url(r'^problem/(?P<code>\w+)/latex$', problem.ProblemLatexView.as_view(), name='problem_latex'),
    url(r'^problem/(?P<code>\w+)/edit', problem.ProblemEdit.as_view(), name='problem_edit'),
    url(r'^problem/(\w+)/submit$', 'judge.views.problem_submit'),
    url(r'^problem/(\w+)/resubmit/(\d+)$', 'judge.views.problem_submit'),

    url(r'^submit/problem/$', 'judge.views.problem_submit'),
    url(r'^rejudge$', 'judge.views.rejudge_submission'),
    url(r'^src/(?P<pk>\d+)$', views.SubmissionSource.as_view(), name='submission_source'),
    url(r'^submission/(?P<pk>\d+)$', views.SubmissionStatus.as_view(), name='submission_status'),
    url(r'^submission/(\d+)/abort$', 'judge.views.abort_submission'),
    url(r'^submission/(\d+)/html$', 'judge.views.single_submission'),

    url(r'^submissions/$', views.AllSubmissions.as_view(), name='all_submissions'),
    url(r'^submissions/(?P<page>\d+)$', views.AllSubmissions.as_view(), name='all_submissions'),

    url(r'^problem/(?P<problem>\w+)/rank/$', views.RankedSubmissions.as_view(), name='ranked_submissions'),
    url(r'^problem/(?P<problem>\w+)/rank/(?P<page>\d+)$', views.RankedSubmissions.as_view(), name='ranked_submissions'),
    url(r'^problem/(?P<problem>\w+)/submissions/$', views.ProblemSubmissions.as_view(), name='chronological_submissions'),
    url(r'^problem/(?P<problem>\w+)/submissions/(?P<page>\d+)$', views.ProblemSubmissions.as_view(), name='chronological_submissions'),

    url(r'^problem/(?P<problem>\w+)/submissions/(?P<user>\w+)/$', views.UserProblemSubmissions.as_view(), name='user_submissions'),
    url(r'^problem/(?P<problem>\w+)/submissions/(?P<user>\w+)/(?P<page>\d+)$', views.UserProblemSubmissions.as_view(), name='user_submissions'),

    url(r'^user/(?P<user>\w+)/submissions/$', views.AllUserSubmissions.as_view(), name='all_user_submissions'),
    url(r'^user/(?P<user>\w+)/submissions/(?P<page>\d+)$', views.AllUserSubmissions.as_view(), name='all_user_submissions'),
    
    url(r'^single_submission', 'judge.views.single_submission_query'),
    url(r'^submission_testcases', 'judge.views.submission_testcases_query'),
    url(r'^statistics_table', 'judge.views.statistics_table_query'),

    url(r'^comments/upvote/$', 'judge.views.upvote_comment'),
    url(r'^comments/downvote/$', 'judge.views.downvote_comment'),

    url(r'^contests/$', views.ContestList.as_view(), name='contest_list'),
    url(r'^contest/(\w+)$', views.ContestDetail.as_view(), name='contest_view'),
    url(r'^contest/(\w+)/ranking/$', 'judge.views.contest_ranking'),
    url(r'^contest/(\w+)/ranking/ajax$', 'judge.views.contest_ranking_ajax'),
    url(r'^contest/(\w+)/join$', 'judge.views.join_contest'),
    url(r'^contest/(\w+)/leave$', 'judge.views.leave_contest'),

    url(r'^contest/(?P<contest>\w+)/rank/(?P<problem>\w+)/$', views.ContestRankedSubmission.as_view(), name='contest_ranked_submissions'),
    url(r'^contest/(?P<contest>\w+)/rank/(?P<problem>\w+)/(?P<page>\d+)$', views.ContestRankedSubmission.as_view(), name='contest_ranked_submissions'),

    url(r'^contest/(?P<contest>\w+)/submissions/(?P<user>\w+)/(?P<problem>\w+)/$', views.UserContestSubmissions.as_view(), name='contest_user_submissions'),
    url(r'^contest/(?P<contest>\w+)/submissions/(?P<user>\w+)/(?P<problem>\w+)/(?P<page>\d+)$', views.UserContestSubmissions.as_view(), name='contest_user_submissions'),
    
    url(r'^organizations/$', organization.OrganizationList.as_view(), name='organization_list'),
    url(r'^organizations/add$', organization.NewOrganization.as_view()),
    url(r'^organization/(?P<key>\w+)$', organization.OrganizationHome.as_view(), name='organization_home'),
    url(r'^organization/(?P<key>\w+)/users$', organization.OrganizationUsers.as_view(), name='organization_users'),
    url(r'^organization/(?P<key>\w+)/join', organization.JoinOrganization.as_view(), name='join_organization'),
    url(r'^organization/(?P<key>\w+)/leave', organization.LeaveOrganization.as_view(), name='leave_organization'),
    url(r'^organization/(?P<key>\w+)/edit', organization.EditOrganization.as_view(), name='edit_organization'),

    url(r'^runtimes/$', language.LanguageList.as_view(), name='runtime_list'),
    url(r'^runtime/(?P<key>\w+)$', language.LanguageDetail.as_view(), name='runtime_info'),
    url(r'^runtime/(?P<key>\w+)/judges$', language.LanguageJudgesAjaxList.as_view(), name='runtime_judge_ajax'),

    url(r'^status/$', 'judge.views.status_all'),
    url(r'^status-table/$', 'judge.views.status_table'),
    url(r'^judge/(?P<name>[\w.]+)$', status.JudgeDetail.as_view(), name='judge_info'),

    url(r'^blog/$', blog.PostList.as_view(), name='blog_post_list'),
    url(r'^blog/(?P<page>\d+)$', blog.PostList.as_view(), name='blog_post_list'),
    url(r'^post/(?P<id>\d+)-(?P<slug>.*)$', blog.PostView.as_view(), name='blog_post'),

    url(r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': {
        'problem': ProblemSitemap,
        'user': UserSitemap,
        'home': HomePageSitemap,
        'contest': ContestSitemap,
        'organization': OrganizationSitemap,
        'blog': BlogPostSitemap,
        'pages': UrlSitemap([
            {'location': '/about/', 'priority': 0.9},
        ]),
    }}),
)

handler404 = 'judge.views.error.error404'
handler403 = 'judge.views.error.error403'
handler500 = 'judge.views.error.error500'

if 'tinymce' in settings.INSTALLED_APPS:
    urlpatterns += patterns('', (r'^tinymce/', include('tinymce.urls')))

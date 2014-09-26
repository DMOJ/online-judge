from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.sitemaps import FlatPageSitemap

from judge.views import RegistrationView, ActivationView, TemplateView
from judge.sitemap import ProblemSitemap, UserSitemap, HomePageSitemap, UrlSitemap

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
        {'extra_context': {'title': 'Change Password'}},
        name='auth_password_change'),
    url(r'^password/change/done/$',
        'django.contrib.auth.views.password_change_done',
        {'extra_context': {'title': 'Password Changed'}},
        name='auth_password_change_done'),
    url(r'^password/reset/$',
        'django.contrib.auth.views.password_reset',
        {'extra_context': {'title': 'Reset Password'}},
        name='auth_password_reset'),
    url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        'django.contrib.auth.views.password_reset_confirm',
        {'extra_context': {'title': 'Confirm Reset Password'}},
        name='auth_password_reset_confirm'),
    url(r'^password/reset/complete/$',
        'django.contrib.auth.views.password_reset_complete',
        {'extra_context': {'title': 'Password Reset'}},
        name='auth_password_reset_complete'),
    url(r'^password/reset/done/$',
        'django.contrib.auth.views.password_reset_done',
        {'extra_context': {'title': 'Password Reset'}},
        name='auth_password_reset_done'),
)


def exception(request):
    raise RuntimeError('@Xyene asked me to cause this')


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'dmopc.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', 'judge.views.home'),
    url(r'^500/$', exception),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include(register_patterns)),
    url(r'^users/$', 'judge.views.users'),
    url(r'^user/(\w+)$', 'judge.views.user'),
    url(r'^user$', 'judge.views.user'),
    url(r'^problems/$', 'judge.views.problems'),
    url(r'^problem/(\w+)$', 'judge.views.problem'),
    url(r'^problem/(\w+)/submit$', 'judge.views.problem_submit'),
    url(r'^problem/(\w+)/resubmit/(\d+)$', 'judge.views.problem_submit'),
    url(r'^submission/(\w+)$', 'judge.views.submission_status'),
    url(r'^submission/(\w+)/abort$', 'judge.views.abort_submission'),
    url(r'^submission/(\w+)/html$', 'judge.views.single_submission'),
    url(r'^single_submission', 'judge.views.single_submission_query'),
    url(r'^submit/problem/$', 'judge.views.problem_submit'),
    url(r'^edit/profile/$', 'judge.views.edit_profile'),
    url(r'^submissions/$', 'judge.views.submissions'),
    url(r'^submissions/(\d+)$', 'judge.views.submissions'),
    url(r'^src/(\d+)$', 'judge.views.submission_source'),
    url(r'^status/$', 'judge.views.status'),
    url(r'^status-table/$', 'judge.views.status_table'),

    url(r'^problem/(\w+)/rank/$', 'judge.views.ranked_submissions'),
    url(r'^problem/(\w+)/rank/(\d+)$', 'judge.views.ranked_submissions'),

    url(r'^problem/(\w+)/submissions/$', 'judge.views.chronological_submissions'),
    url(r'^problem/(\w+)/submissions/(\d+)$', 'judge.views.chronological_submissions'),

    url(r'^problem/(\w+)/submissions/(\w+)/$', 'judge.views.user_submissions'),
    url(r'^problem/(\w+)/submissions/(\w+)/(\d+)$', 'judge.views.user_submissions'),

    url(r'^user/(\w+)/submissions/$', 'judge.views.all_user_submissions'),
    url(r'^user/(\w+)/submissions/(\d+)$', 'judge.views.all_user_submissions'),

    url(r'^comments/upvote/$', 'judge.views.upvote_comment'),
    url(r'^comments/downvote/$', 'judge.views.downvote_comment'),

    url(r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': {
        'problem': ProblemSitemap,
        'user': UserSitemap,
        'home': HomePageSitemap,
        'pages': UrlSitemap([
            {'location': '/about/', 'priority': 1.0},
        ]),
    }}),
)

handler404 = 'judge.views.error.error404'
handler403 = 'judge.views.error.error403'
handler500 = 'judge.views.error.error500'

if 'tinymce' in settings.INSTALLED_APPS:
    urlpatterns += patterns('', (r'^tinymce/', include('tinymce.urls')))

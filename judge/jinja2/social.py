from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django_social_share.templatetags.social_share import post_to_gplus_url, post_to_twitter_url, post_to_facebook_url

from . import registry

SHARES = [
    ('post_to_twitter', 'django_social_share/templatetags/post_to_twitter.html', post_to_twitter_url),
    ('post_to_facebook', 'django_social_share/templatetags/post_to_facebook.html', post_to_facebook_url),
    ('post_to_gplus', 'django_social_share/templatetags/post_to_gplus.html', post_to_gplus_url),
    # For future versions:
    # ('post_to_linkedin', 'django_social_share/templatetags/post_to_linkedin.html', post_to_linkedin_url),
    # ('post_to_reddit', 'django_social_share/templatetags/post_to_reddit.html', post_to_reddit_url),
]


for name, template, url_func in SHARES:
    def func(request, link_text, *args):
        context = {'request': request, 'link_text': link_text}
        context = url_func(context, *args)
        return mark_safe(get_template(template).render(context))
    func.__name__ = name
    registry.function(name, func)

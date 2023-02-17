from django.contrib.auth.models import User
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from judge.models import BlogPost, Contest, Organization, Problem, Solution


class ProblemSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Problem.get_public_problems().values_list('code')

    def location(self, obj):
        return reverse('problem_detail', args=obj)


class UserSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.5

    def items(self):
        return User.objects.values_list('username')

    def location(self, obj):
        return reverse('user_page', args=obj)


class ContestSitemap(Sitemap):
    changefreq = 'hourly'
    priority = 0.7

    def items(self):
        return Contest.objects.filter(is_visible=True, is_private=False,
                                      is_organization_private=False).values_list('key')

    def location(self, obj):
        return reverse('contest_view', args=obj)


class OrganizationSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.5

    def items(self):
        return Organization.objects.values_list('id', 'slug')

    def location(self, obj):
        return reverse('organization_home', args=obj)


class BlogPostSitemap(Sitemap):
    changefreq = 'hourly'
    priority = 0.7

    def items(self):
        return BlogPost.objects.filter(visible=True, publish_on__lte=timezone.now()).values_list('id', 'slug')

    def location(self, obj):
        return reverse('blog_post', args=obj)


class SolutionSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return (Solution.objects.filter(is_public=True, publish_on__lte=timezone.now(),
                                        problem__in=Problem.get_public_problems()).values_list('problem__code'))

    def location(self, obj):
        return reverse('problem_editorial', args=obj)


class HomePageSitemap(Sitemap):
    priority = 1.0
    changefreq = 'hourly'

    def items(self):
        return ['home']

    def location(self, obj):
        return reverse(obj)


class UrlSitemap(Sitemap):
    def __init__(self, pages):
        self.pages = pages

    def items(self):
        return self.pages

    def location(self, obj):
        return obj['location'] if isinstance(obj, dict) else obj

    def priority(self, obj):
        return obj.get('priority', 0.5) if isinstance(obj, dict) else 0.5

    def changefreq(self, obj):
        return obj.get('changefreq', 'daily') if isinstance(obj, dict) else 'daily'


sitemaps = {
    'home': HomePageSitemap,
    'pages': UrlSitemap([
        {'location': '/about/', 'priority': 0.9},
    ]),
    'problem': ProblemSitemap,
    'solutions': SolutionSitemap,
    'blog': BlogPostSitemap,
    'contest': ContestSitemap,
    'organization': OrganizationSitemap,
    'user': UserSitemap,
}

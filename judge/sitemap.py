from django.core.urlresolvers import reverse
from django.contrib.sitemaps import Sitemap
from django.contrib.auth.models import User
from django.utils import timezone
from judge.models import Problem, Organization, Contest, BlogPost, Solution


class ProblemSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return Problem.objects.filter(is_public=True)

    def location(self, obj):
        return reverse('problem_detail', args=(obj.code,))


class UserSitemap(Sitemap):
    changefreq = 'hourly'
    priority = 0.5

    def items(self):
        return User.objects.all()

    def location(self, obj):
        return reverse('judge.views.user', args=(obj.username,))


class ContestSitemap(Sitemap):
    changefreq = 'hourly'
    priority = 0.5

    def items(self):
        return Contest.objects.filter(is_public=True)

    def location(self, obj):
        return reverse('contest_view', args=(obj.key,))


class OrganizationSitemap(Sitemap):
    changefreq = 'hourly'
    priority = 0.5

    def items(self):
        return Organization.objects.all()

    def location(self, obj):
        return reverse('organization_home', args=(obj.key,))


class BlogPostSitemap(Sitemap):
    changefreq = 'hourly'
    priority = 0.7

    def items(self):
        return BlogPost.objects.filter(visible=True, publish_on__lte=timezone.now())

    def location(self, obj):
        return reverse('blog_post', args=(obj.id, obj.slug))


class SolutionSitemap(Sitemap):
    changefreq = 'hourly'
    priority = 0.8

    def items(self):
        return Solution.objects.all()

    def location(self, obj):
        return obj.url


class HomePageSitemap(Sitemap):
    priority = 1.0
    changefreq = 'daily'

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

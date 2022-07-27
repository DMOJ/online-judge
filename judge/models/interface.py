import re

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from judge.models.profile import Profile

__all__ = ['MiscConfig', 'validate_regex', 'NavigationBar', 'BlogPost']


class MiscConfig(models.Model):
    key = models.CharField(max_length=30, verbose_name=_('key'), db_index=True)
    value = models.TextField(verbose_name=_('value'), blank=True)

    def __str__(self):
        return self.key

    class Meta:
        verbose_name = _('configuration item')
        verbose_name_plural = _('miscellaneous configuration')


def validate_regex(regex):
    try:
        re.compile(regex, re.VERBOSE)
    except re.error as e:
        raise ValidationError('Invalid regex: %s' % e.message)


class NavigationBar(MPTTModel):
    class Meta:
        verbose_name = _('navigation item')
        verbose_name_plural = _('navigation bar')

    class MPTTMeta:
        order_insertion_by = ['order']

    order = models.PositiveIntegerField(db_index=True, verbose_name=_('order'))
    key = models.CharField(max_length=10, unique=True, verbose_name=_('identifier'))
    label = models.CharField(max_length=20, verbose_name=_('label'))
    path = models.CharField(max_length=255, verbose_name=_('link path'))
    regex = models.TextField(verbose_name=_('highlight regex'), validators=[validate_regex])
    parent = TreeForeignKey('self', verbose_name=_('parent item'), null=True, blank=True,
                            related_name='children', on_delete=models.CASCADE)

    def __str__(self):
        return self.label

    @property
    def pattern(self, cache={}):
        # A cache with a bad policy is an alias for memory leak
        # Thankfully, there will never be too many regexes to cache.
        if self.regex in cache:
            return cache[self.regex]
        else:
            pattern = cache[self.regex] = re.compile(self.regex, re.VERBOSE)
            return pattern


class BlogPost(models.Model):
    title = models.CharField(verbose_name=_('post title'), max_length=100)
    authors = models.ManyToManyField(Profile, verbose_name=_('authors'), blank=True)
    slug = models.SlugField(verbose_name=_('slug'))
    visible = models.BooleanField(verbose_name=_('public visibility'), default=False)
    sticky = models.BooleanField(verbose_name=_('sticky'), default=False)
    publish_on = models.DateTimeField(verbose_name=_('publish after'))
    content = models.TextField(verbose_name=_('post content'))
    summary = models.TextField(verbose_name=_('post summary'), blank=True)
    og_image = models.CharField(verbose_name=_('OpenGraph image'), default='', max_length=150, blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog_post', args=(self.id, self.slug))

    def can_see(self, user):
        if self.visible and self.publish_on <= timezone.now():
            return True
        return self.is_editable_by(user)

    def is_editable_by(self, user):
        if not user.is_authenticated:
            return False
        if user.has_perm('judge.edit_all_post'):
            return True
        return user.has_perm('judge.change_blogpost') and self.authors.filter(id=user.profile.id).exists()

    class Meta:
        permissions = (
            ('edit_all_post', _('Edit all posts')),
            ('change_post_visibility', _('Edit post visibility')),
        )
        verbose_name = _('blog post')
        verbose_name_plural = _('blog posts')

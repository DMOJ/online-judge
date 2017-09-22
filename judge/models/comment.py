import itertools

from django.contrib.contenttypes.fields import GenericRelation
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from reversion.models import Version

from judge.models.contest import Contest
from judge.models.interface import BlogPost
from judge.models.problem import Problem
from judge.models.profile import Profile

__all__ = ['Comment', 'CommentVote']


class VersionRelation(GenericRelation):
    def __init__(self):
        super(VersionRelation, self).__init__(Version, object_id_field='object_id')

    def get_extra_restriction(self, where_class, alias, remote_alias):
        cond = super(VersionRelation, self).get_extra_restriction(where_class, alias, remote_alias)
        field = self.remote_field.model._meta.get_field('db')
        lookup = field.get_lookup('exact')(field.get_col(remote_alias), 'default')
        cond.add(lookup, 'AND')
        return cond


class Comment(MPTTModel):
    author = models.ForeignKey(Profile, verbose_name=_('commenter'))
    time = models.DateTimeField(verbose_name=_('posted time'), auto_now_add=True)
    page = models.CharField(max_length=30, verbose_name=_('associated Page'), db_index=True,
                            validators=[RegexValidator('^[pc]:[a-z0-9]+$|^b:\d+$|^s:',
                                                       _('Page code must be ^[pc]:[a-z0-9]+$|^b:\d+$'))])
    score = models.IntegerField(verbose_name=_('votes'), default=0)
    title = models.CharField(max_length=200, verbose_name=_('title of comment'), blank=True)
    body = models.TextField(verbose_name=_('body of comment'), max_length=8192)
    hidden = models.BooleanField(verbose_name=_('hide the comment'), default=0)
    parent = TreeForeignKey('self', verbose_name=_('parent'), null=True, blank=True, related_name='replies')
    versions = VersionRelation()

    class Meta:
        verbose_name = _('comment')
        verbose_name_plural = _('comments')

    class MPTTMeta:
        order_insertion_by = ['-time']

    @classmethod
    def most_recent(cls, user, n, batch=None):
        queryset = cls.objects.filter(hidden=False).select_related('author__user') \
            .defer('author__about', 'body').order_by('-id')
        if user.is_superuser:
            return queryset[:n]
        if batch is None:
            batch = 2 * n
        output = []
        for i in itertools.count(0):
            slice = queryset[i * batch:i * batch + batch]
            if not slice:
                break
            for comment in slice:
                if comment.page.startswith('p:'):
                    try:
                        if Problem.objects.get(code=comment.page[2:]).is_accessible_by(user):
                            output.append(comment)
                    except Problem.DoesNotExist:
                        pass
                else:
                    output.append(comment)
                if len(output) >= n:
                    return output
        return output

    @cached_property
    def link(self):
        try:
            link = None
            if self.page.startswith('p:'):
                link = reverse('problem_detail', args=(self.page[2:],))
            elif self.page.startswith('c:'):
                link = reverse('contest_view', args=(self.page[2:],))
            elif self.page.startswith('b:'):
                key = 'blog_slug:%s' % self.page[2:]
                slug = cache.get(key)
                if slug is None:
                    try:
                        slug = BlogPost.objects.get(id=self.page[2:]).slug
                    except ObjectDoesNotExist:
                        slug = ''
                    cache.set(key, slug, 3600)
                link = reverse('blog_post', args=(self.page[2:], slug))
            elif self.page.startswith('s:'):
                link = reverse('problem_editorial', args=(self.page[2:],))
        except:
            link = 'invalid'
        return link

    @cached_property
    def page_title(self):
        try:
            if self.page.startswith('p:'):
                return Problem.objects.values_list('name', flat=True).get(code=self.page[2:])
            elif self.page.startswith('c:'):
                return Contest.objects.values_list('name', flat=True).get(key=self.page[2:])
            elif self.page.startswith('b:'):
                return BlogPost.objects.values_list('title', flat=True).get(id=self.page[2:])
            elif self.page.startswith('s:'):
                return _('Editorial for %s') % Problem.objects.values_list('name', flat=True).get(code=self.page[2:])
            return '<unknown>'
        except ObjectDoesNotExist:
            return '<deleted>'

    def get_absolute_url(self):
        return '%s#comment-%d' % (self.link, self.id)

    def __unicode__(self):
        return '%(page)s by %(user)s' % {'page': self.page, 'user': self.author.user.username}

        # Only use this when queried with
        # .prefetch_related(Prefetch('votes', queryset=CommentVote.objects.filter(voter_id=profile_id)))
        # It's rather stupid to put a query specific property on the model, but the alternative requires
        # digging Django internals, and could not be guaranteed to work forever.
        # Hence it is left here for when the alternative breaks.
        # @property
        # def vote_score(self):
        #    queryset = self.votes.all()
        #    if not queryset:
        #        return 0
        #    return queryset[0].score


class CommentVote(models.Model):
    voter = models.ForeignKey(Profile, related_name='voted_comments')
    comment = models.ForeignKey(Comment, related_name='votes')
    score = models.IntegerField()

    class Meta:
        unique_together = ['voter', 'comment']
        verbose_name = _('comment vote')
        verbose_name_plural = _('comment votes')

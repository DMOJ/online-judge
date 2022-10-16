import itertools

from django.contrib.contenttypes.fields import GenericRelation
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import CASCADE
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from reversion.models import Version

from judge.models.contest import Contest
from judge.models.interface import BlogPost
from judge.models.problem import Problem, Solution
from judge.models.profile import Profile
from judge.utils.cachedict import CacheDict

__all__ = ['Comment', 'CommentLock', 'CommentVote']

comment_validator = RegexValidator(r'^[pcs]:[a-z0-9]+$|^b:\d+$',
                                   _(r'Page code must be ^[pcs]:[a-z0-9]+$|^b:\d+$'))


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
    author = models.ForeignKey(Profile, verbose_name=_('commenter'), on_delete=CASCADE)
    time = models.DateTimeField(verbose_name=_('posted time'), auto_now_add=True)
    page = models.CharField(max_length=30, verbose_name=_('associated page'), db_index=True,
                            validators=[comment_validator])
    score = models.IntegerField(verbose_name=_('votes'), default=0)
    body = models.TextField(verbose_name=_('body of comment'), max_length=8192)
    hidden = models.BooleanField(verbose_name=_('hidden'), default=0)
    parent = TreeForeignKey('self', verbose_name=_('parent'), null=True, blank=True, related_name='replies',
                            on_delete=CASCADE)
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

        problem_cache = CacheDict(lambda code: Problem.objects.defer('description', 'summary').get(code=code))
        solution_cache = CacheDict(lambda code: Solution.objects.defer('content').get(problem__code=code))
        contest_cache = CacheDict(lambda key: Contest.objects.defer('description').get(key=key))
        blog_cache = CacheDict(lambda id: BlogPost.objects.defer('summary', 'content').get(id=id))

        problem_access = CacheDict(lambda code: problem_cache[code].is_accessible_by(user))
        solution_access = CacheDict(lambda code: problem_access[code] and solution_cache[code].is_accessible_by(user))
        contest_access = CacheDict(lambda key: contest_cache[key].is_accessible_by(user))
        blog_access = CacheDict(lambda id: blog_cache[id].can_see(user))

        if batch is None:
            batch = 2 * n
        output = []
        for i in itertools.count(0):
            slice = queryset[i * batch:i * batch + batch]
            if not slice:
                break
            for comment in slice:
                page_key = comment.page[2:]
                try:
                    if comment.page.startswith('p:'):
                        has_access = problem_access[page_key]
                        comment.page_title = problem_cache[page_key].name
                    elif comment.page.startswith('s:'):
                        has_access = solution_access[page_key]
                        comment.page_title = _('Editorial for %s') % problem_cache[page_key].name
                    elif comment.page.startswith('c:'):
                        has_access = contest_access[page_key]
                        comment.page_title = contest_cache[page_key].name
                    elif comment.page.startswith('b:'):
                        has_access = blog_access[page_key]
                        comment.page_title = blog_cache[page_key].title
                    else:
                        has_access = True
                except ObjectDoesNotExist:
                    pass
                else:
                    if has_access:
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
        except Exception:
            link = 'invalid'
        return link

    @classmethod
    def get_page_title(cls, page):
        try:
            if page.startswith('p:'):
                return Problem.objects.values_list('name', flat=True).get(code=page[2:])
            elif page.startswith('c:'):
                return Contest.objects.values_list('name', flat=True).get(key=page[2:])
            elif page.startswith('b:'):
                return BlogPost.objects.values_list('title', flat=True).get(id=page[2:])
            elif page.startswith('s:'):
                return _('Editorial for %s') % Problem.objects.values_list('name', flat=True).get(code=page[2:])
            return '<unknown>'
        except ObjectDoesNotExist:
            return '<deleted>'

    @cached_property
    def page_title(self):
        return self.get_page_title(self.page)

    def is_accessible_by(self, user):
        try:
            if self.page.startswith('p:'):
                return Problem.objects.get(code=self.page[2:]).is_accessible_by(user)
            elif self.page.startswith('s:'):
                return Solution.objects.get(problem__code=self.page[2:]).is_accessible_by(user)
            elif self.page.startswith('c:'):
                return Contest.objects.get(key=self.page[2:]).is_accessible_by(user)
            elif self.page.startswith('b:'):
                return BlogPost.objects.get(id=self.page[2:]).can_see(user)
            else:
                return True
        except ObjectDoesNotExist:
            return False

    def get_absolute_url(self):
        return '%s#comment-%d' % (self.link, self.id)

    def __str__(self):
        return _('%(page)s by %(user)s') % {'page': self.page, 'user': self.author.user.username}

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
    voter = models.ForeignKey(Profile, related_name='voted_comments', on_delete=CASCADE)
    comment = models.ForeignKey(Comment, related_name='votes', on_delete=CASCADE)
    score = models.IntegerField()

    class Meta:
        unique_together = ['voter', 'comment']
        verbose_name = _('comment vote')
        verbose_name_plural = _('comment votes')


class CommentLock(models.Model):
    page = models.CharField(max_length=30, verbose_name=_('associated page'), db_index=True,
                            validators=[comment_validator])

    class Meta:
        permissions = (
            ('override_comment_lock', _('Override comment lock')),
        )
        verbose_name = _('comment lock')
        verbose_name_plural = _('comment locks')

    def __str__(self):
        return str(self.page)

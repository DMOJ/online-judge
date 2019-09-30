from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import CASCADE
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext, gettext_lazy as _
from jsonfield import JSONField

from judge import contest_format
from judge.models.problem import Problem
from judge.models.profile import Organization, Profile
from judge.models.submission import Submission

__all__ = ['Contest', 'ContestTag', 'ContestParticipation', 'ContestProblem', 'ContestSubmission', 'Rating']


class ContestTag(models.Model):
    color_validator = RegexValidator('^#(?:[A-Fa-f0-9]{3}){1,2}$', _('Invalid colour.'))

    name = models.CharField(max_length=20, verbose_name=_('tag name'), unique=True,
                            validators=[RegexValidator(r'^[a-z-]+$', message=_('Lowercase letters and hyphens only.'))])
    color = models.CharField(max_length=7, verbose_name=_('tag colour'), validators=[color_validator])
    description = models.TextField(verbose_name=_('tag description'), blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('contest_tag', args=[self.name])

    @property
    def text_color(self, cache={}):
        if self.color not in cache:
            if len(self.color) == 4:
                r, g, b = [ord(bytes.fromhex(i * 2)) for i in self.color[1:]]
            else:
                r, g, b = [i for i in bytes.fromhex(self.color[1:])]
            cache[self.color] = '#000' if 299 * r + 587 * g + 144 * b > 140000 else '#fff'
        return cache[self.color]

    class Meta:
        verbose_name = _('contest tag')
        verbose_name_plural = _('contest tags')


class Contest(models.Model):
    key = models.CharField(max_length=20, verbose_name=_('contest id'), unique=True,
                           validators=[RegexValidator('^[a-z0-9]+$', _('Contest id must be ^[a-z0-9]+$'))])
    name = models.CharField(max_length=100, verbose_name=_('contest name'), db_index=True)
    organizers = models.ManyToManyField(Profile, help_text=_('These people will be able to edit the contest.'),
                                        related_name='organizers+')
    description = models.TextField(verbose_name=_('description'), blank=True)
    problems = models.ManyToManyField(Problem, verbose_name=_('problems'), through='ContestProblem')
    start_time = models.DateTimeField(verbose_name=_('start time'), db_index=True)
    end_time = models.DateTimeField(verbose_name=_('end time'), db_index=True)
    time_limit = models.DurationField(verbose_name=_('time limit'), blank=True, null=True)
    is_visible = models.BooleanField(verbose_name=_('publicly visible'), default=False,
                                     help_text=_('Should be set even for organization-private contests, where it '
                                                 'determines whether the contest is visible to members of the '
                                                 'specified organizations.'))
    is_rated = models.BooleanField(verbose_name=_('contest rated'), help_text=_('Whether this contest can be rated.'),
                                   default=False)
    hide_scoreboard = models.BooleanField(verbose_name=_('hide scoreboard'),
                                          help_text=_('Whether the scoreboard should remain hidden for the duration '
                                                      'of the contest.'),
                                          default=False)
    use_clarifications = models.BooleanField(verbose_name=_('no comments'),
                                             help_text=_("Use clarification system instead of comments."),
                                             default=True)
    rating_floor = models.IntegerField(verbose_name=('rating floor'), help_text=_('Rating floor for contest'),
                                       null=True, blank=True)
    rating_ceiling = models.IntegerField(verbose_name=('rating ceiling'), help_text=_('Rating ceiling for contest'),
                                         null=True, blank=True)
    rate_all = models.BooleanField(verbose_name=_('rate all'), help_text=_('Rate all users who joined.'), default=False)
    rate_exclude = models.ManyToManyField(Profile, verbose_name=_('exclude from ratings'), blank=True,
                                          related_name='rate_exclude+')
    is_private = models.BooleanField(verbose_name=_('private to specific users'), default=False)
    private_contestants = models.ManyToManyField(Profile, blank=True, verbose_name=_('private contestants'),
                                                 help_text=_('If private, only these users may see the contest'),
                                                 related_name='private_contestants+')
    hide_problem_tags = models.BooleanField(verbose_name=_('hide problem tags'),
                                            help_text=_('Whether problem tags should be hidden by default.'),
                                            default=False)
    run_pretests_only = models.BooleanField(verbose_name=_('run pretests only'),
                                            help_text=_('Whether judges should grade pretests only, versus all '
                                                        'testcases. Commonly set during a contest, then unset '
                                                        'prior to rejudging user submissions when the contest ends.'),
                                            default=False)
    is_organization_private = models.BooleanField(verbose_name=_('private to organizations'), default=False)
    organizations = models.ManyToManyField(Organization, blank=True, verbose_name=_('organizations'),
                                           help_text=_('If private, only these organizations may see the contest'))
    og_image = models.CharField(verbose_name=_('OpenGraph image'), default='', max_length=150, blank=True)
    logo_override_image = models.CharField(verbose_name=_('Logo override image'), default='', max_length=150,
                                           blank=True,
                                           help_text=_('This image will replace the default site logo for users '
                                                       'inside the contest.'))
    tags = models.ManyToManyField(ContestTag, verbose_name=_('contest tags'), blank=True, related_name='contests')
    user_count = models.IntegerField(verbose_name=_('the amount of live participants'), default=0)
    summary = models.TextField(blank=True, verbose_name=_('contest summary'),
                               help_text=_('Plain-text, shown in meta description tag, e.g. for social media.'))
    access_code = models.CharField(verbose_name=_('access code'), blank=True, default='', max_length=255,
                                   help_text=_('An optional code to prompt contestants before they are allowed '
                                               'to join the contest. Leave it blank to disable.'))
    banned_users = models.ManyToManyField(Profile, verbose_name=_('personae non gratae'), blank=True,
                                          help_text=_('Bans the selected users from joining this contest.'))
    format_name = models.CharField(verbose_name=_('contest format'), default='default', max_length=32,
                                   choices=contest_format.choices(), help_text=_('The contest format module to use.'))
    format_config = JSONField(verbose_name=_('contest format configuration'), null=True, blank=True,
                              help_text=_('A JSON object to serve as the configuration for the chosen contest format '
                                          'module. Leave empty to use None. Exact format depends on the contest format '
                                          'selected.'))

    @cached_property
    def format_class(self):
        return contest_format.formats[self.format_name]

    @cached_property
    def format(self):
        return self.format_class(self, self.format_config)

    def clean(self):
        # Django will complain if you didn't fill in start_time or end_time, so we don't have to.
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError('What is this? A contest that ended before it starts?')
        self.format_class.validate(self.format_config)

    def is_in_contest(self, user):
        if user.is_authenticated:
            profile = user.profile
            return profile and profile.current_contest is not None and profile.current_contest.contest == self
        return False

    def can_see_scoreboard(self, user):
        if user.has_perm('judge.see_private_contest'):
            return True
        if user.is_authenticated and self.organizers.filter(id=user.profile.id).exists():
            return True
        if not self.is_visible:
            return False
        if self.start_time is not None and self.start_time > timezone.now():
            return False
        if self.hide_scoreboard and not self.is_in_contest(user) and self.end_time > timezone.now():
            return False
        return True

    @property
    def contest_window_length(self):
        return self.end_time - self.start_time

    @cached_property
    def _now(self):
        # This ensures that all methods talk about the same now.
        return timezone.now()

    @cached_property
    def can_join(self):
        return self.start_time <= self._now

    @property
    def time_before_start(self):
        if self.start_time >= self._now:
            return self.start_time - self._now
        else:
            return None

    @property
    def time_before_end(self):
        if self.end_time >= self._now:
            return self.end_time - self._now
        else:
            return None

    @cached_property
    def ended(self):
        return self.end_time < self._now

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('contest_view', args=(self.key,))

    def update_user_count(self):
        self.user_count = self.users.filter(virtual=0).count()
        self.save()

    @cached_property
    def show_scoreboard(self):
        if self.hide_scoreboard and not self.ended:
            return False
        return True

    def is_accessible_by(self, user):
        # Contest is publicly visible
        if self.is_visible:
            # Contest is not private
            if not self.is_private and not self.is_organization_private:
                return True
            if user.is_authenticated:
                # User is in the organizations it is private to
                if self.organizations.filter(id__in=user.profile.organizations.all()).exists():
                    return True
                # User is in the group of private contestants
                if self.private_contestants.filter(id=user.profile.id).exists():
                    return True

        # If the user can view all contests
        if user.has_perm('judge.see_private_contest'):
            return True

        # If the user is a contest organizer
        if user.has_perm('judge.edit_own_contest') and \
                self.organizers.filter(id=user.profile.id).exists():
            return True

        return False

    update_user_count.alters_data = True

    class Meta:
        permissions = (
            ('see_private_contest', _('See private contests')),
            ('edit_own_contest', _('Edit own contests')),
            ('edit_all_contest', _('Edit all contests')),
            ('clone_contest', _('Clone contest')),
            ('contest_rating', _('Rate contests')),
            ('contest_access_code', _('Contest access codes')),
            ('create_private_contest', _('Create private contests')),
        )
        verbose_name = _('contest')
        verbose_name_plural = _('contests')


class ContestParticipation(models.Model):
    LIVE = 0
    SPECTATE = -1

    contest = models.ForeignKey(Contest, verbose_name=_('associated contest'), related_name='users', on_delete=CASCADE)
    user = models.ForeignKey(Profile, verbose_name=_('user'), related_name='contest_history', on_delete=CASCADE)
    real_start = models.DateTimeField(verbose_name=_('start time'), default=timezone.now, db_column='start')
    score = models.IntegerField(verbose_name=_('score'), default=0, db_index=True)
    cumtime = models.PositiveIntegerField(verbose_name=_('cumulative time'), default=0)
    virtual = models.IntegerField(verbose_name=_('virtual participation id'), default=LIVE,
                                  help_text=_('0 means non-virtual, otherwise the n-th virtual participation'))
    format_data = JSONField(verbose_name=_('contest format specific data'), null=True, blank=True)

    def recompute_results(self):
        self.contest.format.update_participation(self)
    recompute_results.alters_data = True

    @property
    def live(self):
        return self.virtual == self.LIVE

    @property
    def spectate(self):
        return self.virtual == self.SPECTATE

    @cached_property
    def start(self):
        contest = self.contest
        return contest.start_time if contest.time_limit is None and (self.live or self.spectate) else self.real_start

    @cached_property
    def end_time(self):
        contest = self.contest
        if self.spectate:
            return contest.end_time
        if self.virtual:
            if contest.time_limit:
                return self.real_start + contest.time_limit
            else:
                return self.real_start + (contest.end_time - contest.start_time)
        return contest.end_time if contest.time_limit is None else \
            min(self.real_start + contest.time_limit, contest.end_time)

    @cached_property
    def _now(self):
        # This ensures that all methods talk about the same now.
        return timezone.now()

    @property
    def ended(self):
        return self.end_time is not None and self.end_time < self._now

    @property
    def time_remaining(self):
        end = self.end_time
        if end is not None and end >= self._now:
            return end - self._now

    def __str__(self):
        if self.spectate:
            return gettext('%s spectating in %s') % (self.user.username, self.contest.name)
        if self.virtual:
            return gettext('%s in %s, v%d') % (self.user.username, self.contest.name, self.virtual)
        return gettext('%s in %s') % (self.user.username, self.contest.name)

    class Meta:
        verbose_name = _('contest participation')
        verbose_name_plural = _('contest participations')

        unique_together = ('contest', 'user', 'virtual')


class ContestProblem(models.Model):
    problem = models.ForeignKey(Problem, verbose_name=_('problem'), related_name='contests', on_delete=CASCADE)
    contest = models.ForeignKey(Contest, verbose_name=_('contest'), related_name='contest_problems', on_delete=CASCADE)
    points = models.IntegerField(verbose_name=_('points'))
    partial = models.BooleanField(default=True, verbose_name=_('partial'))
    is_pretested = models.BooleanField(default=False, verbose_name=_('is pretested'))
    order = models.PositiveIntegerField(db_index=True, verbose_name=_('order'))
    output_prefix_override = models.IntegerField(verbose_name=_('output prefix length override'), null=True, blank=True)
    max_submissions = models.IntegerField(help_text=_('Maximum number of submissions for this problem, '
                                                      'or 0 for no limit.'), default=0,
                                          validators=[MinValueValidator(0, _('Why include a problem you '
                                                                             'can\'t submit to?'))])

    class Meta:
        unique_together = ('problem', 'contest')
        verbose_name = _('contest problem')
        verbose_name_plural = _('contest problems')


class ContestSubmission(models.Model):
    submission = models.OneToOneField(Submission, verbose_name=_('submission'),
                                      related_name='contest', on_delete=CASCADE)
    problem = models.ForeignKey(ContestProblem, verbose_name=_('problem'), on_delete=CASCADE,
                                related_name='submissions', related_query_name='submission')
    participation = models.ForeignKey(ContestParticipation, verbose_name=_('participation'), on_delete=CASCADE,
                                      related_name='submissions', related_query_name='submission')
    points = models.FloatField(default=0.0, verbose_name=_('points'))
    is_pretest = models.BooleanField(verbose_name=_('is pretested'),
                                     help_text=_('Whether this submission was ran only on pretests.'),
                                     default=False)

    class Meta:
        verbose_name = _('contest submission')
        verbose_name_plural = _('contest submissions')


class Rating(models.Model):
    user = models.ForeignKey(Profile, verbose_name=_('user'), related_name='ratings', on_delete=CASCADE)
    contest = models.ForeignKey(Contest, verbose_name=_('contest'), related_name='ratings', on_delete=CASCADE)
    participation = models.OneToOneField(ContestParticipation, verbose_name=_('participation'),
                                         related_name='rating', on_delete=CASCADE)
    rank = models.IntegerField(verbose_name=_('rank'))
    rating = models.IntegerField(verbose_name=_('rating'))
    volatility = models.IntegerField(verbose_name=_('volatility'))
    last_rated = models.DateTimeField(db_index=True, verbose_name=_('last rated'))

    class Meta:
        unique_together = ('user', 'contest')
        verbose_name = _('contest rating')
        verbose_name_plural = _('contest ratings')

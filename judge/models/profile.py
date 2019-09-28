from operator import mul

from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Max
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from fernet_fields import EncryptedCharField
from sortedm2m.fields import SortedManyToManyField

from judge.models.choices import TIMEZONE, ACE_THEMES, MATH_ENGINES_CHOICES
from judge.ratings import rating_class

__all__ = ['Organization', 'Profile', 'OrganizationRequest']


class EncryptedNullCharField(EncryptedCharField):
    def get_prep_value(self, value):
        if not value:
            return None
        return super(EncryptedNullCharField, self).get_prep_value(value)


class Organization(models.Model):
    name = models.CharField(max_length=128, verbose_name=_('organization title'))
    slug = models.SlugField(max_length=128, verbose_name=_('organization slug'),
                            help_text=_('Organization name shown in URL'))
    short_name = models.CharField(max_length=20, verbose_name=_('short name'),
                                  help_text=_('Displayed beside user name during contests'))
    about = models.TextField(verbose_name=_('organization description'))
    registrant = models.ForeignKey('Profile', verbose_name=_('registrant'), on_delete=models.CASCADE,
                                   related_name='registrant+', help_text=_('User who registered this organization'))
    admins = models.ManyToManyField('Profile', verbose_name=_('administrators'), related_name='admin_of',
                                    help_text=_('Those who can edit this organization'))
    creation_date = models.DateTimeField(verbose_name=_('creation date'), auto_now_add=True)
    is_open = models.BooleanField(verbose_name=_('is open organization?'),
                                  help_text=_('Allow joining organization'), default=True)
    slots = models.IntegerField(verbose_name=_('maximum size'), null=True, blank=True,
                                help_text=_('Maximum amount of users in this organization, '
                                            'only applicable to private organizations'))
    access_code = models.CharField(max_length=7, help_text=_('Student access code'),
                                   verbose_name=_('access code'), null=True, blank=True)

    def __contains__(self, item):
        if isinstance(item, int):
            return self.members.filter(id=item).exists()
        elif isinstance(item, Profile):
            return self.members.filter(id=item.id).exists()
        else:
            raise TypeError('Organization membership test must be Profile or primany key')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('organization_home', args=(self.id, self.slug))

    def get_users_url(self):
        return reverse('organization_users', args=(self.id, self.slug))

    class Meta:
        ordering = ['name']
        permissions = (
            ('organization_admin', 'Administer organizations'),
            ('edit_all_organization', 'Edit all organizations'),
        )
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')


class Profile(models.Model):
    user = models.OneToOneField(User, verbose_name=_('user associated'), on_delete=models.CASCADE)
    about = models.TextField(verbose_name=_('self-description'), null=True, blank=True)
    timezone = models.CharField(max_length=50, verbose_name=_('location'), choices=TIMEZONE,
                                default=getattr(settings, 'DEFAULT_USER_TIME_ZONE', 'America/Toronto'))
    language = models.ForeignKey('Language', verbose_name=_('preferred language'), on_delete=models.CASCADE)
    points = models.FloatField(default=0, db_index=True)
    performance_points = models.FloatField(default=0, db_index=True)
    problem_count = models.IntegerField(default=0, db_index=True)
    ace_theme = models.CharField(max_length=30, choices=ACE_THEMES, default='github')
    last_access = models.DateTimeField(verbose_name=_('last access time'), default=now)
    ip = models.GenericIPAddressField(verbose_name=_('last IP'), blank=True, null=True)
    organizations = SortedManyToManyField(Organization, verbose_name=_('organization'), blank=True,
                                          related_name='members', related_query_name='member')
    display_rank = models.CharField(max_length=10, default='user', verbose_name=_('display rank'),
                                    choices=(('user', 'Normal User'), ('setter', 'Problem Setter'), ('admin', 'Admin')))
    mute = models.BooleanField(verbose_name=_('comment mute'), help_text=_('Some users are at their best when silent.'),
                               default=False)
    is_unlisted = models.BooleanField(verbose_name=_('unlisted user'), help_text=_('User will not be ranked.'),
                                      default=False)
    rating = models.IntegerField(null=True, default=None)
    user_script = models.TextField(verbose_name=_('user script'), default='', blank=True, max_length=65536,
                                   help_text=_('User-defined JavaScript for site customization.'))
    current_contest = models.OneToOneField('ContestParticipation', verbose_name=_('current contest'),
                                           null=True, blank=True, related_name='+', on_delete=models.SET_NULL)
    math_engine = models.CharField(verbose_name=_('math engine'), choices=MATH_ENGINES_CHOICES, max_length=4,
                                   default=getattr(settings, 'MATHOID_DEFAULT_TYPE', 'auto'),
                                   help_text=_('the rendering engine used to render math'))
    is_totp_enabled = models.BooleanField(verbose_name=_('2FA enabled'), default=False,
                                          help_text=_('check to enable TOTP-based two factor authentication'))
    totp_key = EncryptedNullCharField(max_length=32, null=True, blank=True, verbose_name=_('TOTP key'),
                                      help_text=_('32 character base32-encoded key for TOTP'),
                                      validators=[RegexValidator('^$|^[A-Z2-7]{32}$',
                                                                 _('TOTP key must be empty or base32'))])
    notes = models.TextField(verbose_name=_('internal notes'), null=True, blank=True,
                             help_text=_('Notes for administrators regarding this user.'))

    @cached_property
    def organization(self):
        # We do this to take advantage of prefetch_related
        orgs = self.organizations.all()
        return orgs[0] if orgs else None

    @cached_property
    def username(self):
        return self.user.username

    _pp_table = [pow(getattr(settings, 'DMOJ_PP_STEP', 0.95), i)
                 for i in range(getattr(settings, 'DMOJ_PP_ENTRIES', 100))]

    def calculate_points(self, table=_pp_table):
        from judge.models import Problem
        data = (Problem.objects.filter(submission__user=self, submission__points__isnull=False, is_public=True,
                                       is_organization_private=False)
                       .annotate(max_points=Max('submission__points')).order_by('-max_points')
                       .values_list('max_points', flat=True).filter(max_points__gt=0))
        extradata = Problem.objects.filter(submission__user=self, submission__result='AC', is_public=True) \
                           .values('id').distinct().count()
        bonus_function = getattr(settings, 'DMOJ_PP_BONUS_FUNCTION', lambda n: 300 * (1 - 0.997 ** n))
        points = sum(data)
        problems = len(data)
        entries = min(len(data), len(table))
        pp = sum(map(mul, table[:entries], data[:entries])) + bonus_function(extradata)
        if self.points != points or problems != self.problem_count or self.performance_points != pp:
            self.points = points
            self.problem_count = problems
            self.performance_points = pp
            self.save(update_fields=['points', 'problem_count', 'performance_points'])
        return points

    calculate_points.alters_data = True

    def remove_contest(self):
        self.current_contest = None
        self.save()

    remove_contest.alters_data = True

    def update_contest(self):
        contest = self.current_contest
        if contest is not None and contest.ended:
            self.remove_contest()

    update_contest.alters_data = True

    def get_absolute_url(self):
        return reverse('user_page', args=(self.user.username,))

    def __str__(self):
        return self.user.username

    @classmethod
    def get_user_css_class(cls, display_rank, rating, rating_colors=getattr(settings, 'DMOJ_RATING_COLORS', False)):
        if rating_colors:
            return 'rating %s %s' % (rating_class(rating) if rating is not None else 'rate-none', display_rank)
        return display_rank

    @cached_property
    def css_class(self):
        return self.get_user_css_class(self.display_rank, self.rating)

    class Meta:
        permissions = (
            ('test_site', 'Shows in-progress development stuff'),
            ('totp', 'Edit TOTP settings')
        )
        verbose_name = _('user profile')
        verbose_name_plural = _('user profiles')


class OrganizationRequest(models.Model):
    user = models.ForeignKey(Profile, verbose_name=_('user'), related_name='requests', on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, verbose_name=_('organization'), related_name='requests',
                                     on_delete=models.CASCADE)
    time = models.DateTimeField(verbose_name=_('request time'), auto_now_add=True)
    state = models.CharField(max_length=1, verbose_name=_('state'), choices=(
        ('P', 'Pending'),
        ('A', 'Approved'),
        ('R', 'Rejected'),
    ))
    reason = models.TextField(verbose_name=_('reason'))

    class Meta:
        verbose_name = _('organization join request')
        verbose_name_plural = _('organization join requests')

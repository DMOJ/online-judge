import os
import errno

from django.conf import settings
from django.core.cache.utils import make_template_fragment_key
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from .models import Problem, Contest, Submission, Organization, Profile, MiscConfig, Language, Judge, \
    BlogPost, ContestSubmission, Comment, License
from .caching import finished_submission


@receiver(post_save, sender=Problem)
def problem_update(sender, instance, **kwargs):
    cache.delete_many([
        make_template_fragment_key('problem_html', (instance.id, True)),
        make_template_fragment_key('problem_html', (instance.id, False)),
        make_template_fragment_key('problem_authors', (instance.id,)),
        make_template_fragment_key('submission_problem', (instance.id,)),
        make_template_fragment_key('problem_feed', (instance.id,))
    ])
l
    if hasattr(settings, 'PROBLEM_PDF_CACHE'):
        try:
            os.unlink(os.path.join(settings.PROBLEM_PDF_CACHE, '%s.pdf' % instance.code))
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
        try:
            os.unlink(os.path.join(settings.PROBLEM_PDF_CACHE, '%s.log' % instance.code))
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise


@receiver(post_save, sender=Profile)
def profile_update(sender, instance, **kwargs):
    cache.delete_many([make_template_fragment_key('submission_user', (instance.id,)),
                       make_template_fragment_key('user_about', (instance.id,))] +
                      [make_template_fragment_key('org_member_count', (org_id,))
                       for org_id in instance.organizations.values_list('id', flat=True)])


@receiver(post_save, sender=Contest)
def contest_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('contest_html', (instance.id,)))


@receiver(post_save, sender=License)
def license_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('license_html', (instance.id,)))


@receiver(post_save, sender=Language)
def language_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('language_html', (instance.id,)))


@receiver(post_save, sender=Judge)
def judge_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('judge_html', (instance.id,)))


@receiver(post_save, sender=Comment)
def comment_update(sender, instance, **kwargs):
    cache.delete('comment_feed:%d' % instance.id)


@receiver(post_save, sender=BlogPost)
def post_update(sender, instance, **kwargs):
    cache.delete_many([
        make_template_fragment_key('post_summary', (instance.id,)),
        make_template_fragment_key('post_content', (instance.id,)),
        'blog_slug:%d' % instance.id,
        'blog_feed:%d' % instance.id,
    ])


@receiver(post_delete, sender=Submission)
def submission_delete(sender, instance, **kwargs):
    finished_submission(instance)
    instance.user.calculate_points()


@receiver(post_delete, sender=ContestSubmission)
def contest_submission_delete(sender, instance, **kwargs):
    participation = instance.participation
    participation.recalculate_score()


@receiver(post_save, sender=Organization)
def organization_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('organization_html', (instance.id,)))


@receiver(post_save, sender=MiscConfig)
def misc_config_update(sender, instance, **kwargs):
    cache.delete('misc_config:%s' % instance.key)

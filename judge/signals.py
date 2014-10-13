from django.core.cache.utils import make_template_fragment_key
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import Problem, Contest, Submission, SubmissionTestCase


import logging
logger = logging.getLogger('judge.cache')


@receiver(post_save, sender=Problem)
def problem_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('problem_html', (instance.id,)))


@receiver(post_save, sender=Contest)
def contest_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('contest_html', (instance.id,)))


def update_submission(id):
    key = 'version:submission-%d' % id
    cache.add(key, 0)
    cache.incr(key)
    logger.info('Increment: %s', key)


@receiver(post_save, sender=Submission)
def submission_update(sender, instance, **kwargs):
    update_submission(instance.id)


@receiver(post_save, sender=SubmissionTestCase)
def submission_case_update(sender, instance, **kwargs):
    update_submission(instance.submission_id)

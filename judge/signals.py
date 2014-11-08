from django.core.cache.utils import make_template_fragment_key
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import Problem, Contest, Submission, Organization, Profile
from .caching import update_submission


@receiver(post_save, sender=Problem)
def problem_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('problem_html', (instance.id,)))
    cache.delete(make_template_fragment_key('submission_problem', (instance.id,)))
    cache.delete(make_template_fragment_key('problem_list_group', (instance.group_id,)))


@receiver(post_save, sender=Profile)
def profile_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('user_on_rank', (instance.id,)))
    cache.delete(make_template_fragment_key('user_org_on_rank', (instance.id,)))
    cache.delete(make_template_fragment_key('submission_user', (instance.id,)))


@receiver(post_save, sender=Contest)
def contest_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('contest_html', (instance.id,)))


@receiver(post_save, sender=Submission)
def submission_update(sender, instance, **kwargs):
    update_submission(instance.id)


@receiver(post_save, sender=Organization)
def organization_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('organization_html', (instance.id,)))

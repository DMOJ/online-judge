from django.core.cache.utils import make_template_fragment_key
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Problem, Contest, Submission, Organization, Profile, NavigationBar, MiscConfig, Language, Judge, \
    BlogPost, ContestSubmission
from .caching import update_submission, finished_submission


@receiver(post_save, sender=Problem)
def problem_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('problem_html', (instance.id,)))
    cache.delete(make_template_fragment_key('submission_problem', (instance.id,)))


@receiver(post_save, sender=Profile)
def profile_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('user_on_rank', (instance.id,)))
    cache.delete(make_template_fragment_key('user_org_on_rank', (instance.id,)))
    cache.delete(make_template_fragment_key('submission_user', (instance.id,)))
    cache.delete(make_template_fragment_key('org_member_count', (instance.organization_id,)))


@receiver(post_save, sender=Contest)
def contest_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('contest_html', (instance.id,)))


@receiver(post_save, sender=Language)
def language_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('language_html', (instance.id,)))


@receiver(post_save, sender=Judge)
def language_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('judge_html', (instance.id,)))


@receiver(post_save, sender=BlogPost)
def post_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('post_summary', (instance.id,)))
    cache.delete(make_template_fragment_key('post_content', (instance.id,)))


@receiver(post_save, sender=Submission)
def submission_update(sender, instance, **kwargs):
    update_submission(instance.id)


@receiver(post_delete, sender=Submission)
def submission_delete(sender, instance, **kwargs):
    finished_submission(instance)
    instance.user.calculate_points()


@receiver(post_delete, sender=ContestSubmission)
def contest_submission_delete(sender, instance, **kwargs):
    participation = instance.participation
    participation.recalculate_score()
    cache.delete(make_template_fragment_key('conrank_user_prob',
                                            (participation.profile.user_id,
                                             participation.contest_id)))


@receiver(post_save, sender=Organization)
def organization_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('organization_html', (instance.id,)))
    cache.delete_many([make_template_fragment_key('user_org_on_rank', (user,))
                       for user in instance.members.values_list('id', flat=True)])


@receiver(post_save, sender=NavigationBar)
def navigation_update(sender, instance, **kwargs):
    cache.delete('navbar')
    cache.delete('navbar_dict')
    cache.delete(make_template_fragment_key('navbar'))


@receiver(post_save, sender=MiscConfig)
def misc_config_update(sender, instance, **kwargs):
    cache.delete('misc_config:%s' % instance.key)
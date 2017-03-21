from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from judge.models import Problem
from judge.utils.problems import editable_problems


def own_ticket_filter(profile_id):
    return Q(assignees__id=profile_id) | Q(user_id=profile_id)


def filter_visible_tickets(queryset, user, profile=None):
    if profile is None:
        profile = user.profile
    return queryset.filter(own_ticket_filter(profile.id) |
                           Q(content_type=ContentType.objects.get_for_model(Problem),
                             object_id__in=editable_problems(user, profile))).distinct()

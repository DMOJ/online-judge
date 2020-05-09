from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from judge.models import Problem


def own_ticket_filter(profile_id):
    return Q(assignees__id=profile_id) | Q(user_id=profile_id)


def filter_visible_tickets(queryset, user):
    return queryset.filter(own_ticket_filter(user.profile.id) |
                           Q(content_type=ContentType.objects.get_for_model(Problem),
                             object_id__in=Problem.get_editable_problems(user))).distinct()

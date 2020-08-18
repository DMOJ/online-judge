import re

from collections import defaultdict

from django.db.models import Max
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from judge.contest_format.default import DefaultContestFormat
from judge.contest_format.registry import register_contest_format


@register_contest_format('asdan')
class ASDANContestFormat(LegacyIOIContestFormat):
    name = gettext_lazy('ASDAN')
    config_defaults = {'cumtime': True}
    reteam = re.compile(r'(ASDAN_\d+)[ABC]$')
    # Sort by (sum of average team scores per problem, average team score on p2, cumtime)
    # Bastardize the points field because better is the enemy of <<deployed in prod>>
    def update_participation(self, participation):
        from judge.models.contest import ContestParticipation

        points = defaultdict(list)
        cumtimes = defaultdict(list)
        cumtime = 0
        team_points = 0
        format_data = {}
        problem_order = {}

        username = participation.user.user.username
        match = reteam.match(username)
        if match:
            team = [match.group(1) + letter for letter in 'ABC']
            team_participations = list(ContestParticipation.objects.filter(
                user__user__username__in=team,
                contest=participation.contest,
            ))
        else:
            team_participations = [participation]
        team_size = len(team_participations)

        for problem in participation.contest.problems:
            problem_order[problem.id] = problem.order

        for team_participation in team_participations:
            queryset = (team_participation.submissions.values('problem_id')
                                                      .filter(points=Subquery(
                                                          participation.submissions.filter(
                                                              problem_id=OuterRef('problem_id'))
                                                     .order_by('-points').values('points')[:1]))
                                                  .annotate(
                                                      time=Min('submission__date'),
                                                  ).values_list('problem_id', 'time', 'points'))
            for problem_id, sub_time, sub_points in queryset:
                team_points += sub_points
                points[problem_id].append(sub_points)
                cumtime[problem_id].append((sub_time - team_participation.start).total_seconds())

        format_data['real_score'] = team_points

        for problem_id, points_list in points.items():
            points_list_sum = sum(points_list)
            cumtime_max = max(cumtime[problem_id])
            if points_list_sum:
                cumtime += cumtime_max
            format_data[problem_id] = {'points': points_list_sum / team_size, 'time': cumtime_max}
            if problem_order[problem_id] == 1:
                team_points += 100 * points_list_sum

        for team_participation in team_participations:
            team_participation.cumtime = 0
            team_participation.score = team_points * (6 / team_size) # Make things integers because comparing things
            team_participation.tiebreaker = 0
            team_participation.format_data = format_data
            team_participation.save()
    
    def display_participation_result(self, participation):
        return format_html(
            u'<td class="user-points"><a href="{url}">{points}<div class="solving-time">{cumtime}</div></a></td>',
            url=reverse('contest_all_user_submissions',
                        args=[self.contest.key, participation.user.user.username]),
            points=floatformat(participation.format_data['real_score']),
            cumtime=nice_repr(timedelta(seconds=participation.cumtime), 'noday'),
        )
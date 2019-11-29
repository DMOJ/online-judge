from celery import shared_task
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext as _
from moss import MOSS

from judge.models import Contest, ContestMoss, ContestParticipation, Submission
from judge.utils.celery import Progress

__all__ = ('rescore_contest', 'run_moss')


@shared_task(bind=True)
def rescore_contest(self, contest_key):
    contest = Contest.objects.get(key=contest_key)
    participations = contest.users

    rescored = 0
    with Progress(self, participations.count(), stage=_('Recalculating contest scores')) as p:
        for participation in participations.iterator():
            participation.recompute_results()
            rescored += 1
            if rescored % 10 == 0:
                p.done = rescored
    return rescored


@shared_task(bind=True)
def run_moss(self, contest_key):
    moss_api_key = settings.MOSS_API_KEY
    if moss_api_key is None:
        raise ImproperlyConfigured('No MOSS API Key supplied')

    contest = Contest.objects.get(key=contest_key)
    ContestMoss.objects.filter(contest=contest).delete()

    length = len(ContestMoss.LANG_MAPPING) * contest.problems.count()
    moss_results = []

    with Progress(self, length, stage=_('Running MOSS')) as p:
        for problem in contest.problems.all():
            for dmoj_lang, moss_lang in ContestMoss.LANG_MAPPING:
                result = ContestMoss(contest=contest, problem=problem, language=dmoj_lang)

                subs = Submission.objects.filter(
                    contest__participation__virtual__in=(ContestParticipation.LIVE, ContestParticipation.SPECTATE),
                    contest_object=contest,
                    problem=problem,
                    language__common_name=dmoj_lang,
                ).order_by('-points').values_list('user__user__username', 'source__source')

                if subs.exists():
                    moss_call = MOSS(moss_api_key, language=moss_lang, matching_file_limit=100,
                                     comment='%s - %s' % (contest.key, problem.code))

                    users = set()

                    for username, source in subs:
                        if username in users:
                            continue
                        users.add(username)
                        moss_call.add_file_from_memory(username, source.encode('utf-8'))

                    result.url = moss_call.process()
                    result.submission_count = len(users)

                moss_results.append(result)
                p.did(1)

    ContestMoss.objects.bulk_create(moss_results)

    return len(moss_results)

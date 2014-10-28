import logging
from operator import attrgetter
import traceback

logger = logging.getLogger('judge.bridge')


class JudgeList(object):
    def __init__(self):
        self.queue = []
        self.judges = set()
        self.submission_map = {}

    def _handle_free_judge(self, judge):
        for i, elem in enumerate(self.queue):
            id, problem, language, source = elem
            if judge.can_judge(problem, language):
                self.submission_map[id] = judge
                logger.info('Dispatched queued submission %d: %s', id, judge.name)
                try:
                    judge.submit(id, problem, language, source)
                except Exception:
                    traceback.print_exc()
                    self.judges.remove(judge)
                    return
                del self.queue[i]
                break

    def register(self, judge):
        self.judges.add(judge)
        self._handle_free_judge(judge)

    def update_problems(self, judge):
        self._handle_free_judge(judge)

    def remove(self, judge):
        sub = judge.get_current_submission()
        if sub is not None:
            try:
                del self.submission_map[judge.working]
            except KeyError:
                pass
        self.judges.discard(judge)

    def __iter__(self):
        return iter(self.judges)

    def on_judge_free(self, judge, submission):
        logger.info('Judge available after grading %d: %s', submission, judge.name)
        del self.submission_map[submission]
        self._handle_free_judge(judge)

    def abort(self, submission):
        logger.info('Abort request: %d', submission)
        self.submission_map[submission].abort()

    def judge(self, id, problem, language, source):
        if id in self.submission_map:
            logger.warning('Already judging? %d', id)
            return

        candidates = [judge for judge in self.judges if not judge.working and judge.can_judge(problem, language)]
        logger.info('Free judges: %d', len(candidates))
        if candidates:
            judge = min(candidates, key=attrgetter('load'))
            logger.info('Dispatched submission %d to: %s', id, judge.name)
            self.submission_map[id] = judge
            try:
                judge.submit(id, problem, language, source)
            except Exception:
                logger.exception('Failed to dispatch %d (%s, %s) to %s', id, problem, language, judge.name)
                self.judges.discard(judge)
                return self.judge(id, problem, language, source)
        else:
            self.queue.append((id, problem, language, source))
            logger.info('Queued submission: %d', id)

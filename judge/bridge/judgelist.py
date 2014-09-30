import logging
from operator import attrgetter

logger = logging.getLogger('judge.bridge')


class JudgeList(object):
    def __init__(self):
        self.queue = []
        self.judges = []
        self.submission_map = {}

    def _handle_free_judge(self, judge):
        for i, elem in enumerate(self.queue):
            id, problem, language, source = elem
            if judge.can_judge(problem, language):
                self.submission_map[id] = judge
                logger.info('Dispatched queued submission %d: %s', id, judge.name)
                judge.submit(id, problem, language, source)
                del self.queue[i]
                break

    def register(self, judge):
        self.judges.append(judge)
        self._handle_free_judge(judge)

    def remove(self, judge):
        self.judges.remove(judge)

    def __iter__(self):
        return iter(self.judges)

    def on_judge_free(self, judge, submission):
        logger.info('Judge available: %d', submission)
        del self.submission_map[submission]
        self._handle_free_judge(judge)

    def abort(self, submission):
        logger.info('Abort request: %d', submission)
        self.submission_map[submission].abort()

    def judge(self, id, problem, language, source):
        candidates = [judge for judge in self.judges if not judge.working and judge.can_judge(problem, language)]
        logger.info('Free judges: %d', len(candidates))
        if candidates:
            judge = min(candidates, key=attrgetter('load'))
            logger.info('Dispatched submission %d to: %s', id, judge.name)
            self.submission_map[id] = judge
            judge.submit(id, problem, language, source)
        else:
            self.queue.append((id, problem, language, source))
            logger.info('Queued submission: %d', id)

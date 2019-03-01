import logging
from collections import namedtuple
from operator import attrgetter
from threading import RLock

try:
    from llist import dllist
except ImportError:
    from pyllist import dllist

logger = logging.getLogger('judge.bridge')

PriorityMarker = namedtuple('PriorityMarker', 'priority')


class JudgeList(object):
    priorities = 3

    def __init__(self):
        self.queue = dllist()
        self.priority = [self.queue.append(PriorityMarker(i)) for i in range(self.priorities)]
        self.judges = set()
        self.submission_map = {}
        self.lock = RLock()

    def _handle_free_judge(self, judge):
        with self.lock:
            node = self.queue.first
            while node:
                if not isinstance(node.value, PriorityMarker):
                    id, problem, language, source = node.value
                    if judge.can_judge(problem, language):
                        self.submission_map[id] = judge
                        logger.info('Dispatched queued submission %d: %s', id, judge.name)
                        try:
                            judge.submit(id, problem, language, source)
                        except Exception:
                            logger.exception('Failed to dispatch %d (%s, %s) to %s', id, problem, language, judge.name)
                            self.judges.remove(judge)
                            return
                        self.queue.remove(node)
                        break
                node = node.next

    def register(self, judge):
        with self.lock:
            self.judges.add(judge)
            self._handle_free_judge(judge)

    def disconnect(self, judge_id, force=False):
        for judge in self.judges:
            if judge.name == judge_id:
                judge.disconnect(force=force)

    def update_problems(self, judge):
        with self.lock:
            self._handle_free_judge(judge)

    def remove(self, judge):
        with self.lock:
            sub = judge.get_current_submission()
            if sub is not None:
                try:
                    del self.submission_map[sub]
                except KeyError:
                    pass
            self.judges.discard(judge)

    def __iter__(self):
        return iter(self.judges)

    def on_judge_free(self, judge, submission):
        with self.lock:
            logger.info('Judge available after grading %d: %s', submission, judge.name)
            del self.submission_map[submission]
            self._handle_free_judge(judge)

    def abort(self, submission):
        with self.lock:
            logger.info('Abort request: %d', submission)
            self.submission_map[submission].abort()

    def check_priority(self, priority):
        return 0 <= priority < self.priorities

    def judge(self, id, problem, language, source, priority):
        with self.lock:
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
                    return self.judge(id, problem, language, source, priority)
            else:
                self.queue.insert((id, problem, language, source), self.priority[priority])
                logger.info('Queued submission: %d', id)

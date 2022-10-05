import logging
from collections import namedtuple
from random import random
from threading import RLock

from judge.judge_priority import REJUDGE_PRIORITY

try:
    from llist import dllist
except ImportError:
    from pyllist import dllist

logger = logging.getLogger('judge.bridge')

PriorityMarker = namedtuple('PriorityMarker', 'priority')


class JudgeList(object):
    priorities = 4

    def __init__(self):
        self.queue = dllist()
        self.priority = [self.queue.append(PriorityMarker(i)) for i in range(self.priorities)]
        self.judges = set()
        self.node_map = {}
        self.submission_map = {}
        self.lock = RLock()

    def _handle_free_judge(self, judge):
        with self.lock:
            node = self.queue.first
            priority = 0
            while node:
                if isinstance(node.value, PriorityMarker):
                    priority = node.value.priority + 1
                elif priority >= REJUDGE_PRIORITY and self.count_not_disabled() > 1 and sum(
                        not judge.working and not judge.is_disabled for judge in self.judges) <= 1:
                    return
                else:
                    id, problem, language, source, judge_id = node.value
                    if judge.can_judge(problem, language, judge_id):
                        self.submission_map[id] = judge
                        try:
                            judge.submit(id, problem, language, source)
                        except Exception:
                            logger.exception('Failed to dispatch %d (%s, %s) to %s', id, problem, language, judge.name)
                            self.judges.remove(judge)
                            return
                        logger.info('Dispatched queued submission %d: %s', id, judge.name)
                        self.queue.remove(node)
                        del self.node_map[id]
                        break
                node = node.next

    def count_not_disabled(self):
        return sum(not judge.is_disabled for judge in self.judges)

    def register(self, judge):
        with self.lock:
            # Disconnect all judges with the same name, see <https://github.com/DMOJ/online-judge/issues/828>
            self.disconnect(judge, force=True)
            self.judges.add(judge)
            self._handle_free_judge(judge)

    def disconnect(self, judge_id, force=False):
        with self.lock:
            for judge in self.judges:
                if judge.name == judge_id:
                    judge.disconnect(force=force)

    def update_problems(self, judge):
        with self.lock:
            self._handle_free_judge(judge)

    def update_disable_judge(self, judge_id, is_disabled):
        with self.lock:
            for judge in self.judges:
                if judge.name == judge_id:
                    judge.is_disabled = is_disabled

    def remove(self, judge):
        with self.lock:
            sub = judge.get_current_submission()
            if sub is not None:
                try:
                    del self.submission_map[sub]
                except KeyError:
                    pass
            self.judges.discard(judge)

            # Since we reserve a judge for high priority submissions when there are more than one,
            # we'll need to start judging if there is exactly one judge and it's free.
            if len(self.judges) == 1:
                judge = next(iter(self.judges))
                if not judge.working:
                    self._handle_free_judge(judge)

    def __iter__(self):
        return iter(self.judges)

    def on_judge_free(self, judge, submission):
        logger.info('Judge available after grading %d: %s', submission, judge.name)
        with self.lock:
            del self.submission_map[submission]
            judge._working = False
            self._handle_free_judge(judge)

    def abort(self, submission):
        logger.info('Abort request: %d', submission)
        with self.lock:
            try:
                self.submission_map[submission].abort()
                return True
            except KeyError:
                try:
                    node = self.node_map[submission]
                except KeyError:
                    pass
                else:
                    self.queue.remove(node)
                    del self.node_map[submission]
                return False

    def check_priority(self, priority):
        return 0 <= priority < self.priorities

    def judge(self, id, problem, language, source, judge_id, priority):
        with self.lock:
            if id in self.submission_map or id in self.node_map:
                # Already judging, don't queue again. This can happen during batch rejudges, rejudges should be
                # idempotent.
                return

            candidates = [judge for judge in self.judges if judge.can_judge(problem, language, judge_id)]
            available = [judge for judge in candidates if not judge.working and not judge.is_disabled]
            if judge_id:
                logger.info('Specified judge %s is%savailable', judge_id, ' ' if available else ' not ')
            else:
                logger.info('Free judges: %d', len(available))

            if len(candidates) > 1 and len(available) == 1 and priority >= REJUDGE_PRIORITY:
                available = []

            if available:
                # Schedule the submission on the judge reporting least load.
                judge = min(available, key=lambda judge: (judge.load, random()))
                logger.info('Dispatched submission %d to: %s', id, judge.name)
                self.submission_map[id] = judge
                try:
                    judge.submit(id, problem, language, source)
                except Exception:
                    logger.exception('Failed to dispatch %d (%s, %s) to %s', id, problem, language, judge.name)
                    self.judges.discard(judge)
                    return self.judge(id, problem, language, source, judge_id, priority)
            else:
                self.node_map[id] = self.queue.insert(
                    (id, problem, language, source, judge_id),
                    self.priority[priority],
                )
                logger.info('Queued submission: %d', id)

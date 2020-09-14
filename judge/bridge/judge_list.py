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
            while node:
                if not isinstance(node.value, PriorityMarker):
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

            candidates = [
                judge for judge in self.judges if not judge.working and judge.can_judge(problem, language, judge_id)
            ]
            if judge_id:
                logger.info('Specified judge %s is%savailable', judge_id, ' ' if candidates else ' not ')
            else:
                logger.info('Free judges: %d', len(candidates))
            if candidates:
                # Schedule the submission on the judge reporting least load.
                judge = min(candidates, key=attrgetter('load'))
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

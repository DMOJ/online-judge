from operator import attrgetter


class JudgeList(list):
    __slots__ = ('queue',)

    def __init__(self, *args, **kwargs):
        super(JudgeList, self).__init__(*args, **kwargs)
        self.queue = []

    def on_got_problems(self, judge):
        remove = []
        for elem in self.queue:
            id, problem, language, source = elem
            if problem in judge.problems:
                remove.append(elem)
                judge.submit(id, problem, language, source)
        for elem in remove:
            self.queue.remove(elem)

    def judge(self, id, problem, language, source):
        try:
            judge = min((problem in judge.problems for judge in self), key=attrgetter('load'))
        except ValueError:
            self.queue.append((id, problem, language, source))
        else:
            judge.submit(id, problem, language, source)

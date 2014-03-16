from operator import attrgetter


class JudgeList(list):
    def pick_lazy(self):
        return min(self, key=attrgetter('load'))

class Progress:
    def __init__(self, task, total):
        self.task = task
        self._total = total
        self._done = 0

    def _update_state(self):
        self.task.update_state(
            state='PROGRESS',
            meta={
                'done': self._done,
                'total': self._total,
            }
        )

    @property
    def done(self):
        return self._done

    @done.setter
    def done(self, value):
        self._done = value
        self._update_state()

    @property
    def total(self):
        return self._total

    @total.setter
    def total(self, value):
        self._total = value
        self._done = min(self._done, value)
        self._update_state()

    def did(self, delta):
        self._done += delta
        self._update_state()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.done = self._total

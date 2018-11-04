class CacheDict(dict):
    def __init__(self, func):
        super(CacheDict, self).__init__()
        self.func = func

    def __missing__(self, key):
        self[key] = value = self.func(key)
        return value

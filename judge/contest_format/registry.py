formats = {}


def register_contest_format(name):
    def register_class(contest_format_class):
        assert name not in formats
        formats[name] = contest_format_class
        return contest_format_class

    return register_class


def choices():
    return [(key, value.name) for key, value in sorted(formats.items())]

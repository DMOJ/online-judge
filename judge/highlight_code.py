from django.utils.html import escape, mark_safe

__all__ = ['highlight_code']


def _make_pre_code(code):
    return mark_safe('<pre>' + escape(code) + '</pre>')


def _wrap_code(inner):
    yield 0, "<code>"
    for tup in inner:
        yield tup
    yield 0, "</code>"

try:
    import pygments
    import pygments.lexers
    import pygments.formatters.html
    import pygments.util
except ImportError:
    def highlight_code(code, language, cssclass=None):
        return _make_pre_code(code)
else:
    def highlight_code(code, language, cssclass='codehilite'):
        try:
            lexer = pygments.lexers.get_lexer_by_name(language)
        except pygments.util.ClassNotFound:
            return _make_pre_code(code)

        class HtmlCodeFormatter(pygments.formatters.html.HtmlFormatter):
            def wrap(self, source, outfile):
                return self._wrap_div(self._wrap_pre(_wrap_code(source)))

        return mark_safe(pygments.highlight(code, lexer, HtmlCodeFormatter({'cssclass': cssclass})))
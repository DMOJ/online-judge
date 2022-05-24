from django.utils.html import escape, mark_safe

__all__ = ['highlight_code']


def _make_pre_code(code):
    return mark_safe('<pre>' + escape(code) + '</pre>')


try:
    import pygments
    import pygments.lexers
    import pygments.formatters
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

        return mark_safe(
            pygments.highlight(code, lexer, pygments.formatters.HtmlFormatter(cssclass=cssclass, wrapcode=True)),
        )

from django.utils.html import format_html, mark_safe

__all__ = ['highlight_code']


def _make_pre_code(code):
    return format_html('<pre><code>{0}</code></pre>', code)


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

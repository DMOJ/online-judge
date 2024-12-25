from django.utils.functional import Promise
from django.utils.encoding import force_str
from django.core.serializers.json import DjangoJSONEncoder

import markdown
from .settings import (
    MARTOR_MARKDOWN_SAFE_MODE,
    MARTOR_MARKDOWN_EXTENSIONS,
    MARTOR_MARKDOWN_EXTENSION_CONFIGS
)


class VersionNotCompatible(Exception):
    pass


def markdownify(markdown_content):
    """
    Render the markdown content to HTML.

    Basic:
        >>> from martor.utils import markdownify
        >>> content = "![awesome](http://i.imgur.com/hvguiSn.jpg)"
        >>> markdownify(content)
        '<p><img alt="awesome" src="http://i.imgur.com/hvguiSn.jpg" /></p>'
        >>>
    """
    try:
        return markdown.markdown(
            markdown_content,
            safe_mode=MARTOR_MARKDOWN_SAFE_MODE,
            extensions=MARTOR_MARKDOWN_EXTENSIONS,
            extension_configs=MARTOR_MARKDOWN_EXTENSION_CONFIGS
        )
    except Exception:
        raise VersionNotCompatible("The markdown isn't compatible, please reinstall "
                                   "your python markdown into Markdown>=3.0")


class LazyEncoder(DjangoJSONEncoder):
    """
    This problem because we found error encoding,
    as docs says, django has special `DjangoJSONEncoder`
    at https://docs.djangoproject.com/en/1.10/topics/serialization/#serialization-formats-json
    also discused in this answer: http://stackoverflow.com/a/31746279/6396981

    Usage:
        >>> data = {}
        >>> json.dumps(data, cls=LazyEncoder)
    """

    def default(self, obj):
        if isinstance(obj, Promise):
            return force_str(obj)
        return super(LazyEncoder, self).default(obj)

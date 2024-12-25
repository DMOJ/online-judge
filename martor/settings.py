from django.conf import settings

# Global martor settings
# Input: string boolean, `true/false`
MARTOR_ENABLE_CONFIGS = getattr(
    settings, 'MARTOR_ENABLE_CONFIGS', {
        'emoji': 'true',        # to enable/disable emoji icons.
        'imgur': 'true',        # to enable/disable imgur/custom uploader.
        'mention': 'false',     # to enable/disable mention
        'jquery': 'true',       # to include/revoke jquery (require for admin default django)
        'living': 'false',      # to enable/disable live updates in preview
        'spellcheck': 'false',  # to enable/disable spellcheck in form textareas
        'hljs': 'true',         # to enable/disable hljs highlighting in preview
    }
)

# To setup the martor editor with label or not (default is False)
MARTOR_ENABLE_LABEL = getattr(
    settings, 'MARTOR_ENABLE_LABEL', False
)

# Imgur API Keys
MARTOR_IMGUR_CLIENT_ID = getattr(
    settings, 'MARTOR_IMGUR_CLIENT_ID', ''
)
MARTOR_IMGUR_API_KEY = getattr(
    settings, 'MARTOR_IMGUR_API_KEY', ''
)

# Safe Mode
MARTOR_MARKDOWN_SAFE_MODE = getattr(
    settings, 'MARTOR_MARKDOWN_SAFE_MODE', True
)

# Markdownify
MARTOR_MARKDOWNIFY_FUNCTION = getattr(
    settings, 'MARTOR_MARKDOWNIFY_FUNCTION', 'martor.utils.markdownify'
)
MARTOR_MARKDOWNIFY_URL = getattr(
    settings, 'MARTOR_MARKDOWNIFY_URL', '/martor/markdownify/'
)

# Markdown extensions
MARTOR_MARKDOWN_EXTENSIONS = getattr(
    settings, 'MARTOR_MARKDOWN_EXTENSIONS', [
        'markdown.extensions.extra',
        'markdown.extensions.nl2br',
        'markdown.extensions.smarty',
        'markdown.extensions.fenced_code',

        # Custom markdown extensions.
        'martor.extensions.urlize',
        'martor.extensions.del_ins',    # ~~strikethrough~~ and ++underscores++
        'martor.extensions.mention',    # to parse markdown mention
        'martor.extensions.emoji',      # to parse markdown emoji
        'martor.extensions.mdx_video',  # to parse embed/iframe video
    ]
)

# Markdown Extensions Configs
MARTOR_MARKDOWN_EXTENSION_CONFIGS = getattr(
    settings, 'MARTOR_MARKDOWN_EXTENSION_CONFIGS', {}
)

# Markdown urls
MARTOR_UPLOAD_URL = getattr(
    settings, 'MARTOR_UPLOAD_URL', '/martor/uploader/'  # for imgur
)
MARTOR_SEARCH_USERS_URL = getattr(
    settings, 'MARTOR_SEARCH_USERS_URL', '/martor/search-user/'  # for mention
)

# Markdown Extensions
MARTOR_MARKDOWN_BASE_EMOJI_URL = getattr(
    settings, 'MARTOR_MARKDOWN_BASE_EMOJI_URL', 'https://github.githubassets.com/images/icons/emoji/'
)
# to use static and keep backward compatibility
# set to true if using bucket like storage engine
MARTOR_MARKDOWN_BASE_EMOJI_USE_STATIC = getattr(
    settings, 'MARTOR_MARKDOWN_BASE_EMOJI_USE_STATIC', False)
MARTOR_MARKDOWN_BASE_MENTION_URL = getattr(
    settings, 'MARTOR_MARKDOWN_BASE_MENTION_URL', 'https://python.web.id/author/'
)

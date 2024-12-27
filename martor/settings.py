from django.conf import settings

# Global martor settings
# Input: string boolean, `true/false`
MARTOR_ENABLE_CONFIGS = getattr(
    settings, 'MARTOR_ENABLE_CONFIGS', {
        'imgur': 'true',        # to enable/disable imgur/custom uploader.
        'mention': 'false',     # to enable/disable mention
        'living': 'false',      # to enable/disable live updates in preview
        'hljs': 'true',         # to enable/disable hljs highlighting in preview
    },
)

# Markdownify
MARTOR_MARKDOWNIFY_URL = getattr(
    settings, 'MARTOR_MARKDOWNIFY_URL', '/martor/markdownify/',
)

# Markdown urls
MARTOR_UPLOAD_URL = getattr(
    settings, 'MARTOR_UPLOAD_URL', '/martor/uploader/',  # for imgur
)
MARTOR_SEARCH_USERS_URL = getattr(
    settings, 'MARTOR_SEARCH_USERS_URL', '/martor/search-user/',  # for mention
)

# Markdown Extensions
MARTOR_MARKDOWN_BASE_MENTION_URL = getattr(
    settings, 'MARTOR_MARKDOWN_BASE_MENTION_URL', 'https://python.web.id/author/',
)

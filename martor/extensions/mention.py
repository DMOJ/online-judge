import markdown
from django.contrib.auth import get_user_model
from ..settings import (
    MARTOR_ENABLE_CONFIGS,
    MARTOR_MARKDOWN_BASE_MENTION_URL
)

"""
>>> import markdown
>>> md = markdown.Markdown(extensions=['martor.utils.extensions.mention'])
>>> md.convert('[user:summonagus]')
'<p><a class="direct-mention-link" href="https://webname.com/profile/summonagus/">summonagus</a></p>'
>>>
>>> md.convert('hello [user:summonagus], i mentioned you!')
'<p>hello <a class="direct-mention-link" href="https://webname.com/profile/summonagus/">summonagus</a>, i mentioned you!</p>'
>>>
"""

MENTION_RE = r'(?<!\!)\[(\w+)\]'


class MentionPattern(markdown.inlinepatterns.Pattern):

    def handleMatch(self, m):
        username = self.unescape(m.group(2))
        users = get_user_model().objects.filter(username=username, is_active=True)

        """Makesure `username` is registered and actived."""
        if MARTOR_ENABLE_CONFIGS['mention'] == 'true':
            if users.exists():
                url = '{0}{1}/'.format(MARTOR_MARKDOWN_BASE_MENTION_URL, username)
                el = markdown.util.etree.Element('a')
                el.set('href', url)
                el.set('class', 'direct-mention-link')
                el.text = markdown.util.AtomicString(username)
                return el


class MentionExtension(markdown.Extension):

    def extendMarkdown(self, md, md_globals):
        """ Setup `mention_link` with MentionPattern """
        md.inlinePatterns['mention_link'] = MentionPattern(MENTION_RE, md)


def makeExtension(*args, **kwargs):
    return MentionExtension(*args, **kwargs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

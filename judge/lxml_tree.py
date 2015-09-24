from lxml import html


class HTMLTreeString(object):
    def __init__(self, str):
        self.tree = html.fromstring(str)

    def __getattr__(self, attr):
        return getattr(self.tree, attr)

    def __unicode__(self):
        return html.tostring(self.tree)

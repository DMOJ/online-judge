from django.core.cache import cache
from django.template.defaultfilters import truncatewords

from judge.lxml_tree import HTMLTreeString
from markdown_trois import markdown

from judge.templatetags.reference import reference
from markdown_trois.templatetags.markdown_trois_tags import markdown_filter

def generate_opengraph(cache_key, data):
    metadata = cache.get(cache_key)
    if metadata is None:
        description = None
        tree = reference(markdown_filter(data, 'contest')).tree
        for p in tree.iterfind('p'):
            text = p.text_content().strip()
            if text:
                description = text
                break
        img = tree.xpath('.//img')
        metadata = truncatewords(description, 60), img[0].get('src') if img else None
        cache.set(cache_key, metadata, 86400)
    return metadata

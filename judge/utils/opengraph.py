from django.core.cache import cache

from judge.lxml_tree import HTMLTreeString
from markdown_trois import markdown


def generate_opengraph(cache_key, data):
    metadata = cache.get(cache_key)
    if metadata is None:
        description = None
        tree = HTMLTreeString(markdown(data, 'contest')).tree
        for p in tree.iterfind('p'):
            text = p.text_content().strip()
            if text:
                description = text
                break
        img = tree.xpath('.//img')
        metadata = description, img[0].get('src') if img else None
        cache.set(cache_key, metadata, 86400)
    return metadata

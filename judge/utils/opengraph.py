from django.core.cache import cache
from django.template.defaultfilters import truncatewords

from judge.templatetags.reference import reference
from judge.templatetags.markdown import markdown_filter


def generate_opengraph(cache_key, data, style):
    metadata = cache.get(cache_key)
    if metadata is None:
        description = None
        tree = reference(markdown_filter(data, style)).tree
        for p in tree.iterfind('p'):
            text = p.text_content().strip()
            if text:
                description = text
                break
        img = tree.xpath('.//img')
        metadata = truncatewords(description, 60), img[0].get('src') if img else None
        cache.set(cache_key, metadata, 86400)
    return metadata

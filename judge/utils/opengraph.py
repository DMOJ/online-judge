from django.core.cache import cache
from django.template.defaultfilters import truncatewords

from judge.jinja2.markdown import markdown
from judge.jinja2.reference import reference


def generate_opengraph(cache_key, data, style):
    metadata = cache.get(cache_key)
    if metadata is None:
        description = None
        tree = reference(markdown(data, style)).tree
        for p in tree.iterfind('..//p'):
            text = p.text_content().strip()
            if text:
                description = text
                break
        if description:
            for remove in (r'\[', r'\]', r'\(', r'\)'):
                description = description.replace(remove, '')
        img = tree.xpath('.//img')
        metadata = truncatewords(description, 60), img[0].get('src') if img else None
        cache.set(cache_key, metadata, 86400)
    return metadata

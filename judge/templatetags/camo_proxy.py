from camo import CamoClient
from django import template
from django.utils.safestring import mark_safe
from django.conf import settings

register = template.Library()

@register.filter(is_safe=True)
def proxy_images(text):
    if getattr(settings, 'CAMO_URL', None) and getattr(settings, 'CAMO_KEY', None):
        client = CamoClient(settings.CAMO_URL, key=settings.CAMO_KEY)
        return client.parse_html(text)
    return '<p>I broke it!</p>'

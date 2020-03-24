from judge.utils.camo import client as camo_client
from . import registry


@registry.filter
def camo(url):
    if camo_client is None:
        return url
    return camo_client.rewrite_url(url)

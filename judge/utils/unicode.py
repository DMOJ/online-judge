from django.utils import six


def utf8bytes(maybe_text):
    if maybe_text is None:
        return
    if isinstance(maybe_text, six.binary_type):
        return maybe_text
    return maybe_text.encode('utf-8')


def utf8text(maybe_bytes, errors='strict'):
    if maybe_bytes is None:
        return
    if isinstance(maybe_bytes, six.text_type):
        return maybe_bytes
    return maybe_bytes.decode('utf-8', errors)

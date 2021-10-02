from typing import AnyStr, Optional, overload


@overload
def utf8bytes(maybe_text: AnyStr) -> bytes:
    pass


@overload
def utf8bytes(maybe_text: None) -> None:
    pass


def utf8bytes(maybe_text):
    if maybe_text is None:
        return None
    if isinstance(maybe_text, bytes):
        return maybe_text
    return maybe_text.encode('utf-8')


@overload
def utf8text(maybe_bytes: AnyStr, errors='strict') -> str:
    pass


@overload
def utf8text(maybe_bytes: None, errors='strict') -> None:
    pass


def utf8text(maybe_bytes, errors='strict') -> Optional[str]:
    if maybe_bytes is None:
        return None
    if isinstance(maybe_bytes, str):
        return maybe_bytes
    return maybe_bytes.decode('utf-8', errors)

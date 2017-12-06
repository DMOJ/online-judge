from django.utils import translation

from . import registry


@registry.function('language_info')
def get_language_info(language):
    # ``language`` is either a language code string or a sequence
    # with the language code as its first item
    if len(language[0]) > 1:
        return translation.get_language_info(language[0])
    else:
        return translation.get_language_info(str(language))


@registry.function('language_info_list')
def get_language_info_list(langs):
    return [get_language_info(lang) for lang in langs]

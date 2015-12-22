import gettext as gettext_module

from django.conf import settings
from django.utils.safestring import SafeData, mark_safe

if settings.USE_I18N:
    from django.utils.translation.trans_real import DjangoTranslation, get_language

    _translations = {}


    class UserTranslation(DjangoTranslation):
        def _new_gnu_trans(self, localedir, use_null_fallback=True):
            translation = gettext_module.translation(
                    domain='dmoj-user',
                    localedir=localedir,
                    languages=[self._DjangoTranslation__locale],
                    codeset='utf-8',
                    fallback=True)
            if not hasattr(translation, '_catalog'):
                # provides merge support for NullTranslations()
                translation._catalog = {}
                translation._info = {}
                translation.plural = lambda n: int(n != 1)
            return translation


    def translation(language):
        global _translations
        if language not in _translations:
            _translations[language] = UserTranslation(language)
        return _translations[language]


    def do_translate(message, translation_function):
        """Copied from django.utils.translation.trans_real"""
        # str() is allowing a bytestring message to remain bytestring on Python 2
        eol_message = message.replace(str('\r\n'), str('\n')).replace(str('\r'), str('\n'))

        if len(eol_message) == 0:
            # Returns an empty value of the corresponding type if an empty message
            # is given, instead of metadata, which is the default gettext behavior.
            result = type(message)("")
        else:
            translation_object = translation(get_language())
            result = getattr(translation_object, translation_function)(eol_message)

        if isinstance(message, SafeData):
            return mark_safe(result)

        return result


    def ugettext(message):
        return do_translate(message, 'ugettext')
else:
    def ugettext(message):
        return message

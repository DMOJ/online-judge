from django.conf import settings
from django.utils.safestring import SafeData, mark_safe

if settings.USE_I18N:
    from django.utils.translation.trans_real import DjangoTranslation, get_language

    _translations = {}

    def translation(language):
        global _translations
        if language not in _translations:
            _translations[language] = DjangoTranslation(language, domain='dmoj-user')
        return _translations[language]

    def do_translate(message, translation_function):
        """Copied from django.utils.translation.trans_real"""
        # str() is allowing a bytestring message to remain bytestring on Python 2
        eol_message = message.replace(str('\r\n'), str('\n')).replace(str('\r'), str('\n'))

        if len(eol_message) == 0:
            # Returns an empty value of the corresponding type if an empty message
            # is given, instead of metadata, which is the default gettext behavior.
            result = ''
        else:
            translation_object = translation(get_language())
            result = getattr(translation_object, translation_function)(eol_message)
            if not isinstance(result, str):
                result = result.decode('utf-8')

        if isinstance(message, SafeData):
            return mark_safe(result)

        return result

    def gettext(message):
        return do_translate(message, 'gettext')
else:
    def gettext(message):
        return message

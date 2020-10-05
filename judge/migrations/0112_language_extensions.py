from django.db import migrations


def update_language_extensions(apps, schema_editor):
    Language = apps.get_model('judge', 'Language')

    extension_mapping = {
        'ADA': 'adb',
        'AWK': 'awk',
        'BASH': 'sh',
        'BF': 'c',
        'C': 'c',
        'C11': 'c',
        'CBL': 'cbl',
        'CLANG': 'c',
        'CLANGX': 'cpp',
        'COFFEE': 'coffee',
        'CPP03': 'cpp',
        'CPP11': 'cpp',
        'CPP14': 'cpp',
        'CPP17': 'cpp',
        'D': 'd',
        'DART': 'dart',
        'F95': 'f95',
        'FORTH': 'fs',
        'GAS32': 'asm',
        'GAS64': 'asm',
        'GASARM': 'asm',
        'GO': 'go',
        'GROOVY': 'groovy',
        'HASK': 'hs',
        'ICK': 'i',
        'JAVA10': 'java',
        'JAVA11': 'java',
        'JAVA8': 'java',
        'JAVA9': 'java',
        'KOTLIN': 'kt',
        'LUA': 'lua',
        'MONOCS': 'cs',
        'MONOFS': 'fs',
        'MONOVB': 'vb',
        'NASM': 'asm',
        'NASM64': 'asm',
        'OBJC': 'm',
        'OCAML': 'ml',
        'PAS': 'pas',
        'PERL': 'pl',
        'PHP': 'php',
        'PIKE': 'pike',
        'PRO': 'pl',
        'PY2': 'py',
        'PY3': 'py',
        'PYPY': 'py',
        'PYPY3': 'py',
        'RKT': 'rkt',
        'RUBY18': 'rb',
        'RUBY2': 'rb',
        'RUST': 'rs',
        'SBCL': 'cl',
        'SCALA': 'scala',
        'SCM': 'scm',
        'SED': 'sed',
        'SWIFT': 'swift',
        'TCL': 'tcl',
        'TEXT': 'txt',
        'TUR': 't',
        'V8JS': 'js',
        'ZIG': 'zig',
    }

    languages = Language.objects.all()
    for language in languages:
        try:
            extension = extension_mapping[language.key]
        except KeyError:
            print('Warning: no extension found for %s. Setting extension to language key.' % language.key)
            extension = language.key.lower()

        language.extension = extension

    Language.objects.bulk_update(languages, ['extension'])


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0111_blank_assignees_ticket'),
    ]

    operations = [
        migrations.RunPython(update_language_extensions, reverse_code=migrations.RunPython.noop),
    ]

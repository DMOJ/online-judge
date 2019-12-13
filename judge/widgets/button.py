from django.forms import TextInput
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class GenerateKeyTextInputButton(TextInput):
    def __init__(self, *args, **kwargs):
        self.charset = kwargs.pop("charset", "abcdefghijklnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`~!@#$%^&*()_+-=|[]{};:,<>./")  # noqa: E501
        self.length = kwargs.pop("length", 100)
        super(TextInput, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None, charset=None):
        text = super(TextInput, self).render(name, value, attrs)
        return mark_safe(text + format_html(
            '''\
&nbsp;<a href="#" onclick="return false;" class="button inline-button" id="id_{0}_regen">Regenerate</a>
<script type="text/javascript">
django.jQuery(document).ready(function ($) {{
    $(document).ready(function () {{
        $('#id_{0}_regen').click(function () {{
            var length = {length},
                charset = "{charset}",
                key = "";
            for (var i = 0, n = charset.length; i < length; ++i) {{
                key += charset.charAt(Math.floor(Math.random() * n));
            }}
            $('#id_{0}').val(key);
        }});
    }});
}});
</script>
''', name, length=self.length, charset=self.charset))

from django.conf.urls import url
from django.db.models import TextField
from django.forms import ModelForm, ModelMultipleChoiceField, TextInput
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from reversion.admin import VersionAdmin

from django_ace import AceWidget
from judge.models import Judge, Problem
from judge.widgets import AdminHeavySelect2MultipleWidget, AdminMartorWidget


class LanguageForm(ModelForm):
    problems = ModelMultipleChoiceField(
        label=_('Disallowed problems'),
        queryset=Problem.objects.all(),
        required=False,
        help_text=_('These problems are NOT allowed to be submitted in this language'),
        widget=AdminHeavySelect2MultipleWidget(data_view='problem_select2'))

    class Meta:
        widgets = {'description': AdminMartorWidget}


class LanguageAdmin(VersionAdmin):
    fields = ('key', 'name', 'short_name', 'common_name', 'ace', 'pygments', 'info', 'description',
              'template', 'problems')
    list_display = ('key', 'name', 'common_name', 'info')
    form = LanguageForm

    def save_model(self, request, obj, form, change):
        super(LanguageAdmin, self).save_model(request, obj, form, change)
        obj.problem_set.set(Problem.objects.exclude(id__in=form.cleaned_data['problems'].values('id')))

    def get_form(self, request, obj=None, **kwargs):
        self.form.base_fields['problems'].initial = \
            Problem.objects.exclude(id__in=obj.problem_set.values('id')).values_list('pk', flat=True) if obj else []
        form = super(LanguageAdmin, self).get_form(request, obj, **kwargs)
        if obj is not None:
            form.base_fields['template'].widget = AceWidget(obj.ace, request.profile.ace_theme)
        return form


class GenerateKeyTextInput(TextInput):
    def render(self, name, value, attrs=None, renderer=None):
        text = super(TextInput, self).render(name, value, attrs)
        return mark_safe(text + format_html(
            '''\
<a href="#" onclick="return false;" class="button" id="id_{0}_regen">Regenerate</a>
<script type="text/javascript">
django.jQuery(document).ready(function ($) {{
    $('#id_{0}_regen').click(function () {{
        var length = 100,
            charset = "abcdefghijklnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`~!@#$%^&*()_+-=|[]{{}};:,<>./?",
            key = "";
        for (var i = 0, n = charset.length; i < length; ++i) {{
            key += charset.charAt(Math.floor(Math.random() * n));
        }}
        $('#id_{0}').val(key);
    }});
}});
</script>
''', name))


class JudgeAdminForm(ModelForm):
    class Meta:
        widgets = {'auth_key': GenerateKeyTextInput, 'description': AdminMartorWidget}


class JudgeAdmin(VersionAdmin):
    form = JudgeAdminForm
    readonly_fields = ('created', 'online', 'start_time', 'ping', 'load', 'last_ip', 'runtimes', 'problems')
    fieldsets = (
        (None, {'fields': ('name', 'auth_key', 'is_blocked')}),
        (_('Description'), {'fields': ('description',)}),
        (_('Information'), {'fields': ('created', 'online', 'last_ip', 'start_time', 'ping', 'load')}),
        (_('Capabilities'), {'fields': ('runtimes', 'problems')}),
    )
    list_display = ('name', 'online', 'start_time', 'ping', 'load', 'last_ip')
    ordering = ['-online', 'name']
    formfield_overrides = {
        TextField: {'widget': AdminMartorWidget},
    }

    def get_urls(self):
        return ([url(r'^(\d+)/disconnect/$', self.disconnect_view, name='judge_judge_disconnect'),
                 url(r'^(\d+)/terminate/$', self.terminate_view, name='judge_judge_terminate')] +
                super(JudgeAdmin, self).get_urls())

    def disconnect_judge(self, id, force=False):
        judge = get_object_or_404(Judge, id=id)
        judge.disconnect(force=force)
        return HttpResponseRedirect(reverse('admin:judge_judge_changelist'))

    def disconnect_view(self, request, id):
        return self.disconnect_judge(id)

    def terminate_view(self, request, id):
        return self.disconnect_judge(id, force=True)

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.online:
            return self.readonly_fields + ('name',)
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        result = super(JudgeAdmin, self).has_delete_permission(request, obj)
        if result and obj is not None:
            return not obj.online
        return result

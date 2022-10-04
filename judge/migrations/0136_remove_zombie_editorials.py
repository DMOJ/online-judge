import django.db.models.deletion
from django.db import migrations, models


def delete_null_solutions(apps, scheme_editor):
    model = apps.get_model('judge', 'Solution')
    model.objects.filter(problem=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0135_disable_judge'),
    ]

    operations = [
        migrations.RunPython(delete_null_solutions),
        migrations.AlterField(
            model_name='solution',
            name='problem',
            field=models.OneToOneField(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='solution', to='judge.Problem', verbose_name='associated problem'),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0152_deactivate_user_permission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='time',
            field=models.FloatField(blank=True, null=True, verbose_name='execution time'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='memory',
            field=models.FloatField(blank=True, null=True, verbose_name='memory usage'),
        ),
    ]

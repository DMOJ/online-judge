import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0112_language_extensions'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='points_precision',
            field=models.IntegerField(default=3, help_text='Number of digits to round points to.', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)], verbose_name='precision points'),
        ),
        migrations.AlterField(
            model_name='contestparticipation',
            name='score',
            field=models.FloatField(db_index=True, default=0, verbose_name='score'),
        ),
    ]

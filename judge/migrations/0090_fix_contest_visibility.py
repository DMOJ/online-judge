from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0089_submission_to_contest'),
    ]

    operations = [
        migrations.RunSQL("""
            UPDATE `judge_contest`
            SET `judge_contest`.`is_private` = 0, `judge_contest`.`is_organization_private` = 1
            WHERE `judge_contest`.`is_private` = 1
        """, """
            UPDATE `judge_contest`
            SET `judge_contest`.`is_private` = `judge_contest`.`is_organization_private`
        """),
    ]

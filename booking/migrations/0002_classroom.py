from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='classroom',
            field=models.CharField(
                blank=True,
                choices=[
                    ('all', '全教室'),
                    ('yokogawa', '通常教室（横川）のみ'),
                    ('ishihara', '石原教室のみ'),
                ],
                default='all',
                max_length=20,
                verbose_name='担当教室',
            ),
        ),
        migrations.AddField(
            model_name='family',
            name='access_yokogawa',
            field=models.BooleanField(default=True, verbose_name='通常教室（横川）'),
        ),
        migrations.AddField(
            model_name='family',
            name='access_ishihara',
            field=models.BooleanField(default=False, verbose_name='石原教室'),
        ),
        migrations.AddField(
            model_name='lessonslot',
            name='classroom',
            field=models.CharField(
                choices=[
                    ('yokogawa', '通常教室（横川）'),
                    ('ishihara', '石原教室'),
                ],
                default='yokogawa',
                max_length=20,
                verbose_name='教室',
            ),
        ),
    ]

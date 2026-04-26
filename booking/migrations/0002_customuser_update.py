import django.contrib.auth.models
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('booking', '0001_initial'),
    ]

    operations = [
        # 既存DBのCustomUserテーブルをマイグレーション状態に登録（DDLは実行しない）
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='CustomUser',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('password', models.CharField(max_length=128, verbose_name='password')),
                        ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                        ('is_superuser', models.BooleanField(default=False)),
                        ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                        ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                        ('is_staff', models.BooleanField(default=False)),
                        ('is_active', models.BooleanField(default=True)),
                        ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
                        ('username', models.CharField(max_length=150, unique=True)),
                        ('email', models.EmailField(max_length=254, unique=True, verbose_name='メールアドレス')),
                        ('groups', models.ManyToManyField(blank=True, to='auth.Group')),
                        ('user_permissions', models.ManyToManyField(blank=True, to='auth.Permission')),
                    ],
                    options={
                        'verbose_name': 'ユーザー',
                        'verbose_name_plural': 'ユーザー',
                    },
                    managers=[
                        ('objects', django.contrib.auth.models.UserManager()),
                    ],
                ),
            ],
            database_operations=[],
        ),
        # nameフィールドを追加
        migrations.AddField(
            model_name='customuser',
            name='name',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='氏名'),
            preserve_default=False,
        ),
        # usernameフィールドを削除
        migrations.RemoveField(
            model_name='customuser',
            name='username',
        ),
    ]

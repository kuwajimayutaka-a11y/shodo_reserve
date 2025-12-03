# create_admin.py
import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shodo_reserve.settings")
django.setup()

User = get_user_model()

username = os.environ.get("DJANGO_ADMIN_USER", "tomoko")
email = os.environ.get("DJANGO_ADMIN_EMAIL", "tomoko.yutakana@gmail.com")
password = os.environ.get("DJANGO_ADMIN_PASSWORD", "koko0601")

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Created superuser {username}")
else:
    print(f"Superuser {username} already exists")

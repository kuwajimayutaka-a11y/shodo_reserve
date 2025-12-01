# shodo_reserve/Dockerfile
# Python公式イメージ
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=shodo_reserve.settings

WORKDIR /usr/src/app

# 依存関係をインストール
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# プロジェクトコードをコピー
COPY . .

EXPOSE 8000

# 起動時に migrate → collectstatic → gunicorn を順に実行
ENTRYPOINT ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn --bind 0.0.0.0:8000 shodo_reserve.wsgi:application"]

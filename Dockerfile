# shodo_reserve/Dockerfile
# Python公式イメージ
FROM python:3.11-slim

# 環境変数
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=shodo_reserve.settings

# 作業ディレクトリ
WORKDIR /usr/src/app

# 依存関係をコピーしてインストール
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# プロジェクトコードをコピー
COPY . .

# 8000番ポートを公開
EXPOSE 8000

# ※ migrate / collectstatic は CMD 実行時に走らせる方が安全（無料プラン DB 対応）
# ENTRYPOINT で migrate → collectstatic → gunicorn を順に実行
ENTRYPOINT ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn --bind 0.0.0.0:8000 shodo_reserve.wsgi:application"]

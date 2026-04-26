#!/bin/bash

# データベースのマイグレーションを実行
echo "Applying database migrations..."
python manage.py migrate --noinput

# 静的ファイルの収集を実行
echo "Collecting static files..."
python manage.py collectstatic --noinput

# 管理者ユーザーを作成（環境変数が設定されている場合のみ）
echo "Creating admin user..."
python create_admin.py

# Gunicornでアプリケーションを起動
echo "Starting Gunicorn..."
PORT=${PORT:-8000}
exec gunicorn shodo_reserve.wsgi:application --bind 0.0.0.0:$PORT

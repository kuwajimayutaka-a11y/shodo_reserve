#!/bin/bash

# データベースのマイグレーションを実行
echo "Applying database migrations..."
python manage.py migrate --noinput

# 静的ファイルの収集を実行
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Gunicornでアプリケーションを起動
echo "Starting Gunicorn..."
# Renderの環境変数PORTを使用。未設定の場合は8000をデフォルトとする
PORT=${PORT:-8000}
exec gunicorn shodo_reserve.wsgi:application --bind 0.0.0.0:$PORT

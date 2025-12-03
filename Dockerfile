# shodo_reserve/Dockerfile
# Pythonの公式イメージを使用
FROM python:3.11-slim

# 環境変数を設定
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE shodo_reserve.settings

# 作業ディレクトリを設定
WORKDIR /usr/src/app

# 依存関係をインストール
COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

# プロジェクトのコードをコンテナにコピー
COPY . /usr/src/app/

# 8000番ポートを公開
EXPOSE 8000

# Gunicornを使ってアプリケーションを起動
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "shodo_reserve.wsgi:application"]

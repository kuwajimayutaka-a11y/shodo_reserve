# ベースイメージ
FROM python:3.11-slim AS builder

# 作業ディレクトリ
WORKDIR /app

# 依存パッケージ
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && apt-get clean

# requirements.txt をコピー
COPY requirements.txt .

# 依存インストール（wheel を作って後で使う）
RUN pip install --upgrade pip && pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels



# ============================
#   実行環境
# ============================
FROM python:3.11-slim

WORKDIR /app

# wheel をコピーしてインストール
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

# プロジェクト本体をコピー
COPY . /app/

# collectstatic（STATIC_ROOT が設定されている場合）
RUN python manage.py collectstatic --noinput || true

# ポート開放
EXPOSE 8000

# Gunicorn 実行
# shodo_reserve は Django プロジェクト名に置き換えてね！
CMD ["gunicorn", "shodo_reserve.wsgi:application", "--bind", "0.0.0.0:8000"]

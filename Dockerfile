# ============================
#   ビルド環境
# ============================
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && apt-get clean

COPY requirements.txt .

RUN pip install --upgrade pip && pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels

# ============================
#   実行環境
# ============================
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

COPY . /app/

# collectstatic（STATIC_ROOT が設定されている場合）
RUN python manage.py collectstatic --noinput || true

# ポート開放
EXPOSE 8000

# コンテナ起動時に migrate を実行してから Gunicorn を起動
CMD python manage.py migrate && gunicorn shodo_reserve.wsgi:application --bind 0.0.0.0:8000

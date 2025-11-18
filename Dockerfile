# CloudRun用 ScienceBuddy Dockerfile
# Python 3.11ベースイメージ
FROM python:3.11-slim

# CloudRunでは8080番ポートを使用
EXPOSE 8080

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージのアップデート
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ローカルストレージディレクトリを作成
RUN mkdir -p /app/uploads && \
    mkdir -p /app/logs

# 環境変数を設定
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# gunicornでFlaskアプリを実行
CMD exec gunicorn --bind :${PORT} --workers 2 --threads 2 --timeout 60 --access-logfile - --error-logfile - app:app

# ScienceBuddy 技術仕様書

**プロジェクト名**: ScienceBuddy（サイエンスバディ）  
**バージョン**: 2.0  
**最終更新日**: 2026年1月26日  
**作成者**: nov11masaki  

---

## 目次

1. [システムアーキテクチャ](#1-システムアーキテクチャ)
2. [技術スタック](#2-技術スタック)
3. [データベース設計](#3-データベース設計)
4. [API設計](#4-api設計)
5. [セキュリティ](#5-セキュリティ)
6. [デプロイメント](#6-デプロイメント)
7. [モニタリング・ロギング](#7-モニタリングロギング)
8. [パフォーマンス最適化](#8-パフォーマンス最適化)

---

## 1. システムアーキテクチャ

### 1.1 全体構成

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Web Browser │  │   Tablet    │  │ Smartphone  │         │
│  │  (Chrome/    │  │   (iPad/    │  │  (iOS/      │         │
│  │   Safari)    │  │   Android)  │  │   Android)  │         │
│  └──────┬───────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼──────────────────┼─────────────────┼───────────────┘
          │                  │                 │
          └──────────────────┴─────────────────┘
                             │
                    HTTPS (Port 443/8080)
                             │
          ┌──────────────────▼─────────────────┐
          │     Application Layer               │
          │  ┌─────────────────────────────┐   │
          │  │   Flask App (Python 3.11+)  │   │
          │  │  ┌────────────────────────┐ │   │
          │  │  │  Routes & Controllers  │ │   │
          │  │  └────────────────────────┘ │   │
          │  │  ┌────────────────────────┐ │   │
          │  │  │  Session Management    │ │   │
          │  │  └────────────────────────┘ │   │
          │  │  ┌────────────────────────┐ │   │
          │  │  │  Business Logic        │ │   │
          │  │  └────────────────────────┘ │   │
          │  └─────────────┬───────────────┘   │
          └────────────────┼─────────────────────┘
                           │
          ┌────────────────┴─────────────────┐
          │         Service Layer             │
          ├───────────────┬───────────────────┤
          │   OpenAI API  │  Analysis Engine  │
          │ (gpt-4o-mini) │  (tools/analysis) │
          │  - Chat       │  - 理科用語分析   │
          │  - Embeddings │  - クラスタリング │
          └───────┬───────┴────────┬──────────┘
                  │                │
          ┌───────▼────────────────▼──────────┐
          │       Data Storage Layer          │
          ├───────────────────────────────────┤
          │ Development:                      │
          │  - Local JSON Files               │
          │    • learning_progress.json       │
          │    • session_storage.json         │
          │    • summary_storage.json         │
          │    • logs/learning_log_*.json     │
          ├───────────────────────────────────┤
          │ Production:                       │
          │  - Google Cloud Storage (GCS)     │
          │    • Bucket: science-buddy-logs   │
          │  - Firestore (Optional)           │
          │  - Redis (Optional, for RQ)       │
          └───────────────────────────────────┘
```

### 1.2 レイヤーアーキテクチャ

#### 1.2.1 プレゼンテーション層
- **責務**: UI表示、ユーザー入力処理
- **技術**: Jinja2テンプレート、Bootstrap 5、JavaScript
- **主要ファイル**: `templates/`, `static/css/style.css`

#### 1.2.2 アプリケーション層
- **責務**: ビジネスロジック、ルーティング、セッション管理
- **技術**: Flask、Python 3.11+
- **主要ファイル**: `app.py` (3488行)

#### 1.2.3 サービス層
- **責務**: 外部API連携、データ分析
- **技術**: OpenAI API、scikit-learn、numpy
- **主要ファイル**: `tools/analysis.py`

#### 1.2.4 データ層
- **責務**: データ永続化、ストレージ管理
- **技術**: JSON、GCS、Firestore（オプション）
- **主要ファイル**: `storage/firestore_store.py`

---

## 2. 技術スタック

### 2.1 バックエンド

| カテゴリ | 技術 | バージョン | 用途 |
|---------|------|----------|------|
| **言語** | Python | 3.11+ | アプリケーション開発 |
| **Webフレームワーク** | Flask | 3.1.1 | HTTPリクエスト処理 |
| **WSGI サーバー** | Gunicorn | 21.2.0 | 本番環境（Linux） |
| **WSGI サーバー** | Waitress | 2.1.2 | 本番環境（Windows） |
| **AI** | OpenAI API | 1.99.9+ | 対話生成、Embeddings |
| **データ分析** | scikit-learn | 1.3.0+ | クラスタリング、テキスト分析 |
| **数値計算** | numpy | <2.0 | 数値演算 |
| **非同期処理** | Redis + RQ | 4.7.0+ / 1.1.0+ | ジョブキュー（オプション） |

### 2.2 フロントエンド

| カテゴリ | 技術 | バージョン | 用途 |
|---------|------|----------|------|
| **HTMLテンプレート** | Jinja2 | 3.x | 動的HTML生成 |
| **CSSフレームワーク** | Bootstrap | 5.x | レスポンシブデザイン |
| **JavaScript** | Vanilla JS | ES6+ | クライアントサイドロジック |

### 2.3 インフラストラクチャ

| カテゴリ | 技術 | 用途 |
|---------|------|------|
| **本番環境** | Google Cloud Run | コンテナ実行環境 |
| **ストレージ** | Google Cloud Storage | ファイル保存（本番） |
| **データベース** | Firestore | NoSQLデータベース（オプション） |
| **CI/CD** | Cloud Build | 自動ビルド・デプロイ |
| **コンテナ** | Docker | アプリケーションコンテナ化 |

### 2.4 開発ツール

| カテゴリ | 技術 | 用途 |
|---------|------|------|
| **バージョン管理** | Git | ソースコード管理 |
| **リポジトリ** | GitHub | コード共有 |
| **環境変数管理** | python-dotenv | .env ファイル管理 |
| **HTTPクライアント** | requests, urllib3 | HTTP通信 |

---

## 3. データベース設計

### 3.1 ストレージ戦略

#### 3.1.1 ストレージ選択ロジック

```python
# app.py の初期化部分
USE_GCS = (
    (os.getenv('FLASK_ENV') == 'production')
    or bool(os.getenv('K_SERVICE'))  # Cloud Run 環境検出
    or os.getenv('USE_GCS') == '1'
) and bool(os.getenv('GCP_PROJECT_ID'))

# 優先順位: Firestore > GCS > Local JSON
```

#### 3.1.2 データファイル構造

##### ローカル環境
```
ScienceBuddy/
├── learning_progress.json      # 学習進捗管理
├── session_storage.json        # セッションデータ
├── summary_storage.json        # 要約データ
└── logs/
    ├── learning_log_20251203.json
    ├── learning_log_20251204.json
    └── learning_log_20260120.json
```

##### GCS 環境
```
gs://science-buddy-logs/
├── learning_progress.json
├── sessions/
│   └── {student_id}/
│       └── {unit}/
│           ├── prediction.json
│           └── reflection.json
├── summaries/
│   └── {student_id}/
│       └── {unit}/
│           ├── prediction_summary.json
│           └── reflection_summary.json
├── logs/
│   └── learning_log_YYYYMMDD.json
└── error_logs/
    └── error_log_YYYYMMDD.json
```

### 3.2 データスキーマ

#### 3.2.1 学習進捗データ（learning_progress.json）

```json
{
  "4101": {
    "空気の温度と体積": {
      "prediction_completed": true,
      "prediction_timestamp": "2026-01-26T14:30:00+09:00",
      "reflection_completed": false,
      "reflection_timestamp": null
    },
    "金属のあたたまり方": {
      "prediction_completed": true,
      "prediction_timestamp": "2026-01-25T10:15:00+09:00",
      "reflection_completed": true,
      "reflection_timestamp": "2026-01-25T11:30:00+09:00"
    }
  },
  "4102": {
    "水のあたたまり方": {
      "prediction_completed": true,
      "prediction_timestamp": "2026-01-26T09:00:00+09:00",
      "reflection_completed": false,
      "reflection_timestamp": null
    }
  }
}
```

#### 3.2.2 セッションデータ（session_storage.json）

```json
{
  "4101": {
    "空気の温度と体積": {
      "prediction": {
        "timestamp": "2026-01-26T14:30:00+09:00",
        "conversation": [
          {
            "role": "assistant",
            "content": "まずは空気を温めると体積はどうなるかな？"
          },
          {
            "role": "user",
            "content": "大きくなると思います"
          },
          {
            "role": "assistant",
            "content": "なぜ大きくなると思ったのかな？"
          },
          {
            "role": "user",
            "content": "夏の日にタイヤがパンパンになったから"
          }
        ]
      }
    }
  }
}
```

#### 3.2.3 サマリーストレージ（summary_storage.json）

```json
{
  "4101": {
    "空気の温度と体積": {
      "prediction_summary": {
        "summary": "空気を温めると体積が大きくなると思います。なぜなら、夏の日に自転車のタイヤがパンパンになったからです。冷やすと小さくなると思います。",
        "timestamp": "2026-01-26T14:35:00+09:00",
        "conversation": [...]
      },
      "reflection_summary": {
        "summary": "実験では空気を温めると体積が大きくなりました。予想通りでした。冷やすと小さくなることも確認できました。",
        "timestamp": "2026-01-26T15:00:00+09:00",
        "conversation": [...]
      }
    }
  }
}
```

#### 3.2.4 学習ログ（learning_log_YYYYMMDD.json）

```json
[
  {
    "log_type": "prediction_chat",
    "timestamp": "2026-01-26T14:30:15+09:00",
    "student_id": 4101,
    "class": 1,
    "unit": "空気の温度と体積",
    "stage": "prediction",
    "conversation": [
      {
        "role": "assistant",
        "content": "まずは空気を温めると体積はどうなるかな？"
      },
      {
        "role": "user",
        "content": "大きくなると思います"
      }
    ]
  },
  {
    "log_type": "prediction_summary",
    "timestamp": "2026-01-26T14:35:00+09:00",
    "student_id": 4101,
    "class": 1,
    "unit": "空気の温度と体積",
    "stage": "prediction",
    "conversation": [...],
    "summary": "空気を温めると体積が大きくなると思います。なぜなら、夏の日に自転車のタイヤがパンパンになったからです。"
  }
]
```

### 3.3 データアクセスパターン

#### 3.3.1 原子的書き込み

```python
def _atomic_write_json(path, data):
    """
    アトミック書き込みによるデータ整合性確保
    - 一時ファイルに書き込み
    - fsync で永続化
    - os.replace で原子的にリネーム
    - プロセス内・プロセス間ロック
    """
    import tempfile
    import fcntl
    
    lock = _get_lock_for_path(path)
    with lock:
        fd, tmp = tempfile.mkstemp(...)
        # 書き込み処理
        os.replace(tmp, path)  # 原子的
```

#### 3.3.2 GCS アクセス

```python
def _save_to_gcs(bucket, blob_name, data):
    """
    GCS へのデータ保存
    - Application Default Credentials (ADC) 使用
    - JSON 形式でアップロード
    - エラーハンドリング
    """
    blob = bucket.blob(blob_name)
    blob.upload_from_string(
        json.dumps(data, ensure_ascii=False, indent=2),
        content_type='application/json'
    )
```

---

## 4. API設計

### 4.1 内部API（Flask Routes）

#### 4.1.1 学習者向けエンドポイント

| メソッド | エンドポイント | 説明 | パラメータ |
|---------|--------------|------|-----------|
| GET | `/` | トップページ | - |
| GET | `/select_class` | クラス選択 | - |
| GET | `/select_number` | 出席番号選択 | `class` |
| GET | `/select_unit` | 単元選択 | `student_id`, `class` |
| GET | `/prediction` | 予想段階 | `unit`, `resume` |
| GET | `/reflection` | 考察段階 | `unit`, `resume` |
| POST | `/chat` | 予想チャット | `message` |
| POST | `/reflect_chat` | 考察チャット | `message` |
| POST | `/summary` | 予想要約生成 | - |
| POST | `/final_summary` | 考察要約生成 | - |
| GET | `/history` | 学習履歴 | - |
| GET | `/api/student-history` | 履歴データ取得 | - |

#### 4.1.2 教員向けエンドポイント

| メソッド | エンドポイント | 説明 | パラメータ |
|---------|--------------|------|-----------|
| GET/POST | `/teacher/login` | 教員ログイン | `username`, `password` |
| GET | `/teacher/logout` | ログアウト | - |
| GET | `/teacher` | リダイレクト → dashboard | - |
| GET | `/teacher/dashboard` | ダッシュボード | - |
| GET | `/teacher/logs` | 学習ログ一覧 | `date`, `student_id` |
| GET | `/teacher/student_detail` | 児童詳細 | `student_id` |
| GET | `/teacher/analysis_dashboard` | 分析ダッシュボード | - |
| GET | `/teacher/analysis` | 分析実行 | `unit`, `stage` |
| GET | `/teacher/export` | CSV エクスポート | - |
| GET | `/teacher/export_json` | JSON エクスポート | - |

#### 4.1.3 ユーティリティエンドポイント

| メソッド | エンドポイント | 説明 |
|---------|--------------|------|
| GET | `/api/test` | ヘルスチェック |
| POST | `/api/sync-session` | セッション同期 |
| POST | `/report_error` | エラー報告 |
| GET | `/job_status/<job_id>` | ジョブステータス（RQ） |
| GET | `/summary/status/<job_id>` | 要約ジョブステータス |

### 4.2 外部API連携

#### 4.2.1 OpenAI Chat Completions API

**エンドポイント**: `https://api.openai.com/v1/chat/completions`

**リクエスト例**:
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "system",
      "content": "あなたは小学4年生の理科学習をサポートするAIです..."
    },
    {
      "role": "user",
      "content": "空気を温めるとどうなると思う？"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 500
}
```

**レスポンス処理**:
```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    temperature=0.7,
    max_tokens=500
)
ai_response = response.choices[0].message.content
```

#### 4.2.2 OpenAI Embeddings API

**エンドポイント**: `https://api.openai.com/v1/embeddings`

**用途**: テキストクラスタリング、類似度計算

**実装**:
```python
def get_text_embedding(text):
    """テキストの埋め込みベクトルを取得"""
    if not OPENAI_AVAILABLE or not client:
        return None
    
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding
```

---

## 5. セキュリティ

### 5.1 認証・認可

#### 5.1.1 教員認証

**実装方式**: セッションベース認証

```python
TEACHER_CREDENTIALS = {
    "teacher": "science",  # 全クラス管理
    "4100": "science",     # 1組担任
    "4200": "science",     # 2組担任
    "4300": "science",     # 3組担任
    "4400": "science",     # 4組担任
    "5000": "science",     # 研究室
}

def require_teacher_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('teacher_authenticated'):
            return redirect(url_for('teacher_login'))
        return f(*args, **kwargs)
    return decorated_function
```

#### 5.1.2 クラス別権限管理

```python
TEACHER_CLASS_MAPPING = {
    "teacher": ["class1", "class2", "class3", "class4", "lab"],
    "4100": ["class1"],
    "4200": ["class2"],
    # ...
}

# 権限チェック
accessible_classes = TEACHER_CLASS_MAPPING.get(teacher_id, [])
```

### 5.2 セッション管理

#### 5.2.1 同時ログイン制御

```python
active_sessions = {}  # {student_id: session_id}
session_devices = {}  # {session_id: device_fingerprint}

def get_device_fingerprint():
    """デバイスフィンガープリント生成"""
    ua = request.headers.get('User-Agent', 'unknown')
    ip = request.remote_addr
    device_info = f"{ua}:{ip}"
    return hashlib.md5(device_info.encode()).hexdigest()
```

#### 5.2.2 セッションセキュリティ

```python
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True  # 本番環境のみ
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
```

### 5.3 APIキー管理

#### 5.3.1 環境変数による管理

```bash
# .env ファイル（Git 管理外）
OPENAI_API_KEY=sk-proj-...
GCP_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=science-buddy-logs
SECRET_KEY=random-secret-key-for-production
```

#### 5.3.2 Cloud Run シークレット管理

```bash
# シークレットの作成
gcloud secrets create openai-api-key --data-file=-

# Cloud Run へのマウント
gcloud run services update science-buddy \
  --update-secrets=OPENAI_API_KEY=openai-api-key:latest
```

### 5.4 入力検証

#### 5.4.1 XSS 対策

```python
# Jinja2 の自動エスケープ（デフォルト有効）
{{ user_input }}  # 自動的に HTML エスケープ

# JavaScript でのエスケープ
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}
```

#### 5.4.2 CSRF 対策

```python
# Flask-WTF を使用する場合
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)
```

### 5.5 データ保護

#### 5.5.1 HTTPS 通信

```python
# 本番環境では HTTPS 強制
if os.getenv('FLASK_ENV') == 'production':
    @app.before_request
    def before_request():
        if not request.is_secure:
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)
```

#### 5.5.2 ログのサニタイズ

```python
def sanitize_log_data(data):
    """ログから機密情報を除去"""
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key in ['password', 'api_key', 'secret']:
                sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = sanitize_log_data(value)
        return sanitized
    return data
```

---

## 6. デプロイメント

### 6.1 開発環境

#### 6.1.1 ローカルセットアップ

```bash
# 1. リポジトリクローン
git clone https://github.com/nov11masaki/scienceapp2.git
cd scienceapp2

# 2. 仮想環境作成
python -m venv .venv
source .venv/bin/activate

# 3. 依存関係インストール
pip install -r requirements.txt

# 4. 環境変数設定
cat > .env << EOF
OPENAI_API_KEY=your_api_key_here
FLASK_ENV=development
EOF

# 5. アプリケーション起動
python app.py
```

**起動後のアクセス**:
- 学習者: http://localhost:5014
- 教員: http://localhost:5014/teacher

### 6.2 Docker 環境

#### 6.2.1 Dockerfile

```dockerfile
FROM python:3.11-slim

EXPOSE 8080
WORKDIR /app

# システムパッケージ
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Python依存関係
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# アプリケーションコード
COPY . .

# ディレクトリ作成
RUN mkdir -p /app/uploads /app/logs /data

# 環境変数
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV LEARNING_PROGRESS_FILE=/data/learning_progress.json
ENV SESSION_STORAGE_FILE=/data/session_storage.json

VOLUME ["/data"]

# Gunicorn 起動
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
```

#### 6.2.2 Docker ビルド・実行

```bash
# イメージビルド
docker build -t sciencebuddy:latest .

# ローカル実行（データ永続化）
docker run -it --rm -p 8080:8080 \
  -v $(pwd)/data:/data \
  -e OPENAI_API_KEY=your_key \
  -e FLASK_ENV=production \
  sciencebuddy:latest
```

### 6.3 本番環境（Google Cloud Run）

#### 6.3.1 Cloud Run デプロイ

```bash
# 1. Google Cloud 認証
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Cloud Storage バケット作成
gsutil mb gs://science-buddy-logs/

# 3. Cloud Run デプロイ
gcloud run deploy science-buddy \
  --source . \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=your_key,GCP_PROJECT_ID=YOUR_PROJECT_ID,GCS_BUCKET_NAME=science-buddy-logs,FLASK_ENV=production \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10
```

#### 6.3.2 Cloud Build 設定（cloudbuild.yaml）

```yaml
steps:
  # Docker イメージビルド
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/sciencebuddy:$COMMIT_SHA', '.']
  
  # Container Registry へプッシュ
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/sciencebuddy:$COMMIT_SHA']
  
  # Cloud Run へデプロイ
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'science-buddy'
      - '--image=gcr.io/$PROJECT_ID/sciencebuddy:$COMMIT_SHA'
      - '--region=asia-northeast1'
      - '--platform=managed'

images:
  - 'gcr.io/$PROJECT_ID/sciencebuddy:$COMMIT_SHA'
```

#### 6.3.3 CI/CD パイプライン

```bash
# GitHub リポジトリと Cloud Build 連携
gcloud builds triggers create github \
  --repo-name=scienceapp2 \
  --repo-owner=nov11masaki \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

### 6.4 環境変数設定

#### 6.4.1 開発環境（.env）

```bash
OPENAI_API_KEY=sk-proj-...
FLASK_ENV=development
PORT=5014
```

#### 6.4.2 本番環境（Cloud Run）

```bash
# 必須
OPENAI_API_KEY=sk-proj-...
FLASK_ENV=production
GCP_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=science-buddy-logs

# オプション
PORT=8080
USE_FIRESTORE=1
FIRESTORE_DATABASE=rika
FORCE_SYNC_SUMMARY=true
```

---

## 7. モニタリング・ロギング

### 7.1 ロギング戦略

#### 7.1.1 ログレベル

```python
import logging

# 開発環境: DEBUG
# 本番環境: INFO

if os.getenv('FLASK_ENV') == 'development':
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)
```

#### 7.1.2 ログ出力先

```python
# 学習ログ
logs/learning_log_YYYYMMDD.json

# エラーログ
error_logs/error_log_YYYYMMDD.json

# アプリケーションログ（標準出力）
# Cloud Run では自動的に Cloud Logging へ
print(f"[INFO] {message}")
print(f"[ERROR] {error_message}")
```

#### 7.1.3 構造化ロギング

```python
import json
from datetime import datetime

def log_event(event_type, data):
    """構造化ログ出力"""
    log_entry = {
        "timestamp": now_jst_isoformat(),
        "event_type": event_type,
        "data": data
    }
    print(json.dumps(log_entry, ensure_ascii=False))
```

### 7.2 パフォーマンスモニタリング

#### 7.2.1 Cloud Run メトリクス

- **リクエスト数**: `/teacher/dashboard` へのアクセス頻度
- **レスポンスタイム**: P50, P95, P99
- **エラー率**: 5xx エラーの発生率
- **CPU 使用率**: コンテナの CPU 使用状況
- **メモリ使用率**: コンテナのメモリ使用状況

#### 7.2.2 OpenAI API 使用量

```python
# API コールのカウント
api_call_count = 0
total_tokens = 0

def track_openai_usage(response):
    global api_call_count, total_tokens
    api_call_count += 1
    total_tokens += response.usage.total_tokens
    
    print(f"[OPENAI_USAGE] Calls: {api_call_count}, Tokens: {total_tokens}")
```

### 7.3 エラー追跡

#### 7.3.1 エラーハンドリング

```python
@app.errorhandler(Exception)
def handle_exception(e):
    """全ての例外をキャッチしてログ記録"""
    import traceback
    
    error_data = {
        "timestamp": now_jst_isoformat(),
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc(),
        "request_url": request.url,
        "request_method": request.method
    }
    
    # エラーログに記録
    save_error_log(error_data)
    
    # ユーザーには親切なメッセージ
    return jsonify({"error": "システムエラーが発生しました"}), 500
```

#### 7.3.2 クライアントサイドエラー報告

```javascript
// JavaScript でのエラー送信
function reportError(errorMessage) {
    fetch('/report_error', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            error: errorMessage,
            url: window.location.href,
            userAgent: navigator.userAgent
        })
    });
}
```

---

## 8. パフォーマンス最適化

### 8.1 キャッシング戦略

#### 8.1.1 関数レベルキャッシング

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def load_prompt(unit, stage):
    """プロンプトファイルをキャッシュ"""
    prompt_path = PROMPTS_DIR / f"{unit}_{stage}.md"
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()
```

#### 8.1.2 セッションキャッシング

```python
# セッションデータをメモリにキャッシュ
session_cache = {}

def get_cached_session(student_id, unit, stage):
    cache_key = f"{student_id}_{unit}_{stage}"
    if cache_key in session_cache:
        return session_cache[cache_key]
    
    # データベースから取得
    data = load_session_from_db(student_id, unit, stage)
    session_cache[cache_key] = data
    return data
```

### 8.2 非同期処理

#### 8.2.1 RQ（Redis Queue）による非同期化

```python
# tools/worker.py
from rq import Worker, Queue, Connection
import redis

redis_conn = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

with Connection(redis_conn):
    worker = Worker(['default'])
    worker.work()
```

```python
# app.py での非同期ジョブ投入
from rq import Queue
from redis import Redis

redis_conn = Redis()
queue = Queue(connection=redis_conn)

# 要約生成を非同期化
job = queue.enqueue(
    'tools.worker.generate_summary_async',
    conversation=conversation,
    unit=unit,
    timeout=120
)

return jsonify({"job_id": job.id})
```

#### 8.2.2 同期処理モード

```python
# 環境変数で同期処理を強制
FORCE_SYNC_SUMMARY = os.getenv('FORCE_SYNC_SUMMARY', 'false').lower() == 'true'

if FORCE_SYNC_SUMMARY:
    # 即座に要約を生成
    summary = generate_summary(conversation, unit)
    return jsonify({"summary": summary})
else:
    # 非同期ジョブを投入
    job = queue.enqueue(...)
    return jsonify({"job_id": job.id})
```

### 8.3 データベース最適化

#### 8.3.1 バッチ読み込み

```python
def load_all_logs_for_date(date_str):
    """指定日付のログを一括読み込み"""
    log_file = f"logs/learning_log_{date_str}.json"
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []
```

#### 8.3.2 インデックス最適化（将来的にDB導入時）

```python
# Firestore インデックス
# student_id + unit + stage の複合インデックス
# timestamp の降順インデックス
```

### 8.4 フロントエンド最適化

#### 8.4.1 CSS/JS の最小化

```html
<!-- 本番環境では minified 版を使用 -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
```

#### 8.4.2 遅延ロード

```javascript
// 画像の遅延ロード
<img src="placeholder.jpg" data-src="actual-image.jpg" loading="lazy">

// JavaScript の遅延実行
document.addEventListener('DOMContentLoaded', function() {
    // 初期化処理
});
```

### 8.5 OpenAI API 最適化

#### 8.5.1 トークン削減

```python
# 会話履歴の制限
MAX_CONVERSATION_LENGTH = 20  # 最大20ターン

if len(conversation) > MAX_CONVERSATION_LENGTH:
    # 古い会話を削除（システムメッセージは保持）
    conversation = [conversation[0]] + conversation[-(MAX_CONVERSATION_LENGTH-1):]
```

#### 8.5.2 レート制限対応

```python
import time
from openai import RateLimitError

def call_openai_with_retry(func, max_retries=3):
    """OpenAI API 呼び出しをリトライ付きで実行"""
    for i in range(max_retries):
        try:
            return func()
        except RateLimitError:
            if i < max_retries - 1:
                wait_time = (2 ** i) * 1  # 指数バックオフ
                time.sleep(wait_time)
            else:
                raise
```

---

## 9. テスト戦略

### 9.1 手動テストシナリオ

#### 9.1.1 学習者フロー

1. クラス選択（1組〜4組、研究室）
2. 出席番号選択（1〜30番）
3. 単元選択（5単元）
4. 予想段階の対話（3〜5ターン）
5. 予想のまとめ
6. 考察段階の対話（3〜5ターン）
7. 考察のまとめ
8. 学習履歴の確認

#### 9.1.2 教員フロー

1. 教員ログイン
2. ダッシュボードで学習状況確認
3. 学習ログの詳細表示
4. 分析ダッシュボードでクラス分析
5. CSV/JSON エクスポート

### 9.2 ユニットテスト（今後実装）

```python
# tests/test_analysis.py
import unittest
from tools.analysis import calculate_science_term_ratio

class TestAnalysis(unittest.TestCase):
    def test_science_term_ratio(self):
        text = "温度が高い時、空気が大きくなります"
        unit = "空気の温度と体積"
        ratio, terms = calculate_science_term_ratio(text, unit)
        
        self.assertGreater(ratio, 0)
        self.assertIn("温度", terms)
        self.assertIn("空気", terms)
```

### 9.3 統合テスト（今後実装）

```python
# tests/test_integration.py
import unittest
from app import app

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_prediction_flow(self):
        # クラス選択
        response = self.app.get('/select_number?class=1')
        self.assertEqual(response.status_code, 200)
        
        # 予想ページ
        with self.app.session_transaction() as sess:
            sess['student_id'] = 4101
            sess['class'] = 1
        
        response = self.app.get('/prediction?unit=空気の温度と体積')
        self.assertEqual(response.status_code, 200)
```

---

## 10. 保守・運用

### 10.1 バックアップ戦略

#### 10.1.1 GCS データバックアップ

```bash
# 日次バックアップスクリプト
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_BUCKET="gs://science-buddy-backup"

gsutil -m rsync -r gs://science-buddy-logs/ ${BACKUP_BUCKET}/${DATE}/
```

#### 10.1.2 ローカルデータバックアップ

```bash
# ローカル環境のバックアップ
tar -czf backup_$(date +%Y%m%d).tar.gz \
  learning_progress.json \
  session_storage.json \
  summary_storage.json \
  logs/
```

### 10.2 トラブルシューティング

#### 10.2.1 よくある問題と解決策

| 問題 | 原因 | 解決策 |
|------|------|--------|
| OpenAI API エラー | APIキー未設定 | `.env` に `OPENAI_API_KEY` を設定 |
| GCS 接続エラー | 認証情報不足 | `gcloud auth login` で認証 |
| セッション消失 | Cookie 削除 | ブラウザキャッシュクリア、再ログイン |
| 要約生成失敗 | 会話不足 | より多くの対話を促す |

#### 10.2.2 デバッグモード

```python
# 開発環境でデバッグモード有効化
if os.getenv('FLASK_ENV') == 'development':
    app.debug = True
    app.config['PROPAGATE_EXCEPTIONS'] = True
```

### 10.3 スケーリング戦略

#### 10.3.1 水平スケーリング（Cloud Run）

```bash
# 最大インスタンス数を増やす
gcloud run services update science-buddy \
  --max-instances=50 \
  --concurrency=80
```

#### 10.3.2 垂直スケーリング

```bash
# CPU/メモリを増やす
gcloud run services update science-buddy \
  --memory=2Gi \
  --cpu=2
```

---

## 11. 技術的負債管理

### 11.1 既知の技術的負債

| 項目 | 現状 | 改善計画 |
|------|------|---------|
| **テストカバレッジ** | なし | ユニットテスト導入 |
| **コード品質** | 単一ファイル（3488行） | モジュール分割 |
| **認証システム** | 簡易実装（環境変数） | より堅牢な認証方式検討 |
| **ログ管理** | JSON ファイル / GCS | 構造化ログの強化 |

### 11.2 リファクタリング優先順位

1. **高優先度**: テストコード追加、エラーハンドリング強化
2. **中優先度**: app.py のモジュール分割
3. **低優先度**: パフォーマンスチューニング

---

## 12. 付録

### 12.1 用語集

| 用語 | 説明 |
|------|------|
| **JST** | 日本標準時（UTC+9） |
| **GCS** | Google Cloud Storage |
| **ADC** | Application Default Credentials |
| **RQ** | Redis Queue（Pythonジョブキュー） |
| **Embeddings** | テキストのベクトル表現 |

### 12.2 参考資料

- [Flask Documentation](https://flask.palletsprojects.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Bootstrap 5 Documentation](https://getbootstrap.com/docs/5.0/)
- [scikit-learn Documentation](https://scikit-learn.org/stable/)

---

**文書終了**

**最終更新**: 2026年1月26日  
**作成者**: nov11masaki  
**バージョン**: 2.0

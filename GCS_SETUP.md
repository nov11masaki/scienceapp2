# ScienceBuddy - GCS（Google Cloud Storage）セットアップガイド

本番環境で、学習ログを **Google Cloud Storage（GCS）** に自動保存するための設定ガイドです。

---

## 概要

ScienceBuddy は以下の環境に応じて自動的にストレージを切り替えます：

| 環境 | ストレージ | 用途 |
|------|-----------|------|
| **ローカル開発** | ローカル JSON ファイル | 開発・テスト用 |
| **Cloud Run 本番** | **Google Cloud Storage** | 本番運用・複数サーバー対応 |

環境変数 `FLASK_ENV=production` が設定されると、自動的に GCS 使用開始します。

---

## 1️⃣ Google Cloud Storage バケット作成

### 手順

1. **Cloud Console へアクセス**
   - [Google Cloud Console](https://console.cloud.google.com/)

2. **ナビゲーションメニュー** → **Cloud Storage** → **バケット**

3. **バケットを作成** をクリック

4. **バケット設定**

| 項目 | 設定値 | 説明 |
|------|--------|------|
| **バケット名** | `science-buddy-logs` | グローバルに一意の名前が必要 |
| **リージョンを選択** | `asia-northeast1` | 東京（日本のユーザー向け） |
| **ストレージクラス** | `標準` | アクセス頻度が高いため |
| **オブジェクトへのアクセス制御** | 均一 | シンプル且つ十分なセキュリティ |
| **保護ツール** | なし | 開発段階ではデフォルト |

5. **作成** をクリック

### バケット構造（自動生成される）

```
science-buddy-logs/
├── logs/
│   └── learning_log_YYYYMMDD.json
├── sessions/
│   └── {class}_{student}/{unit}/{stage}.json
└── summaries/
    └── {class}_{student}/{unit}/{stage}_summary.json
```

---

## 2️⃣ IAM 権限設定（サービスアカウント）

Cloud Run が GCS にアクセスするために必要な権限設定です。

### 2.1 デフォルトサービスアカウントの確認

1. **ナビゲーション** → **IAM と管理** → **サービスアカウント**

2. **デフォルトのサービスアカウント**を探す
   - 形式：`YOUR_PROJECT_ID@appspot.gserviceaccount.com`
   - 例：`my-science-project-2025@appspot.gserviceaccount.com`

### 2.2 Cloud Run に権限を付与

#### 方法 A：IAM ロール付与（推奨）

1. **ナビゲーション** → **IAM と管理** → **IAM**

2. **アクセス権を付与** をクリック

3. **プリンシパル**：
   - `YOUR_PROJECT_ID@appspot.gserviceaccount.com`

4. **ロール**を追加：
   - `Storage Object Creator`（ログ書き込み用）
   - `Storage Object Viewer`（ログ読み込み用）
   - または一括：`Storage Admin`

5. **保存**

#### 方法 B：バケットレベルの権限（代替案）

1. Cloud Storage 内の作成したバケットをクリック

2. **権限** タブ

3. **プリンシパルを追加**
   - プリンシパル：`YOUR_PROJECT_ID@appspot.gserviceaccount.com`
   - ロール：`Storage Object Admin`

4. **保存**

---

## 3️⃣ 環境変数の設定

Cloud Run のデプロイ時に以下の環境変数を設定します。

### 環境変数一覧

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
FLASK_ENV=production
GCP_PROJECT_ID=my-science-project-2025
GCS_BUCKET_NAME=science-buddy-logs
```

### 各変数の説明

| 変数 | 値 | 取得方法 |
|------|-----|----------|
| **OPENAI_API_KEY** | OpenAI API キー | [platform.openai.com](https://platform.openai.com/api-keys) |
| **FLASK_ENV** | `production` | 固定値（GCS 有効化トリガー） |
| **GCP_PROJECT_ID** | プロジェクト ID | GCP Console の右上に表示 |
| **GCS_BUCKET_NAME** | `science-buddy-logs` | 手順 1 で作成した名前 |

### GCP_PROJECT_ID の確認方法

1. [Google Cloud Console](https://console.cloud.google.com/)
2. ページ右上の **PROJECT ID** をコピー
3. 例：`my-science-project-2025`

---

## 4️⃣ Cloud Run デプロイ時の環境変数設定

### ダッシュボードでの設定

1. **Cloud Run** → **サービスを作成** または **既存サービス編集**

2. **詳細設定を表示** をクリック

3. **環境変数** セクション

4. 以下を入力：

```
OPENAI_API_KEY = sk-xxxxxxxxxxxx
FLASK_ENV = production
GCP_PROJECT_ID = my-science-project-2025
GCS_BUCKET_NAME = science-buddy-logs
```

5. **デプロイ** をクリック

### 確認

デプロイ完了後、Cloud Run ログを確認：

```
[INIT] GCS bucket 'science-buddy-logs' initialized successfully
```

このメッセージが出れば成功です。

---

## 5️⃣ セキュリティ・ベストプラクティス

### API キーの安全な管理

⚠️ **重要：** 本番環境では API キーを平文で保存しないでください。

#### 推奨方法：Cloud Secret Manager

1. **Secret Manager を有効化**
   - ナビゲーション → **Secret Manager**

2. **シークレットを作成**
   - 名前：`OPENAI_API_KEY`
   - 値：API キー

3. **Cloud Run に権限を付与**
   - サービスアカウントに `Secret Accessor` ロール

4. **app.py で読み込み**

```python
from google.cloud import secretmanager

def access_secret_version(secret_id, version_id="latest"):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

api_key = access_secret_version("OPENAI_API_KEY")
```

#### 参考
- [Secret Manager 統合](https://cloud.google.com/run/docs/configuring/secrets)
- [Secret Manager Python クライアント](https://cloud.google.com/python/docs/reference/secretmanager/latest)

---

## 6️⃣ ストレージ構造と保存内容

### ログファイル構造

```
gs://science-buddy-logs/
├── logs/
│   ├── learning_log_20250101.json  # 日付ごとのログ
│   ├── learning_log_20250102.json
│   └── ...
├── sessions/
│   └── 1_15/  # {class}_{student}
│       ├── 金属のあたたまり方/
│       │   ├── prediction.json
│       │   └── reflection.json
│       └── 水のあたたまり方/
│           ├── prediction.json
│           └── reflection.json
└── summaries/
    └── 1_15/
        └── 金属のあたたまり方/
            ├── prediction_summary.json
            └── reflection_summary.json
```

### ログ内容の例

**learning_log_YYYYMMDD.json:**
```json
[
  {
    "timestamp": "2025-01-15T10:30:45.123456",
    "student_number": "4115",
    "class_num": 1,
    "seat_num": 15,
    "class_display": "1組15番",
    "unit": "金属のあたたまり方",
    "log_type": "prediction_chat",
    "data": {
      "user_message": "あたたかくなると思います",
      "ai_response": "どうしてそう思ったの？"
    }
  },
  ...
]
```

**sessions/{class}_{student}/{unit}/{stage}.json:**
```json
{
  "timestamp": "2025-01-15T10:35:00.000000",
  "student_id": "1_15",
  "unit": "金属のあたたまり方",
  "stage": "prediction",
  "conversation": [
    {"role": "assistant", "content": "実験でどうなると思う？"},
    {"role": "user", "content": "あたたかくなると思います"},
    ...
  ]
}
```

---

## 7️⃣ ログの確認・ダウンロード

### GCS Console で確認

1. **Cloud Storage** → バケット `science-buddy-logs`

2. 各フォルダをクリックして JSON ファイルを確認

3. **ダウンロード** → ローカルで分析可能

### コマンドラインで確認

```bash
# Google Cloud SDK インストール必須
# https://cloud.google.com/sdk/docs/install

# バケット内容を一覧表示
gsutil ls -r gs://science-buddy-logs/

# 特定のファイルをダウンロード
gsutil cp gs://science-buddy-logs/logs/learning_log_20250115.json ./

# JSON を整形表示
gsutil cat gs://science-buddy-logs/logs/learning_log_20250115.json | jq .
```

---

## 8️⃣ トラブルシューティング

### 問題：「GCS bucket initialization failed」エラー

**原因：** 環境変数未設定または権限不足

**解決：**
1. `GCP_PROJECT_ID` と `GCS_BUCKET_NAME` を確認
2. サービスアカウント権限を確認（手順 2.2）
3. バケットが存在するか確認

### 問題：ログが GCS に保存されない

**原因 1：** `FLASK_ENV` が `production` に設定されていない

**確認コマンド：**
```bash
# Cloud Run ログで確認
[INIT] USE_GCS: False  # これなら環境変数設定ミス
```

**解決：** 環境変数を再設定してデプロイ

**原因 2：** 権限不足

**確認：**
1. IAM で `Storage Object Creator` ロールを確認
2. エラーメッセージで詳細確認

```
[GCS_SAVE] ERROR - Permission denied
```

### 問題：バケットへのアクセスタイムアウト

**原因：** ネットワーク遅延またはリージョン設定

**解決：**
- バケットリージョンと Cloud Run リージョンを同じ（`asia-northeast1`）に統一

---

## 9️⃣ コスト見積もり

### GCS の料金

| 項目 | 単価 | 月間予想（学校利用） |
|------|------|-----------|
| ストレージ（標準） | $0.020/GB | $0～1 |
| API 呼び出し（Class A） | $0.05/10万回 | $0～0.5 |
| ネットワーク（エグレス） | $0.12/GB | $0（1GB/月無料） |

**予想月間コスト：** $1～2（30人クラス × 3回実験 × 1学期）

### 削減のコツ
- ローカルテスト時は JSON ファイル使用
- 本番環境のみ GCS 使用
- 古いログは定期的にアーカイブ

---

## 🔟 データ保持ポリシー

### 推奨設定

1. **ライフサイクルルール**
   - 90日以上のログは自動削除
   - または `Nearline` ストレージクラスに移行

2. **設定方法**

```bash
# ライフサイクルルール JSON
cat > lifecycle.json << 'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF

# 適用
gsutil lifecycle set lifecycle.json gs://science-buddy-logs/
```

---

## 参考リンク

- [Google Cloud Storage 公式ドキュメント](https://cloud.google.com/storage/docs)
- [GCS Python クライアント](https://cloud.google.com/python/docs/reference/storage/latest)
- [Cloud Run と GCS 統合](https://cloud.google.com/run/docs/tutorials/connect-to-sql)
- [IAM ロール リファレンス](https://cloud.google.com/iam/docs/understanding-roles)

---

**GCS セットアップが完了すれば、複数クラスの同時利用や中断・復帰が安定して動作します。**

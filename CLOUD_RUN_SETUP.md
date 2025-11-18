# ScienceBuddy - Cloud Run デプロイメント ガイド

本ガイドでは、ScienceBuddyアプリケーションをGoogle Cloud RunにデプロイするためのステップをGCPダッシュボードで実施する方法を説明します。

---

## 📋 前提条件

- Google Cloud アカウント（請求先設定済み）
- GitHub リポジトリ `nov11masaki/scienceapp2` にコードをプッシュ完了
- GCP プロジェクトが作成済み

---

## 1️⃣ GCP プロジェクトのセットアップ

### 1.1 プロジェクトの選択

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. ページ上部の「プロジェクト選択」をクリック
3. 既存プロジェクトを選択するか、新規作成

### 1.2 必須 API の有効化

1. **Cloud Run API** を有効化
   - ナビゲーション → APIとサービス → ライブラリ
   - 「Cloud Run」を検索 → 有効化

2. **Cloud Build API** を有効化
   - 同様に「Cloud Build」を検索 → 有効化

3. **Cloud Storage API** を有効化（GCS 使用時）
   - 「Cloud Storage」を検索 → 有効化

---

## 2️⃣ GCS バケットの作成と設定

### 2.1 バケット作成

1. ナビゲーション → Cloud Storage → バケット
2. **バケットを作成**
   - **バケット名**：`science-buddy-logs`（または任意の名前、グローバルに一意）
   - **ロケーション**：`asia-northeast1`（東京推奨）
   - **ストレージクラス**：`標準`
   - **オブジェクトへのアクセス制御**：均一（推奨）
   - 他はデフォルト設定で OK → 作成

### 2.2 バケットの権限設定

1. 作成したバケットをクリック
2. **権限** タブ
3. **プリンシパルを追加**
   - プリンシパル：`App Engine default service account: YOUR_PROJECT_ID@appspot.gserviceaccount.com`
   - ロール：`Storage Object Admin`、`Storage Legacy Bucket Writer`
   - 保存

### 2.3 バケット内にフォルダ構造を作成（オプション）

GCS 内に以下のフォルダ構造を手動で作成（自動生成される場合もあります）：
```
science-buddy-logs/
├── logs/
├── sessions/
├── summaries/
```

---

## 3️⃣ Cloud Run サービスのデプロイ（ダッシュボード操作）

### 3.1 Cloud Run への移動

1. ナビゲーション → Cloud Run
2. **サービスを作成** をクリック

### 3.2 デプロイメント設定

#### **デプロイ方法**
- **GitHub をクリック**
  - GitHub アカウント認証
  - リポジトリ：`nov11masaki/scienceapp2` を選択
  - ブランチ：`main`（デプォルト）

#### **ビルド設定**
- **Dockerfile の場所**：`./Dockerfile`（自動検出されるはず）
- **イメージ名**：自動生成（デフォルト）

### 3.3 サービス設定

| 項目 | 推奨値 | 説明 |
|------|--------|------|
| **サービス名** | `sciencebuddy-app` | わかりやすい名前 |
| **リージョン** | `asia-northeast1` | 東京リージョン（日本ユーザー向け） |
| **認証** | 認証が不要 | 学校で利用するため公開設定 |
| **CPU** | `1 CPU` | 小～中規模トラフィック向け |
| **メモリ** | `1 GB` | 4年生クラス（30人）向けに十分 |
| **タイムアウト** | `60 秒`（デフォルト） | APIレスポンス待機用 |
| **最大同時実行数** | `100`（デフォルト） | 複数クラス同時利用対応 |
| **スケーリング** | `最小 0、最大 100` | 使用がない時は自動停止 |

### 3.4 環境変数の設定

**詳細設定** → **環境変数** に以下を追加：

```
OPENAI_API_KEY=sk-xxxxxxxxxxxx
FLASK_ENV=production
GCP_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=science-buddy-logs
```

**詳細説明：**
- `OPENAI_API_KEY`：OpenAI APIキー（セキュリティ管理をお勧め：Cloud Secret Manager 使用）
- `FLASK_ENV`：本番環境として `production` に設定（GCS 使用開始）
- `GCP_PROJECT_ID`：GCP プロジェクト ID（例：`my-science-project-2025`）
- `GCS_BUCKET_NAME`：手順 2.1 で作成したバケット名

### 3.5 デプロイを実行

1. **デプロイ** をクリック
2. ビルドが開始（約 3～10 分程度）
3. 完了すると URL が表示される
   - 例：`https://sciencebuddy-app-xxx-an.a.run.app`

---

## 4️⃣ デプロイ後の動作確認

### 4.1 エンドポイントテスト

```bash
curl -I https://sciencebuddy-app-xxx-an.a.run.app/
```

**予想される応答：** `200 OK`

### 4.2 ログ確認

1. Cloud Run サービスをクリック
2. **ログ** タブ
3. エラーがないか確認
4. **GCS バケット内のログ** も確認
   - `science-buddy-logs/logs/` フォルダを確認

### 4.3 機能テスト

ブラウザで `https://sciencebuddy-app-xxx-an.a.run.app` にアクセス：
1. クラス、出席番号を選択
2. 単元を選択
3. AI との対話で予想をまとめる
4. ログが GCS に保存されるか確認

---

## 🔧 パフォーマンス・スペック推奨値

### CPU・メモリの選択基準

| 利用規模 | CPU | メモリ | 理由 |
|---------|-----|--------|------|
| 1クラス同時利用（30人） | 0.5 CPU | 512 MB | 小規模なら最小スペック |
| 2～3クラス同時利用 | **1 CPU** | **1 GB** | **このアプリに推奨** |
| 全学年フルロード（100+人） | 2 CPU | 2 GB | スケーリング時の安全マージン |

### 理由
- **Flask アプリ本体**：軽量（通常 50～100 MB）
- **OpenAI API 通信**：ネットワーク I/O 中心（CPU 消費低い）
- **JSON ログ処理**：メモリ使用量少ない
- **同時実行数**：デフォルト 100 で十分（自動スケーリング対応）

### タイムアウト設定
- **デフォルト 60 秒**で問題なし
- OpenAI API レスポンス：通常 2～5 秒
- 遅い回線でも 15 秒以内

---

## 📊 本番環境設定（ローカル JSON → GCS 自動切り替え）

アプリケーションは自動的に環境を判定します：

```python
USE_GCS = os.getenv('FLASK_ENV') == 'production' and os.getenv('GCP_PROJECT_ID')
```

| 環境 | FLASK_ENV | USE_GCS | ストレージ |
|------|-----------|---------|-----------|
| ローカル開発 | development | False | ローカル JSON |
| Cloud Run | production | True | **GCS（自動）** |

---

## 🔐 セキュリティ上の注意

### API キーの管理

**重要：** 環境変数に平文で API キーを置かないこと

推奨方法：**Google Cloud Secret Manager** を使用

1. Secret Manager を有効化
2. シークレット `OPENAI_API_KEY` を作成
3. Cloud Run に権限付与
4. 環境変数から削除し、アプリでシークレットマネージャーから読み込み

参考：[Cloud Run - Secret Manager](https://cloud.google.com/run/docs/configuring/secrets)

---

## 📈 自動スケーリング・コスト管理

### Cloud Run の料金体系
- **実行時間**：CPU・メモリ使用量に基づく（秒単位）
- **リクエスト**：100万リクエスト/月まで無料
- **ネットワーク**：1 GB/月まで無料エグレス

### コスト削減のコツ
1. **使用がない時は自動停止**（デフォルト）
2. **メモリは必要最小限**（512 MB でも動作可）
3. **タイムアウト短縮**は非推奨（エラー増加）

---

## 🚀 継続的デプロイメント

GitHub にプッシュすると自動デプロイされます：

1. `main` ブランチに新しいコミットをプッシュ
2. Cloud Build が自動で起動
3. ビルド成功後、Cloud Run が自動で最新バージョンにデプロイ

**ビルド状況確認：**
- Cloud Run → サービス → **ビルド** タブで確認

---

## 🐛 トラブルシューティング

### ビルドが失敗する

**原因：** Dockerfile か requirements.txt に問題

**解決：**
1. ローカルでテスト：`docker build -t sciencebuddy .`
2. エラーメッセージを確認
3. requirements.txt の互換性チェック

### ログが GCS に保存されない

**原因：** 環境変数未設定または権限不足

**解決：**
1. `GCP_PROJECT_ID` と `GCS_BUCKET_NAME` を確認
2. サービスアカウント権限を確認
3. ローカルで `USE_GCS` の値をデバッグ出力

### API レスポンスが遅い

**原因：** OpenAI API のレート制限または回線遅延

**解決：**
1. OpenAI API の使用状況を確認
2. リトライロジック確認（コード内で自動リトライ実装済み）
3. CPU・メモリ増強を検討

---

## 📞 参考リンク

- [Google Cloud Run ドキュメント](https://cloud.google.com/run/docs)
- [GitHub 連携（自動デプロイ）](https://cloud.google.com/run/docs/quickstarts/build-and-deploy)
- [Cloud Storage ドキュメント](https://cloud.google.com/storage/docs)
- [Secret Manager 統合](https://cloud.google.com/run/docs/configuring/secrets)

---

**設定に不明な点があれば、GCP ダッシュボードの "サポート" チャットで相談できます。**

# ScienceBuddy - Cloud Run デプロイメント完了レポート

**作成日**：2025年11月18日  
**プロジェクト**：ScienceBuddy（小学4年理科 AI対話型学習支援アプリ）  
**デプロイメント先**：Google Cloud Run  
**リポジトリ**：https://github.com/nov11masaki/scienceapp2

---

## ✅ 完了した作業

### 1. GitHub リポジトリへの登録
- ✅ ローカルリポジトリを初期化
- ✅ `nov11masaki/scienceapp2` リモートリポジトリを設定
- ✅ すべてのアプリケーションコードをプッシュ完了
- ✅ **リポジトリ URL**：https://github.com/nov11masaki/scienceapp2

### 2. Cloud Run デプロイメント準備
- ✅ **Dockerfile** を作成（Python 3.11-slim ベース）
  - Port 8080 設定（CloudRun 標準）
  - gunicorn で 2 workers/2 threads
  - 本番環境設定（FLASK_ENV=production）
  
- ✅ **requirements.txt** を更新
  - `google-cloud-storage>=2.13.0` を追加
  - その他の依存パッケージ確認・維持
  
- ✅ **.dockerignore** を設定
  - 開発ファイル、ログ、テンポラリファイルを除外
  - イメージサイズ最適化

- ✅ **app.py** のポート設定確認
  - 環境変数から PORT 自動取得
  - CloudRun 標準対応済み

### 3. 本番環境ストレージ設定
- ✅ ローカル JSON ↔ Google Cloud Storage（GCS）の自動切り替え
- ✅ `FLASK_ENV=production` で自動的に GCS 使用開始
- ✅ セッション永続化（中断・復帰対応）
- ✅ 学習ログのハイブリッド保存

### 4. 予想 → 考察の受け渡し確認
- ✅ 予想完了時に `prediction_summary` をセッションに保存
- ✅ 考察ページでセッションから復元
- ✅ 中断後も GCS/ローカル JSON から復元対応
- ✅ 考察のシステムプロンプトに予想を自動挿入
- ✅ **中断後も予想情報を確実に受け渡し** ✨

### 5. ドキュメント作成
- ✅ **CLOUD_RUN_SETUP.md**
  - Cloud Run デプロイ手順（ダッシュボード操作）
  - CPU/メモリ推奨値：1 CPU、1 GB メモリ
  - 環境変数設定一覧
  
- ✅ **GCS_SETUP.md**
  - バケット作成・IAM 設定手順
  - セキュリティ・ベストプラクティス
  - トラブルシューティング
  
- ✅ **GITHUB_PUSH_GUIDE.md**
  - GitHub へのプッシュ手順
  - エラー解決方法

---

## 📊 推奨リソース設定

### Cloud Run スペック

| 項目 | 推奨値 | 理由 |
|------|--------|------|
| **CPU** | 1 CPU | Flask + OpenAI API 通信で十分 |
| **メモリ** | 1 GB | JSON ログ処理・セッション管理に十分 |
| **タイムアウト** | 60 秒 | OpenAI API レスポンス待機用 |
| **最大同時実行数** | 100（デフォルト） | 複数クラス同時利用対応 |
| **スケーリング** | 最小 0、最大 100 | 使用がない時は自動停止 |
| **リージョン** | `asia-northeast1`（東京） | 日本ユーザー向け低遅延 |

### 月間予想コスト
- **Cloud Run**：$2～5（使用量に基づく）
- **GCS ストレージ**：$0.50～1
- **ネットワーク**：$0（1GB/月無料）
- **API リクエスト**：$0～0.50

**合計：$3～7/月**（30人クラス × 3単元利用想定）

---

## 🔧 デプロイメント手順クイックガイド

### ステップ 1：GCP ダッシュボードでの設定（5～10 分）

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. **Cloud Run API** と **Cloud Build API** を有効化
3. GCS バケット `science-buddy-logs` を作成
4. サービスアカウントに権限を付与

### ステップ 2：Cloud Run デプロイ

1. **Cloud Run** → **サービスを作成**
2. **GitHub から配置**
   - リポジトリ：`nov11masaki/scienceapp2`
   - ブランチ：`main`
3. **サービス設定**
   - 名前：`sciencebuddy-app`
   - リージョン：`asia-northeast1`
   - CPU：1、メモリ：1 GB

4. **環境変数を設定**
   ```
   OPENAI_API_KEY = sk-xxxxxxxxxxxx
   FLASK_ENV = production
   GCP_PROJECT_ID = your-project-id
   GCS_BUCKET_NAME = science-buddy-logs
   ```

5. **デプロイ実行**（ビルド完了まで約 10 分）

### ステップ 3：動作確認

- 本番 URL にアクセス
- クラス → 出席番号 → 単元 → AI 対話
- ログが GCS に保存されるか確認

---

## 🔐 セキュリティ考慮事項

### API キーの管理
- ⚠️ **本番環境では Secret Manager 使用推奨**
- `app.py` に Secret Manager 統合コード例あり

### ネットワークセキュリティ
- ✅ CloudRun は HTTPS 自動対応
- ✅ CORS 設定は環境に応じて検討

### データ保護
- ✅ GCS は REST 暗号化がデフォルト
- ✅ ログは `asia-northeast1` リージョンに保存（日本国内）

---

## 📈 継続的デプロイメント（CD）

GitHub main ブランチへプッシュ → 自動デプロイ開始（Cloud Build）

```bash
# 開発ローカルでの作業
git add .
git commit -m "Update: 〇〇を修正"
git push origin main

# ↓ 自動実行 ↓
# 1. Cloud Build がビルド開始
# 2. ビルド成功後、Cloud Run に自動デプロイ
# 3. 新 URL で本番環境が更新
```

**ビルド状況確認：**
- GCP Console → Cloud Build → ビルド履歴

---

## 🐛 トラブルシューティング

### ビルド失敗時
- **原因**：Dockerfile または requirements.txt に問題
- **解決**：Cloud Build ログを確認 → 修正後 git push

### ログが GCS に保存されない
- **原因**：環境変数未設定または権限不足
- **確認**：Cloud Run ログで `[INIT] GCS bucket... initialized` を探す
- **解決**：GITHUB_PUSH_GUIDE.md のトラブルシューティングを参照

### API レスポンスが遅い
- **原因**：OpenAI API レート制限
- **確認**：OpenAI API ダッシュボードで使用状況確認
- **解決**：CPU・メモリ増強を検討

---

## 📁 ファイル構成

```
scienceapp2/
├── app.py                    # メインアプリケーション
├── Dockerfile               # CloudRun 用デプロイメント設定
├── requirements.txt         # Python 依存パッケージ
├── .dockerignore            # Docker ビルド時の除外ファイル
├── CLOUD_RUN_SETUP.md       # CloudRun デプロイメント手順
├── GCS_SETUP.md             # GCS バケット設定手順
├── GITHUB_PUSH_GUIDE.md     # GitHub プッシュ手順
├── prompts/                 # AI プロンプトテンプレート
├── templates/               # HTML テンプレート
├── static/                  # CSS・画像ファイル
└── tasks/                   # 実験課題文
```

---

## ✨ 主要機能の動作確認チェックリスト

- [ ] ブラウザで本番 URL にアクセス可能
- [ ] クラス選択 → 出席番号選択 → 単元選択 が動作
- [ ] AI 対話が実行できる
- [ ] 予想をまとめる → 考察ページへ遷移
- [ ] 予想が考察ページに表示される
- [ ] 中断後、「考察に進む」で復帰可能
- [ ] ログが GCS に保存される（GCS Console で確認）

---

## 📞 次のステップ

1. **GCP ダッシュボードでセットアップ**
   - CLOUD_RUN_SETUP.md を参照
   - GCS_SETUP.md で GCS 設定

2. **デプロイ実行**
   - Cloud Run でサービス作成
   - 本番 URL を確認

3. **動作確認**
   - ブラウザでテスト
   - ログ確認

4. **運用開始**
   - 学校ネットワークで配信
   - 学生による利用開始

---

## 📚 参考資料

- [Google Cloud Run ドキュメント](https://cloud.google.com/run/docs)
- [Cloud Storage 公式ガイド](https://cloud.google.com/storage/docs)
- [Flask ドキュメント](https://flask.palletsprojects.com/)
- [OpenAI API リファレンス](https://platform.openai.com/docs)

---

**すべての設定が完了しました。GCP ダッシュボードでセットアップを開始してください。** 🚀

何か問題が生じた場合は、各ドキュメントのトラブルシューティングセクションを参照するか、GitHub Issues で報告してください。

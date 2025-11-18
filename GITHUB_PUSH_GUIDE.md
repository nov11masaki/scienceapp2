# GitHub へのプッシュ手順

ScienceBuddy をリモートリポジトリ `nov11masaki/scienceapp2` に登録するための手順です。

---

## 前提条件

- `git` がインストール済み
- GitHub アカウントでログイン済み
- SSH キーまたは Personal Access Token（PAT）が設定済み

---

## 手順 1：ローカルリポジトリの初期化（初回のみ）

```bash
cd /Users/shimizumasaki/ScienceBuddy

# Git リポジトリの初期化
git init

# ユーザー情報を設定（初回のみ）
git config user.name "Your Name"
git config user.email "your.email@example.com"

# グローバル設定にする場合：
# git config --global user.name "Your Name"
# git config --global user.email "your.email@example.com"
```

---

## 手順 2：リモートリポジトリを追加

```bash
git remote add origin https://github.com/nov11masaki/scienceapp2.git

# 確認
git remote -v
# 出力例：
# origin  https://github.com/nov11masaki/scienceapp2.git (fetch)
# origin  https://github.com/nov11masaki/scienceapp2.git (push)
```

### SSH を使用する場合

```bash
git remote add origin git@github.com:nov11masaki/scienceapp2.git
```

---

## 手順 3：初回のプッシュ

### 3.1 ファイルをステージングに追加

```bash
# すべてのファイルを追加（.gitignore に記載されたものを除く）
git add .

# ステージング状況確認
git status
```

### 3.2 コミットを作成

```bash
git commit -m "Initial commit: ScienceBuddy CloudRun deployment setup

- Added Dockerfile for CloudRun deployment
- Updated requirements.txt with google-cloud-storage
- Added .dockerignore for optimized builds
- Added CLOUD_RUN_SETUP.md deployment guide
- Added GCS_SETUP.md storage configuration guide
- Configured app.py for PORT 8080 (CloudRun standard)
- Verified prediction summary passing to reflection stage
- GCS integration for production logging"
```

### 3.3 デフォルトブランチを確認（GitHub Web で確認）

1. GitHub リポジトリにアクセス：`https://github.com/nov11masaki/scienceapp2`
2. **Settings** → **Branches**
3. **Default branch** を確認（通常は `main` または `master`）

### 3.4 プッシュ実行

**`main` ブランチの場合：**
```bash
git branch -M main
git push -u origin main
```

**`master` ブランチの場合：**
```bash
git push -u origin master
```

### 3.5 GitHub での確認

1. `https://github.com/nov11masaki/scienceapp2` をブラウザで開く
2. ファイルが反映されているか確認
3. コミットメッセージが表示されているか確認

---

## 手順 4：以降の更新手順

```bash
# ファイル変更後、以下を実行：

# 1. 変更を確認
git status

# 2. 変更をステージングに追加
git add .

# 3. コミットを作成
git commit -m "Update: 〇〇を修正"

# 4. プッシュ
git push origin main  # または master
```

---

## よくあるエラーと解決方法

### エラー 1：`fatal: could not read Username`

**原因：** GitHub 認証失敗

**解決：**
```bash
# PAT（Personal Access Token）での認証
git remote set-url origin https://YOUR_USERNAME:YOUR_PAT@github.com/nov11masaki/scienceapp2.git
git push origin main
```

### エラー 2：`fatal: 'origin' does not appear to be a 'git' repository`

**原因：** リモートが設定されていない

**解決：**
```bash
git remote add origin https://github.com/nov11masaki/scienceapp2.git
git push -u origin main
```

### エラー 3：`rejected ... (fetch first)`

**原因：** リモートとローカルの同期が取れていない

**解決：**
```bash
git pull origin main
git push origin main
```

### エラー 4：`permission denied (publickey)`（SSH の場合）

**原因：** SSH キー未設定

**解決：**
```bash
# HTTPS に切り替え
git remote set-url origin https://github.com/nov11masaki/scienceapp2.git

# または SSH キー設定：https://docs.github.com/en/authentication/connecting-to-github-with-ssh
```

---

## 参考リンク

- [Git ドキュメント](https://git-scm.com/doc)
- [GitHub CLI ガイド](https://cli.github.com/)
- [GitHub SSH キー設定](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [GitHub PAT 設定](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)

---

## 次のステップ

GitHub へのプッシュ後：

1. **Cloud Run 連携設定**
   - Cloud Build は GitHub リポジトリを検出
   - `main` ブランチへのプッシュで自動デプロイ開始

2. **デプロイ確認**
   - GCP Console → Cloud Build → ビルド履歴
   - ビルド完了後、Cloud Run で URL を確認

3. **動作確認**
   - 本番 URL にアクセス
   - ログが GCS に保存されているか確認

---

**設定に不明な点があれば、GitHub の Issues で質問できます。**

# セットアップ手順書(Windows PC)

案件データは **この Windows PC の中だけ** に保存されます。iPhone・他の Windows からは
Tailscale(私設ネットワーク)経由の HTTPS でアクセスします。インターネットには公開しません。

## 1. 必要なもの

| もの | 入手先・備考 |
|---|---|
| Python 3.11 以上 | https://www.python.org/ ― インストール時「Add python.exe to PATH」にチェック |
| Tailscale | https://tailscale.com/download ― PC と iPhone の両方に入れ、同じアカウントでログイン |
| バックアップ用の別ドライブ | 外付けHDD・別パーティション等(例: `D:\case-backup`) |

## 2. 初回設定

1. このフォルダ(`case-manager`)を PC の任意の場所に置く(例: `C:\case-manager`)。
2. `.env.example` をコピーして `.env` を作る。
3. アクセストークンを生成し、`.env` の `APP_TOKEN=` に貼る。
   ```
   py -3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   - トークンはパスワードと同じ扱い。パスワード管理ソフトに保管し、メール等で送らない。
4. `.env` の `BACKUP_DIR=` に別ドライブのフォルダを指定(例: `D:\case-backup`)。
5. 案件フォルダの置き場所を `ALLOWED_FOLDER_ROOTS=` に指定(例: `C:\Users\me\Documents\事件`)。
   これ以外の場所はアプリから参照できなくなる。
6. `start.bat` をダブルクリック。初回は必要なライブラリを自動でインストールする。
   「Uvicorn running on http://127.0.0.1:8765」と出れば起動完了。
7. PC のブラウザで http://127.0.0.1:8765 を開き、トークンでログイン。

> サーバーは `127.0.0.1`(この PC 自身)でしか待ち受けません。LAN の他の機器から直接は接続できません。

## 3. iPhone・他の PC からの接続(Tailscale Serve)

管理者権限のコマンドプロンプト(または PowerShell)で:

```
tailscale serve --bg 8765
tailscale serve status
```

`https://<PC名>.<tailnet名>.ts.net/` のような URL が表示されます。
この URL は **同じ Tailscale ネットワークに参加した端末からのみ** 開けます。

- `tailscale funnel` は **使わない**(インターネット公開になります)。
- Tailscale 管理画面で「HTTPS Certificates」を有効にしておく(初回のみ。Serve 実行時に案内が出ます)。
- 停止するとき: `tailscale serve reset`

### iPhone

1. Tailscale アプリを入れて同じアカウントでログインし、VPN をオンにする。
2. Safari で上記 URL を開き、トークンでログイン(iCloud キーチェーンに保存可)。
3. 共有ボタン →「ホーム画面に追加」。以後はアプリのように起動できます。

## 4. PC 起動時に自動起動する(任意)

1. `Win + R` → `shell:startup` でスタートアップフォルダを開く。
2. `start.bat` のショートカットを置く。

## 5. バックアップ

- サーバー稼働中は 1 時間ごとに確認し、前回から 24 時間経過していれば自動でバックアップします。
- PC を常時起動しない場合は、タスクスケジューラでも日次実行してください:
  ```
  schtasks /Create /SC DAILY /ST 12:30 /TN "案件管理バックアップ" /TR "C:\case-manager\backup.bat"
  ```
- 世代数は `.env` の `BACKUP_KEEP`(既定 30)。古いものから自動削除。
- 最終バックアップ日時はダッシュボード下部・「その他 → 設定」に表示。48 時間以上空くと警告。
- 復元: サーバーを停止し、`data\cases.sqlite3` をバックアップファイルで置き換える
  (`cases.sqlite3-wal`・`-shm` があれば削除してから)。

## 6. セキュリティ上の注意

- `.env` は他人に渡さない・クラウド同期フォルダに置かない。Git にも含まれません(`.gitignore` 済み)。
- トークンを変更したら `.env` を書き換えてサーバーを再起動。全端末で再ログインが必要になります。
- 機微案件(案件編集で「機微案件」にチェック)は、閲覧・変更時にトークンの再入力を求めます
  (有効時間は `REAUTH_MINUTES`、既定 10 分)。一覧・検索・通知では題名が伏せられます。
- ログイン失敗が 10 分間に 5 回続くと一時的にログインを拒否します。
- 操作ログ・監査ログ(「その他 → 操作ログ」)に、ログイン、すべての変更操作、機微案件の閲覧、
  資料の閲覧、利益相反チェック、期限の確定が記録されます。
- PC 自体の BitLocker(ドライブ暗号化)と画面ロックを有効にしてください。

## 7. 動作確認用データ

練習用に模擬事件を投入できます(**実事件のデータベースには投入しないこと**)。
別の `DATA_DIR` を指定した試用環境で:

```
.venv\Scripts\python.exe scripts\load_demo.py
```

## 8. テストの実行

```
.venv\Scripts\python.exe -m pytest -q
```

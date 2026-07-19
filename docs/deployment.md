# 本番デプロイ(大学サーバー)

大学サーバーへの初回デプロイ手順。バックアップ/リストアの仕組み自体は
[README.md#backup--restore](../README.md#backup--restore) に検証済み手順があるので、
ここでは**それを「別ホストへの初回移行」に使う手順**と、**本番用`.env`の差分**に絞る。

対象読者はこのリポジトリの運営者(開発者)。学生・教員向けの手順ではない。

## 前提

- 大学サーバー側でDocker / Docker Composeがそのまま使える(確認済み)。
  この`docker-compose.yml`を変更せず持ち込む前提で以下の手順を書いている。
- ローカルの開発DBには既に実データ(学生名簿・ゼミ・教員・募集ラウンド等)が
  入っており、これをそのまま本番の初期データとして使う方針(ゼロから
  CSVインポートし直すのではない)。CSVから入れ直す場合は
  [data/README.md](../data/README.md) の`make import-data`系を使う。

## 1. データ移行(ローカル→本番)

### 1-1. ローカルで最新ダンプを取る

```bash
make backup   # backups/manual_<timestamp>.dump が作られる
```

移行前に、ローカルでのテスト中に紛れ込んだゴミデータが無いか目視確認しておく
(テスト用アカウント、動作確認で作った資料URL等)。`docker compose exec db psql -U postgres -d seminar_platform`
(= `make db-shell`)で直接確認できる。

### 1-2. ダンプファイルをサーバーへ転送

`backups/`は個人情報を含むためgitignore対象(README参照)。**リポジトリ経由ではなく**
`scp`等で直接転送する。

```bash
scp backups/manual_<timestamp>.dump <user>@<university-server>:/path/to/app/backups/
```

### 1-3. サーバー側でリポジトリを配置し、DBだけ先に起動

```bash
git clone <repo-url> && cd muds-hackathon-2026-7-11
cp .env.example .env   # このあと「2. 本番用.envの差分」を反映
docker compose up -d --wait db
cd apps/api && uv run alembic upgrade head   # スキーマを最新化(research_tagsマスタもここで投入される)
```

### 1-4. リストア

```bash
make restore file=backups/manual_<timestamp>.dump
```

`--clean --if-exists`で安全に上書きされる(README「障害復旧手順」と同じ仕組み)。
リストア後、`make db-shell`で`select count(*) from users;`等を叩いて件数がローカルと
一致することを確認する。

## 2. 本番用`.env`の差分

DBの中身には環境依存の値(ドメイン・シークレット)は含まれない。以下は
`.env.example`のうち、**ローカルの値をそのまま使ってはいけない**項目。

| 変数 | ローカルの値 | 本番でやること |
|---|---|---|
| `AUTH_DEV_MODE` | `true` | **必ず`false`**。`true`のままだと`X-Dev-User-Email`ヘッダだけで誰にでもなりすませる(`.env.example`に警告コメントあり)。 |
| `POSTGRES_PASSWORD` | `postgres` | 固有の値に変更。 |
| `AUTH_URL` | `http://localhost:3100` | 本番ドメイン(例: `https://xxx.musashino-u.ac.jp`)。ここが違うとログイン後のリダイレクトが失敗する([docs/authentication.md](authentication.md)参照)。 |
| `WEB_APP_URL` / `NEXT_PUBLIC_API_URL` | localhost各種 | 本番ドメインに合わせる。 |
| `AUTH_GOOGLE_ID` / `AUTH_GOOGLE_SECRET` | チーム共有のテスト用クライアント | Google Cloud Consoleで本番ドメインのリダイレクトURIを登録したOAuthクライアントを別途発行するか、既存クライアントにリダイレクトURIを追加(docs/authentication.md手順1)。 |
| `AUTH_SECRET` / `AUTH_JWT_PRIVATE_KEY` | 各自ローカル生成 | サーバー上で`make setup-auth`を実行し、そのサーバー専有の値を新規生成(使い回さない)。 |
| `AUTH_ALLOWED_EMAIL_DOMAINS` | 空(全許可) | 大学の実ドメインに設定(例: `stu.musashino-u.ac.jp`)。**これを忘れると誰でもログインできる状態になる**。 |
| `INTERNAL_API_SECRET` | 空でも動く(dev) | `openssl rand -hex 32`で生成した値を設定。 |
| `SLACK_BOT_TOKEN` / `SLACK_APP_TOKEN` | (開発用Slackアプリ) | 本番で使う実際のSlackワークスペース/アプリのトークンに差し替え。 |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | 開発用キー | 本番用のAPIキーに差し替え(利用量・課金が本番トラフィックに乗るため)。 |

## 3. 起動と確認

```bash
docker compose up -d --wait
docker compose ps          # 全サービスがhealthy/upであることを確認
curl -f http://localhost:8100/health   # API側のヘルスチェック(README「起動されるサービス」と同じポート)
```

- 実際にブラウザから本番URLでGoogleログイン→マイページ表示まで確認する。
- 学生・教員それぞれのアカウントでログインし、所属ゼミ・担当ゼミの情報が
  正しく出ることを確認する(データ移行漏れがあると空表示になる)。
- 管理者アカウントでログインし、管理者メニューが見えることを確認する。
  移行元のDBで既に`role=admin`になっているユーザーのメールアドレスで
  ログインすれば、本番側で改めて昇格作業をする必要はない
  (`_provision_user`がgoogle_idをメールアドレスで紐付けるため)。
- `docker compose logs backup`で、その日のうちに1回目のバックアップが走ることを確認する。

## 4. 未対応・今後の課題

- **バックアップのオフサイト保管**: `./backups/`はサーバーのローカルディスクに
  溜まるだけで、サーバー自体を失うと一緒に消える(README既知の課題、本ドキュメントでも未対応)。
  別ストレージへの定期コピーは別issueで検討する。
- **CI/CDでの自動デプロイ**: 現状は手動デプロイのみ。GitHub Actionsからのデプロイ自動化は別issue。
- **サーバー固有の設定**: OS・リバースプロキシ(nginx等)・TLS証明書の取得方法は
  大学サーバーの詳細が分かり次第このドキュメントに追記する。

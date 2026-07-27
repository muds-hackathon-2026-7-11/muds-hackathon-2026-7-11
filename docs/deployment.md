# 本番デプロイ(大学サーバー)

sparkサーバで稼働している本番環境の運用手順。ローカル開発の起動手順は
[README.md](../README.md) を参照。

対象読者はこのリポジトリの運営者(開発者)。学生・教員向けの手順ではない。

## 前提

- 本番は `docker-compose.prod.yml` + `.env.production` の組で動く。ローカル開発用の
  `docker-compose.yml` とは**別物**として扱う(マージして使う想定ではない)。
- そのため `Makefile` の各ターゲット(`make migrate` / `make backup` 等)は
  すべてローカル用。本番では使わず、下記のコマンドを直接叩く。
- コマンドが長いので、以下ではこのエイリアスを使う。

```bash
alias dcp='docker compose -f docker-compose.prod.yml --env-file .env.production'
```

## 変更の種類ごとに必要な作業

本番のコンテナはソースを bind mount しておらず、イメージに焼き込んでいる
(dev の `docker-compose.yml` だけが bind mount + `--reload`)。したがって
**コードを変えたら必ずイメージの再ビルドが要る**。

| 変更した内容 | 必要な作業 |
| --- | --- |
| `apps/api` のコードのみ | `build api` → `up -d api` |
| `apps/api` + **マイグレーション追加** | `build api` → **`alembic upgrade head`** → `up -d api` |
| `apps/web` のコードのみ | `build web` → `up -d web` |
| `NEXT_PUBLIC_*` の値 | `build web`(next build 時に焼き込まれるため再ビルド必須) |
| その他の環境変数 | `.env.production` を編集 → 対象サービスを `up -d` |

マイグレーションが増えたかどうかは、`apps/api/alembic/versions/` に新しい
ファイルが追加されたかで判断する。

```bash
git diff --stat <前回デプロイしたコミット>..HEAD -- apps/api/alembic/versions/
```

## 更新デプロイ(稼働中の本番に変更を反映する)

### 0. バックアップを取る

スキーマが変わる場合は必須。`POSTGRES_USER` / `POSTGRES_DB` を `.env.production`
で既定から変えている場合は、その値に合わせること。

```bash
mkdir -p backups
dcp exec -T db pg_dump -U postgres -d seminar_platform --format=custom \
  > backups/manual_$(date +%Y%m%d_%H%M%S).dump
```

### 1. コードを取得する

```bash
git pull origin main
```

### 2. イメージを再ビルドする

```bash
dcp build api          # apps/web も変えたなら `dcp build api web`
```

この時点ではまだ旧イメージのコンテナが動き続けている。

### 3. マイグレーションを先に適用する(ある場合)

**順序を間違えるとアプリが落ちる。** api コンテナは起動時に alembic を実行しない
(`CMD` は uvicorn のみで、lifespan も締切リマインダーのスケジューラを起動する
だけ)。新しいコードがまだ存在しないテーブル/カラムを参照した状態で起動すると、
該当機能がすべて500になる。

使い捨てコンテナで**スキーマだけ先に進める**。サービス本体は旧イメージのまま
動き続けるので、この間もアプリは止まらない(旧コードは新しいテーブルを見ない)。

```bash
dcp run --rm api uv run alembic upgrade head
```

### 4. 新しいイメージに入れ替える

```bash
dcp up -d api          # web も再ビルドしたなら `dcp up -d api web`
dcp ps                 # 対象サービスが running になっていることを確認
```

### 5. 動作確認

api はホストにポートを公開していない(nginxが転送するのは web の公開ポートのみ)
ため、ホストから直接 `curl` で叩くことはできない。ログとブラウザで確認する。

```bash
dcp logs --tail=50 api     # 起動時にトレースバックが出ていないこと
dcp logs --tail=50 web
```

- 公開URLをブラウザで開き、Googleログイン→マイページ表示までを確認する。
- 今回変更した機能を実際に1回動かす。

## ロールバック

**手順3と逆の順序で戻す。** 新しいコードが動いている状態でテーブルを落とすと
500になるため、必ずアプリを先に戻すこと。

```bash
# 1. 先にアプリを戻す
git checkout <戻したいコミット>
dcp build api
dcp up -d api

# 2. そのあとスキーマを戻す(マイグレーションを適用していた場合のみ)
dcp run --rm api uv run alembic downgrade -1
```

データ自体が壊れた場合は手順0で取ったダンプから戻す
([README.md の障害復旧手順](../README.md)を参照。記載の `docker compose` は
`dcp` に読み替えること)。

## 環境変数を追加・変更するとき

`docker-compose.prod.yml` の api / web は `env_file: .env.production` を丸ごと
読んでいるため、**compose ファイルの修正は不要**。追加した変数もそのまま渡る。

```bash
vi .env.production
dcp up -d api
```

例外は `NEXT_PUBLIC_*` で、これは next build 時にバンドルへ焼き込まれるため
build args 経由で渡している。値を変えたら `dcp build web` からやり直すこと。

## 初回移行(初めてサーバーへ載せるとき)

ローカルの開発DBを大学サーバーへ移す初回手順(pg_dump/pg_restore による移行、
本番用 `.env` で差し替えが必要な項目のチェックリスト)は #186 で整備中。
このドキュメントに追記する形で置く。

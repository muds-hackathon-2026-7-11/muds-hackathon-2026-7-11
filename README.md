# ゼミ選択・配属支援プラットフォーム

学生が研究内容や将来の興味に合ったゼミを見つけられるよう支援し、教員側の応募管理・選考業務も効率化するWebシステム。

詳細な要件・DB設計・画面設計は [docs/requirements.md](docs/requirements.md) を参照。

## 技術スタック

- **Frontend**: Next.js (TypeScript, App Router, Tailwind CSS)
- **Backend**: FastAPI (Python) + SQLAlchemy(async) + Alembic
- **DB**: PostgreSQL + pgvector
- **認証**: Google OAuth
- **AI対話(相談アシスタント・志望理由作成支援)**: Claude API
- **マッチング診断**: sentence-transformers + pgvector
- **Slack連携**: slack-bolt
- **モノレポ管理**: pnpm workspace + Turborepo(JS側) / uv(Python側)
- **Lint/Format**: Biome(web) / ruff・mypy(api)

## リポジトリ構成

```
/
├── apps/
│   ├── web/   # Frontend (Next.js / TypeScript)
│   └── api/   # Backend (FastAPI / Python)
├── docs/      # 要件定義・設計ドキュメント
├── docker-compose.yml
└── Makefile
```

## 事前準備

| ツール | バージョン目安 |
|---|---|
| Node.js | 22+ |
| pnpm | 9+ |
| Python | 3.12+ |
| uv | 最新 |
| Docker / Docker Compose | 最新 |

## クイックスタート

```bash
cp .env.example .env
make install   # pnpm install + uv sync
make dev       # docker compose up --build (db / api / web)
```

起動後のURL:

| サービス | URL |
|---|---|
| Web | http://localhost:3100 |
| API | http://localhost:8100 (ヘルスチェック: `/health`) |
| DB (Postgres) | localhost:5442 |

## よく使うコマンド

```bash
make lint       # web(Biome/ESLint) + api(ruff)
make typecheck  # web(tsc) + api(mypy)
make test       # web + api のテスト
make format     # web(Biome) + api(ruff format)
make db-shell   # devのDBにpsqlで接続
make down       # コンテナ停止
make clean      # コンテナ・volume・ビルド成果物を削除
```

`make help` で全コマンド一覧を表示できます。
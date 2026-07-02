#!/usr/bin/env bash
# バックアップ→データ破壊→リストアが実際に機能することを検証するスクリプト。
# ローカルでは `make backup-restore-test`、CIでも同じスクリプトを実行する。
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> starting db"
docker compose up -d --wait db

echo "==> applying migrations"
(cd apps/api && uv run alembic upgrade head)

MARKER="backup-test-$(date +%s)"
echo "==> inserting marker seminar: $MARKER"
docker compose exec -T db psql -U postgres -d seminar_platform -c \
  "INSERT INTO seminars (id, name) VALUES (gen_random_uuid(), '$MARKER');"

echo "==> taking backup"
mkdir -p backups
docker compose exec -T db pg_dump -U postgres -d seminar_platform --format=custom > backups/ci_test.dump

echo "==> destroying data"
docker compose exec -T db psql -U postgres -d seminar_platform -c "TRUNCATE seminars CASCADE;"

echo "==> restoring"
docker compose exec -T db pg_restore -U postgres -d seminar_platform --clean --if-exists < backups/ci_test.dump

echo "==> verifying marker is back"
COUNT=$(docker compose exec -T db psql -U postgres -d seminar_platform -tAc \
  "SELECT COUNT(*) FROM seminars WHERE name = '$MARKER';")

rm -f backups/ci_test.dump

if [ "$COUNT" != "1" ]; then
  echo "FAILED: marker seminar not found after restore (count=$COUNT)"
  exit 1
fi

echo "OK: backup/restore verified"

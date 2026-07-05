#!/usr/bin/env bash
#
# ローカル認証キーを .env に用意する(べき等)。
# - .env が無ければ .env.example から作成
# - AUTH_SECRET / AUTH_JWT_PRIVATE_KEY / AUTH_URL が空のときだけ生成して設定
#   (既に値がある場合は上書きしない)
# - AUTH_GOOGLE_ID / AUTH_GOOGLE_SECRET はチームで共有された値を各自が手で設定する
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "created .env from .env.example"
fi

# セッション暗号化キー
SECRET="$(openssl rand -base64 32)"
# RS256秘密鍵JWK(単一行JSON)。Node組み込みcryptoのみで生成するため追加依存は不要。
JWK="$(node -e "const{generateKeyPairSync}=require('node:crypto');const{privateKey}=generateKeyPairSync('rsa',{modulusLength:2048});process.stdout.write(JSON.stringify(privateKey.export({format:'jwk'})));")"

# 空のkeyだけ生成値を書き込む(位置は保持、行が無ければ追記)。値はenv経由で安全に渡す。
AUTH_SECRET_VALUE="$SECRET" AUTH_JWT_PRIVATE_KEY_VALUE="'$JWK'" python3 - <<'PY'
import os
import re

path = ".env"
with open(path) as f:
    lines = f.readlines()


def set_if_empty(key: str, value: str) -> None:
    for i, ln in enumerate(lines):
        m = re.match(rf"^{re.escape(key)}=(.*)$", ln.rstrip("\n"))
        if m:
            if m.group(1).strip():
                print(f"  {key}: 設定済み（スキップ）")
                return
            lines[i] = f"{key}={value}\n"
            print(f"  {key}: 生成して設定")
            return
    lines.append(f"{key}={value}\n")
    print(f"  {key}: 生成して追記")


set_if_empty("AUTH_SECRET", os.environ["AUTH_SECRET_VALUE"])
set_if_empty("AUTH_JWT_PRIVATE_KEY", os.environ["AUTH_JWT_PRIVATE_KEY_VALUE"])
set_if_empty("AUTH_URL", "http://localhost:3100")

with open(path, "w") as f:
    f.writelines(lines)
PY

echo ""
echo "✅ ローカル認証キー(AUTH_SECRET / AUTH_JWT_PRIVATE_KEY / AUTH_URL)を用意しました。"
echo "   次に、チームで共有された AUTH_GOOGLE_ID / AUTH_GOOGLE_SECRET を .env に設定してください。"
echo "   (Googleログイン無しで進めたい場合は AUTH_DEV_MODE=true のままでOK。バックエンドはダミー認証で動きます)"

# 認証（Google OAuth / JWT）

## 全体像

```
[Next.js / Auth.js]  Googleログイン
   └ jwtコールバックで RS256 アクセストークンを発行(jose)
   └ GET /api/auth/jwks で公開鍵(JWKS)を配信
        │  Authorization: Bearer <RS256 JWT>
        ▼
[FastAPI]  JWKS(JWT_JWKS_URL)で署名/iss/aud/exp を検証
   └ claims(sub/email/name) から users を find-or-create(JITプロビジョニング)
   └ get_current_user で各エンドポイントに認証ユーザーを注入
```

- 発行側（フロント）: `apps/web`（Issue #6）
- 検証側（バックエンド）: `apps/api`（Issue #23。`auth.py` / `get_current_user` / `GET /me`）

## 2つの動作モード

### 開発モード（既定 / 実Google不要）
`AUTH_DEV_MODE=true`（`.env`）のとき、FastAPI は JWT 検証をスキップし、
`X-Dev-User-Email` / `X-Dev-User-Role` ヘッダのユーザーとして認証する。
ローカル・CI 用。フロントの Google ログイン無しで保護APIを叩ける。

```bash
curl -H "X-Dev-User-Email: taro@example.com" -H "X-Dev-User-Role: teacher" \
  http://localhost:8100/me
```

### 実Googleモード
`AUTH_DEV_MODE=false` にし、実際の Google ログインで発行された RS256 トークンを
JWKS 経由で検証する。

## 実Googleモードの有効化手順

1. **Google Cloud Console で OAuth クライアントID を発行**
   - 「APIとサービス」→「認証情報」→「OAuth クライアント ID」→ ウェブアプリケーション
   - 承認済みリダイレクト URI:
     - `http://localhost:3100/api/auth/callback/google`（Docker / `make dev`）
     - `http://localhost:3000/api/auth/callback/google`（`pnpm dev` 直叩き）
   - OAuth 同意画面の「テストユーザー」に自分の Google アカウントを追加
   - 得られた ID / シークレットを `.env` の `AUTH_GOOGLE_ID` / `AUTH_GOOGLE_SECRET` へ

2. **セッションキーと署名鍵を生成**
   ```bash
   openssl rand -base64 32              # → AUTH_SECRET
   cd apps/web && node --input-type=module -e "import{generateKeyPair,exportJWK}from'jose';const{privateKey}=await generateKeyPair('RS256',{extractable:true});process.stdout.write(JSON.stringify(await exportJWK(privateKey)))"
   # → AUTH_JWT_PRIVATE_KEY（単一行JSON）
   ```

3. **`.env` を設定**（`web` と `api` で issuer/audience を一致させる）
   ```
   # web
   AUTH_GOOGLE_ID=...
   AUTH_GOOGLE_SECRET=...
   AUTH_SECRET=...
   AUTH_JWT_ISSUER=seminar-platform-web
   AUTH_JWT_AUDIENCE=seminar-platform-api
   AUTH_JWT_PRIVATE_KEY='{"kty":"RSA",...}'
   # api（検証側）
   AUTH_DEV_MODE=false
   JWT_JWKS_URL=http://web:3000/api/auth/jwks   # Docker。ローカルは http://localhost:3000/api/auth/jwks
   JWT_ISSUER=seminar-platform-web
   JWT_AUDIENCE=seminar-platform-api
   ```

4. **起動して確認**: `make dev` → `http://localhost:3100` で「Googleでログイン」。

## メモ
- ブラウザから FastAPI を直接叩く場合は API 側の CORS 対応が別途必要（別Issue）。
- 大学ドメイン限定にするには `AUTH_ALLOWED_EMAIL_DOMAINS`（カンマ区切り）を設定。空なら全許可。
- アクセストークンの有効期限は 1 時間。期限が近づくとセッション更新時に自動で再発行される。

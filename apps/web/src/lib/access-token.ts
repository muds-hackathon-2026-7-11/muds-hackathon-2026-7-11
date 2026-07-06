import { type JWK, SignJWT, importJWK } from "jose";

// FastAPI(#23)がJWKS経由で検証する、API向けRS256アクセストークンの発行まわり。
const ALG = "RS256";
const KID = "seminar-web-key";
const ACCESS_TOKEN_TTL_SECONDS = 60 * 60; // 1時間

// issuer/audience はバックエンドの JWT_ISSUER / JWT_AUDIENCE と一致させること。
export const ACCESS_TOKEN_ISSUER =
  process.env.AUTH_JWT_ISSUER ?? "seminar-platform-web";
export const ACCESS_TOKEN_AUDIENCE =
  process.env.AUTH_JWT_AUDIENCE ?? "seminar-platform-api";

function getPrivateJwk(): JWK {
  const raw = process.env.AUTH_JWT_PRIVATE_KEY;
  if (!raw) {
    throw new Error(
      "AUTH_JWT_PRIVATE_KEY が未設定です。RS256の秘密鍵JWK(単一行JSON)を設定してください。",
    );
  }
  return JSON.parse(raw) as JWK;
}

export interface AccessTokenClaims {
  sub: string;
  email?: string | null;
  name?: string | null;
}

/** API向けのRS256アクセストークンを発行する。 */
export async function mintAccessToken(
  claims: AccessTokenClaims,
): Promise<{ token: string; expiresAt: number }> {
  const key = await importJWK(getPrivateJwk(), ALG);
  const now = Math.floor(Date.now() / 1000);
  const expiresAt = now + ACCESS_TOKEN_TTL_SECONDS;
  const token = await new SignJWT({
    email: claims.email ?? undefined,
    name: claims.name ?? undefined,
  })
    .setProtectedHeader({ alg: ALG, kid: KID })
    .setSubject(claims.sub)
    .setIssuer(ACCESS_TOKEN_ISSUER)
    .setAudience(ACCESS_TOKEN_AUDIENCE)
    .setIssuedAt(now)
    .setExpirationTime(expiresAt)
    .sign(key);
  return { token, expiresAt };
}

/** JWKSエンドポイントで公開する、公開鍵(n/e)のみのJWKセットを返す。 */
export function getPublicJwks(): { keys: JWK[] } {
  const { kty, n, e } = getPrivateJwk();
  return { keys: [{ kty, n, e, kid: KID, alg: ALG, use: "sig" }] };
}

// @vitest-environment node
import { generateKeyPairSync } from "node:crypto";
import { createLocalJWKSet, jwtVerify } from "jose";
import { beforeAll, describe, expect, it } from "vitest";
import {
  ACCESS_TOKEN_AUDIENCE,
  ACCESS_TOKEN_ISSUER,
  getPublicJwks,
  mintAccessToken,
} from "@/lib/access-token";

beforeAll(() => {
  const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  process.env.AUTH_JWT_PRIVATE_KEY = JSON.stringify(
    privateKey.export({ format: "jwk" }),
  );
});

describe("mintAccessToken / getPublicJwks", () => {
  it("発行したトークンがJWKS(公開鍵)で検証でき、claimsが正しい", async () => {
    const { token, expiresAt } = await mintAccessToken({
      sub: "google-123",
      email: "taro@stu.musashino-u.ac.jp",
      name: "Taro",
    });

    const jwks = createLocalJWKSet(getPublicJwks());
    const { payload } = await jwtVerify(token, jwks, {
      issuer: ACCESS_TOKEN_ISSUER,
      audience: ACCESS_TOKEN_AUDIENCE,
    });

    expect(payload.sub).toBe("google-123");
    expect(payload.email).toBe("taro@stu.musashino-u.ac.jp");
    expect(payload.name).toBe("Taro");
    expect(payload.exp).toBe(expiresAt);
  });

  it("JWKSは公開鍵(n/e)のみで、秘密パラメータを含まない", () => {
    const jwk = getPublicJwks().keys[0] as Record<string, unknown>;

    expect(jwk.kty).toBe("RSA");
    expect(jwk.n).toBeDefined();
    expect(jwk.e).toBeDefined();
    expect(jwk.kid).toBeDefined();
    for (const secret of ["d", "p", "q", "dp", "dq", "qi"]) {
      expect(jwk[secret]).toBeUndefined();
    }
  });

  it("AUTH_JWT_PRIVATE_KEYが未設定なら例外", async () => {
    const saved = process.env.AUTH_JWT_PRIVATE_KEY;
    delete process.env.AUTH_JWT_PRIVATE_KEY;
    try {
      await expect(mintAccessToken({ sub: "x" })).rejects.toThrow();
    } finally {
      process.env.AUTH_JWT_PRIVATE_KEY = saved;
    }
  });
});

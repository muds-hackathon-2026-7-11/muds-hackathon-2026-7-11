import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import { mintAccessToken } from "@/lib/access-token";

// アクセストークンの有効期限が残りこの秒数を切ったら再発行する。
const ACCESS_TOKEN_REFRESH_MARGIN_SECONDS = 5 * 60;

// 大学ドメイン制限(任意): AUTH_ALLOWED_EMAIL_DOMAINS にカンマ区切りで指定すると
// そのドメインのメールのみログインを許可する。未設定なら全許可(開発向け)。
const allowedDomains = (process.env.AUTH_ALLOWED_EMAIL_DOMAINS ?? "")
  .split(",")
  .map((domain) => domain.trim().toLowerCase())
  .filter(Boolean);

export const { handlers, signIn, signOut, auth } = NextAuth({
  // localhost / Docker などVercel以外で動かすため、リクエストのホストを信頼する。
  trustHost: true,
  providers: [Google],
  callbacks: {
    async signIn({ profile }) {
      if (allowedDomains.length === 0) {
        return true;
      }
      const email = profile?.email?.toLowerCase() ?? "";
      const domain = email.split("@")[1] ?? "";
      return allowedDomains.includes(domain);
    },
    async jwt({ token, profile }) {
      // 初回サインイン時にGoogleのsub(=google_id)をトークンへ保存する。
      // email/name はNextAuthがprofileから自動でtokenに載せる。
      if (profile?.sub) {
        token.googleId = profile.sub;
      }

      // API向けRS256アクセストークンを、無い/期限切れ間近なら発行し直す。
      const now = Math.floor(Date.now() / 1000);
      const needsRefresh =
        !token.accessToken ||
        !token.accessTokenExpires ||
        token.accessTokenExpires - now < ACCESS_TOKEN_REFRESH_MARGIN_SECONDS;
      if (token.googleId && needsRefresh) {
        const { token: accessToken, expiresAt } = await mintAccessToken({
          sub: token.googleId,
          email: token.email,
          name: token.name,
        });
        token.accessToken = accessToken;
        token.accessTokenExpires = expiresAt;
      }
      return token;
    },
    async session({ session, token }) {
      if (token.googleId) {
        session.googleId = token.googleId;
      }
      if (token.accessToken) {
        session.accessToken = token.accessToken;
      }
      return session;
    },
  },
});

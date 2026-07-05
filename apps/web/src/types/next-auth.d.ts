// next-auth の型拡張。Session / JWT に独自フィールドを足す。
import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface Session {
    googleId?: string;
    // P2で発行する、FastAPI向けのRS256アクセストークン。
    accessToken?: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    googleId?: string;
    accessToken?: string;
    // アクセストークンの有効期限(epoch秒)。近づいたら再発行する。
    accessTokenExpires?: number;
  }
}

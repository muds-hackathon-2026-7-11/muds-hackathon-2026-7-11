// ログイン許可メールドメインの判定。AUTH_ALLOWED_EMAIL_DOMAINS を扱う。

/** カンマ区切りの環境変数値を、正規化したドメイン配列にする。 */
export function parseAllowedDomains(raw: string | undefined): string[] {
  return (raw ?? "")
    .split(",")
    .map((domain) => domain.trim().toLowerCase())
    .filter(Boolean);
}

/** allowedDomains が空なら全許可。そうでなければメールのドメインが含まれるか。 */
export function isEmailAllowed(
  email: string | null | undefined,
  allowedDomains: string[],
): boolean {
  if (allowedDomains.length === 0) {
    return true;
  }
  const domain = (email ?? "").toLowerCase().split("@")[1] ?? "";
  return allowedDomains.includes(domain);
}

import { isEmailAllowed } from "./allowed-domains";
import { isEmailRegistered } from "./is-email-registered";

/**
 * ログインを許可するか判定する(auth.tsのsignInコールバックから呼ぶ)。
 * ドメイン制限とDB事前登録の両方を満たす必要がある。
 */
export async function shouldAllowSignIn(
  email: string | null | undefined,
  allowedDomains: string[],
): Promise<boolean> {
  if (!isEmailAllowed(email, allowedDomains)) {
    return false;
  }
  return await isEmailRegistered(email);
}

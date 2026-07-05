import { serverApiFetch } from "./api-server";

/** メールアドレスがusersに事前登録済みか(DB未登録者のログインを弾くため)。 */
export async function isEmailRegistered(
  email: string | null | undefined,
): Promise<boolean> {
  if (!email) {
    return false;
  }

  try {
    const res = await serverApiFetch(
      `/users/exists?email=${encodeURIComponent(email)}`,
      null,
    );
    if (!res.ok) {
      return false;
    }
    const data = (await res.json()) as { exists: boolean };
    return data.exists;
  } catch {
    return false;
  }
}

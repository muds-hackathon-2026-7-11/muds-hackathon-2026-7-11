const DEFAULT_FALLBACK = "エラーが発生しました。";

function isValidationErrorItem(value: unknown): value is { msg: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    "msg" in value &&
    typeof (value as { msg: unknown }).msg === "string"
  );
}

// PydanticのValueError由来のmsgには"Value error, "接頭辞が付くため、
// 画面表示前に取り除く。
function cleanValidationMessage(msg: string): string {
  return msg.replace(/^Value error,\s*/, "");
}

/**
 * FastAPIのエラーレスポンス(detail)を、画面表示用の1つの文字列にする。
 *
 * detailは2種類の形をとる:
 * - HTTPException(detail="...")由来: 単一のstring
 * - Pydanticのバリデーションエラー(422)由来: {type, loc, msg, input, ctx}の配列
 * 後者をstring決め打ちで扱うと、配列(オブジェクト)がそのままReactの子要素に
 * 渡り "Objects are not valid as a React child" で画面が落ちるため、
 * どちらの形でも安全に文字列化する。
 *
 * specialCases: 特定のdetail文字列を別の表示用メッセージに読み替えたい場合に使う
 * (例: 締切後を示す固定detail文字列を、画面用の丁寧な文言に変換する)。
 */
export async function extractErrorDetail(
  res: Response,
  specialCases?: Record<string, string>,
): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    const detail = body.detail;

    if (typeof detail === "string") {
      return specialCases?.[detail] ?? detail;
    }

    if (Array.isArray(detail)) {
      const messages = detail
        .filter(isValidationErrorItem)
        .map((item) => cleanValidationMessage(item.msg));
      if (messages.length > 0) {
        return messages.join("\n");
      }
    }

    return DEFAULT_FALLBACK;
  } catch {
    return DEFAULT_FALLBACK;
  }
}

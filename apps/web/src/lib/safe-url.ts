// javascript: 等のスキームは、そのまま <a href> に使うとクリックで実行されて
// しまうため、資料URL等ユーザー入力由来のURLをリンクとして描画する前に
// 必ずこれで検証する(#172)。バックエンドのSeminarMaterialCreateでも
// http(s)のみを許可しているが、既存データや将来の別経路も守るための
// 表示側の防御。
export function isSafeHttpUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

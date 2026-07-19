import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { getSessionRole } from "@/lib/session-role";

export default async function UnsubmittedLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }
  const role = await getSessionRole();
  // 未提出者一覧(#182)は担当ゼミに関係なく全学生分を見せるため、教員・管理者
  // どちらもOK。/teacher配下のlayoutは他の教員専用ページ(応募者一覧・ゼミ設定)
  // まで巻き込んでしまうため、このページ専用に独立させている。
  if (role !== "teacher" && role !== "admin") {
    redirect("/");
  }

  return <>{children}</>;
}

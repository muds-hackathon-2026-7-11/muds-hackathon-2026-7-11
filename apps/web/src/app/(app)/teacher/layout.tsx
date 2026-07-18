import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { getSessionRole } from "@/lib/session-role";

export default async function TeacherLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }
  const role = await getSessionRole();
  // 未提出者一覧(/teacher/unsubmitted, #182)はadminからも見られるようにしているため、
  // teacher配下全体をadminにも開放する。他ページはバックエンド側がteacher限定のままなので
  // adminが叩くと403になるだけで実害はない。
  if (role !== "teacher" && role !== "admin") {
    redirect("/");
  }

  return <>{children}</>;
}

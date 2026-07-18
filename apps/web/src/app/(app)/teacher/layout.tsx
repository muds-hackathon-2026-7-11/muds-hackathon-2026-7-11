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
  if (role !== "teacher") {
    redirect("/");
  }

  return <>{children}</>;
}

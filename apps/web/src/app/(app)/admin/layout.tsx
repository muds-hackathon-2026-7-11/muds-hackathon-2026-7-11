import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { getSessionRole } from "@/lib/session-role";

export default async function AdminLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }
  const role = await getSessionRole();
  if (role !== "admin") {
    redirect("/");
  }

  return <>{children}</>;
}

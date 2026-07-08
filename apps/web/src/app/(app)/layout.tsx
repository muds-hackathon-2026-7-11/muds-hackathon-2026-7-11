import { MenuBar } from "@/components/menu-bar";
import { getSessionRole } from "@/lib/session-role";

export default async function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const role = await getSessionRole();

  return (
    <>
      <MenuBar isAdmin={role === "admin"} />
      {children}
    </>
  );
}

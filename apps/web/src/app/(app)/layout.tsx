import { MenuBar } from "@/components/menu-bar";

export default function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <>
      <MenuBar />
      {children}
    </>
  );
}

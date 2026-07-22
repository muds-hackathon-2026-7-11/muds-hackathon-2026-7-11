import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { LoginButton } from "@/components/login-button";

export default async function LoginPage() {
  const session = await auth();
  if (session) {
    redirect("/");
  }

  return (
    <main className="page-canvas relative flex flex-1 items-center justify-center overflow-hidden px-4">
      <LoginButton />
    </main>
  );
}

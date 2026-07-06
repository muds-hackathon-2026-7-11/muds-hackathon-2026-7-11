import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { LoginButton } from "@/components/login-button";

export default async function LoginPage() {
  const session = await auth();
  if (session) {
    redirect("/");
  }

  return (
    <main className="flex flex-1 items-center justify-center px-4">
      <LoginButton />
    </main>
  );
}

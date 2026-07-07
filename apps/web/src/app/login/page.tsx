import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { LoginButton } from "@/components/login-button";

export default async function LoginPage() {
  const session = await auth();
  if (session) {
    redirect("/");
  }

  return (
    <main className="relative flex flex-1 items-center justify-center overflow-hidden bg-[#e6e6e6] px-4">
      <LoginButton />
    </main>
  );
}

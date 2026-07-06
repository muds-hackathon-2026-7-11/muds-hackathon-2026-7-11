import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { LoginButton } from "@/components/login-button";

export default async function LoginPage() {
  const session = await auth();
  if (session) {
    redirect("/");
  }

  return (
    <main className="relative flex flex-1 items-center justify-center overflow-hidden px-4">
      {/* 画面外周のビネット。縁だけ黒くぼかして中央を引き立てる(白黒基調)。 */}
      <div aria-hidden className="vignette pointer-events-none absolute inset-0" />

      <LoginButton />
    </main>
  );
}

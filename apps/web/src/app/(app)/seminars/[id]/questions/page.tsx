import { redirect } from "next/navigation";
import { auth } from "@/auth";

export default async function SeminarQuestionsPage() {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }

  return (
    <main className="flex flex-1 items-center justify-center px-4">
      <p className="text-foreground/60">FAQは準備中です。</p>
    </main>
  );
}

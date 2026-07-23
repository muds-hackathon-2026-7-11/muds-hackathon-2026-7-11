import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { AiSeminarChatView } from "@/components/ai-seminar-chat-view";

export default async function ChatPage() {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }

  return (
    <main className="page-canvas relative flex flex-1 flex-col">
      <div className="relative mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-6">
        <h1 className="border-l-4 border-[#add8e6] pl-3 text-2xl font-bold text-zinc-800">
          AIゼミ相談
        </h1>
        <AiSeminarChatView />
      </div>
    </main>
  );
}

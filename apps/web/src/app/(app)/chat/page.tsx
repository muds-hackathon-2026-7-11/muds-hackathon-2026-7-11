import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { AiSeminarChatView } from "@/components/ai-seminar-chat-view";

export default async function ChatPage() {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }

  return (
    <main className="relative flex flex-1 flex-col bg-[#e6e6e6]">
      <div className="relative mx-auto flex w-full max-w-3xl flex-1 flex-col p-4 sm:p-6">
        <AiSeminarChatView />
      </div>
    </main>
  );
}

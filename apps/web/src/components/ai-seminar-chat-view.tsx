"use client";

// 動画撮影用の仮画面(#106)。AIチャット自体はまだ実装しない。
type ChatMessage = {
  role: "bot" | "user";
  content: string;
};

const SAMPLE_MESSAGES: ChatMessage[] = [
  {
    role: "bot",
    content:
      "こんにちは!やってみたいことや興味のある分野を教えてください。あなたに合いそうなゼミをご紹介します。",
  },
  {
    role: "user",
    content: "機械学習を使ったデータ分析をやってみたいです。",
  },
  {
    role: "bot",
    content:
      "それなら「中村ゼミ」がおすすめです。機械学習・深層学習を専門にしていて、興味と親和性が高そうです。",
  },
];

export function AiSeminarChatView() {
  return (
    <section className="flex h-[75vh] flex-col rounded-2xl border-2 border-[#add8e6] bg-white p-6 shadow-sm shadow-[#add8e6]/30">
      <p className="font-semibold text-zinc-800">AIゼミ相談</p>

      <div className="mt-4 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto rounded-lg border border-[#add8e6]/60 bg-[#add8e6]/[.06] p-3">
        {SAMPLE_MESSAGES.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={
              message.role === "user"
                ? "flex justify-end"
                : "flex justify-start"
            }
          >
            <p
              className={[
                "max-w-[85%] rounded-2xl px-3 py-2 text-sm",
                message.role === "user"
                  ? "bg-[#add8e6] text-sky-950"
                  : "bg-white text-zinc-700 shadow-sm",
              ].join(" ")}
            >
              {message.content}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-3 flex gap-2">
        <input
          type="text"
          disabled
          placeholder="やりたいことを入力(準備中)"
          className="flex-1 rounded-full border border-[#add8e6]/60 bg-[#e6e6e6]/40 px-4 py-2 text-sm text-zinc-400"
        />
        <button
          type="button"
          disabled
          title="準備中"
          className="cursor-not-allowed rounded-full bg-[#add8e6]/40 px-4 py-2 text-sm font-semibold text-white"
        >
          送信
        </button>
      </div>
    </section>
  );
}

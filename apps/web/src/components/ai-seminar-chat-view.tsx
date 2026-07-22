"use client";

import { useSession } from "next-auth/react";
import {
  type KeyboardEvent as ReactKeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import { apiFetch } from "@/lib/api-client";

type Recommendation = { seminar_name: string; reason: string };

type ChatMessage = {
  id: number;
  speaker: "user" | "assistant";
  content: string;
  // assistant発話に付随するゼミ推薦(あれば)。
  recommendations?: Recommendation[];
  // エラー通知の吹き出し。会話履歴(history)には含めない。
  isError?: boolean;
};

// 会話の先頭に表示する固定のあいさつ。APIへは送らない(表示専用)。
const GREETING =
  "こんにちは!やってみたいことや興味のある分野を教えてください。あなたに合いそうなゼミをご紹介します。";
// 通信・応答に失敗したときにbotとして表示する文言。
const ERROR_REPLY =
  "うまく応答できませんでした。時間をおいて再度お試しください。";
// /consult の history は最大20件。超える分は直近だけ送る。
const MAX_HISTORY = 20;
// 入力欄の最大の高さ(px)。これを超えたら内部スクロール。
const INPUT_MAX_HEIGHT = 160;
// 送信できる1メッセージの最大文字数(バックエンド ConsultIn の上限に合わせる)。
const MESSAGE_MAX_LENGTH = 4000;

export function AiSeminarChatView() {
  const { data: session } = useSession();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const nextIdRef = useRef(0);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 新しいメッセージや送信状態の変化を契機に最下部へスクロールする(表示のみ)。
  // biome-ignore lint/correctness/useExhaustiveDependencies: スクロールのトリガーとして依存させている
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  // 入力量に合わせて入力欄の高さを自動調整する。
  // biome-ignore lint/correctness/useExhaustiveDependencies: 入力変化を契機に高さを再計算するため依存させている
  useEffect(() => {
    const el = inputRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, INPUT_MAX_HEIGHT)}px`;
    }
  }, [input]);

  async function handleSend(): Promise<void> {
    const text = input.trim();
    if (text === "" || isSending) {
      return;
    }
    // このメッセージより前のやりとりを履歴として送る(マルチターン)。
    // エラー通知の吹き出しは文脈に含めない。
    const history = messages
      .filter((m) => !m.isError)
      .slice(-MAX_HISTORY)
      .map((m) => ({ role: m.speaker, content: m.content }));

    setMessages((prev) => [
      ...prev,
      { id: nextIdRef.current++, speaker: "user", content: text },
    ]);
    setInput("");
    setIsSending(true);
    try {
      const res = await apiFetch("/consult", session, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history }),
      });
      if (!res.ok) {
        throw new Error(`consult failed: ${res.status}`);
      }
      const data = (await res.json()) as {
        reply: string;
        recommendations: Recommendation[];
      };
      setMessages((prev) => [
        ...prev,
        {
          id: nextIdRef.current++,
          speaker: "assistant",
          content: data.reply,
          recommendations: data.recommendations,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: nextIdRef.current++,
          speaker: "assistant",
          content: ERROR_REPLY,
          isError: true,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(e: ReactKeyboardEvent<HTMLTextAreaElement>): void {
    // Enterで送信、Shift+Enterで改行。IME変換中のEnterでは送信しない。
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      void handleSend();
    }
  }

  function handleReset(): void {
    setMessages([]);
    setInput("");
  }

  const canSend = input.trim() !== "" && !isSending;

  return (
    <section className="flex h-[75vh] flex-col rounded-2xl border border-line bg-white p-6 shadow-sm shadow-[#add8e6]/30">
      <div
        aria-live="polite"
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto rounded-lg border border-[#add8e6]/60 bg-[#add8e6]/[.06] p-3"
      >
        <ChatBubble speaker="assistant" content={GREETING} />
        {messages.map((message) => (
          <div key={message.id} className="flex flex-col gap-2">
            <ChatBubble speaker={message.speaker} content={message.content} />
            {message.recommendations && message.recommendations.length > 0 && (
              <ul className="flex flex-col gap-2 self-start">
                {message.recommendations.map((rec) => (
                  <li
                    key={`${message.id}-${rec.seminar_name}`}
                    className="max-w-[85%] rounded-2xl border border-[#add8e6]/60 bg-white p-3 shadow-sm"
                  >
                    <p className="text-sm font-bold text-sky-900">
                      {rec.seminar_name}
                    </p>
                    <p className="mt-1 text-sm text-zinc-600">{rec.reason}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {isSending && <ChatBubble speaker="assistant" content="考え中..." />}
        <div ref={endRef} />
      </div>

      <div className="mt-3 flex items-end gap-2">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSending}
          rows={1}
          maxLength={MESSAGE_MAX_LENGTH}
          placeholder="やりたいことを入力"
          className="max-h-40 flex-1 resize-none rounded-2xl border border-[#add8e6]/60 bg-white px-4 py-2 text-sm text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50 disabled:bg-[#e6e6e6]/40"
        />
        <button
          type="button"
          onClick={() => void handleSend()}
          disabled={!canSend}
          className="shrink-0 rounded-full bg-[#add8e6] px-5 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px disabled:cursor-not-allowed focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
        >
          送信
        </button>
      </div>
      <div className="mt-1 flex items-center justify-between text-[11px] text-zinc-400">
        <span>Enterで送信・Shift+Enterで改行</span>
        <span className="tabular-nums">
          {input.length}/{MESSAGE_MAX_LENGTH}
        </span>
      </div>
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] text-zinc-400">
          ※ 会話内容は保存されません。ページを更新・移動すると消えます。
        </p>
        <button
          type="button"
          onClick={handleReset}
          disabled={isSending || messages.length === 0}
          className="shrink-0 rounded-full px-2 py-1 text-xs font-medium text-zinc-500 hover:bg-[#e6e6e6]/60 hover:text-zinc-900 disabled:opacity-40 disabled:hover:bg-transparent"
        >
          会話をリセット
        </button>
      </div>
    </section>
  );
}

function ChatBubble({
  speaker,
  content,
}: {
  speaker: "user" | "assistant";
  content: string;
}) {
  return (
    <div
      className={speaker === "user" ? "flex justify-end" : "flex justify-start"}
    >
      <p
        className={[
          "max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm",
          speaker === "user"
            ? "bg-[#add8e6] text-sky-950"
            : "bg-white text-zinc-700 shadow-sm",
        ].join(" ")}
      >
        {content}
      </p>
    </div>
  );
}

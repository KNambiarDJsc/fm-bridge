"use client";

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { useChatMutation } from "@/lib/api";
import { useAnalysisStore } from "@/store/trading";
import { Send, X, MessageCircle } from "lucide-react";

interface Message {
    role: "user" | "assistant";
    content: string;
}

const QUICK_QUESTIONS = [
    "Why this verdict?",
    "Why hedge needed?",
    "What changed today?",
    "Explain the risk",
];

export function CopilotChat({ onClose }: { onClose: () => void }) {
    const [messages, setMessages] = useState<Message[]>([
        { role: "assistant", content: "I'm your FM Trading Copilot. Ask me anything about today's analysis — verdict, regime, hedge, risk, or why the system chose this trade." }
    ]);
    const [input, setInput] = useState("");
    const bottomRef = useRef<HTMLDivElement>(null);
    const { mutate: chat, isPending } = useChatMutation();
    const { verdict, symbol } = useAnalysisStore();

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const send = (question: string) => {
        if (!question.trim() || isPending) return;
        const q = question.trim();
        setMessages((m) => [...m, { role: "user", content: q }]);
        setInput("");
        chat(
            { question: q, symbol, context: verdict ?? undefined },
            {
                onSuccess: (data) => {
                    setMessages((m) => [...m, { role: "assistant", content: data.answer }]);
                },
                onError: (e) => {
                    setMessages((m) => [...m, { role: "assistant", content: `Error: ${e.message}` }]);
                },
            }
        );
    };

    return (
        <div className="flex flex-col h-full" style={{ background: "#0a0c13", borderTop: "1px solid #1e2d45" }}>
            {/* Header */}
            <div className="flex items-center gap-2 px-4 py-3 border-b border-b shrink-0">
                <MessageCircle size={14} className="text-bl" />
                <span className="font-mono text-[11px] font-bold text-t2 uppercase tracking-[1px]">AI Copilot Chat</span>
                <span className="font-mono text-[10px] text-t3 ml-1">— intelligence access layer, not the product</span>
                <button onClick={onClose} className="ml-auto text-t3 hover:text-t1 transition-colors">
                    <X size={14} />
                </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
                {messages.map((m, i) => (
                    <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                        <div className={cn(
                            "max-w-[85%] rounded-lg px-3 py-2 font-mono text-[12px] leading-relaxed",
                            m.role === "user"
                                ? "bg-bl/15 text-t1 border border-bl/20"
                                : "text-t2 rounded-lg"
                        )} style={m.role !== "user" ? { background: "#131924", border: "1px solid #1e2d45" } : undefined}>
                            {m.content}
                        </div>
          </div>
        ))}
            {isPending && (
                <div className="flex justify-start">
                    <div className="rounded-lg px-3 py-2 font-mono text-[11px] text-t3" style={{ background: "#131924", border: "1px solid #1e2d45" }}>
                        Thinking<span className="animate-pulse">…</span>
                    </div>
                </div>
            )}
            <div ref={bottomRef} />
        </div>

      {/* Quick questions */ }
    <div className="px-4 py-2 flex gap-2 overflow-x-auto shrink-0 border-t border-b">
        {QUICK_QUESTIONS.map((q) => (
            <button
                key={q}
                onClick={() => send(q)}
                disabled={isPending}
                className="font-mono text-[10px] text-t3 border border-b rounded px-2.5 py-1 whitespace-nowrap hover:text-bl hover:border-bl/40 transition-colors disabled:opacity-40 shrink-0"
            >
                {q}
            </button>
        ))}
    </div>

    {/* Input */ }
    <div className="flex gap-2 p-3 border-t border-b shrink-0">
        <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send(input))}
            placeholder="Ask about the analysis…"
            className="flex-1 rounded-xl px-3 py-2.5 font-mono text-[13px] text-t1 placeholder:text-t3 outline-none transition-colors" style={{ background: "#131924", border: "1px solid #1e2d45" }}
        />
        <button
            onClick={() => send(input)}
            disabled={!input.trim() || isPending}
            className="p-2 rounded-md bg-bl/10 border border-bl/30 text-bl hover:bg-bl/20 transition-colors disabled:opacity-40"
        >
            <Send size={14} />
        </button>
    </div>
    </div >
  );
}

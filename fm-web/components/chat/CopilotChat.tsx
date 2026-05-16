"use client";

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { useChatMutation } from "@/lib/api";
import { useAnalysisStore } from "@/store/trading";
import { Send, X, Terminal } from "lucide-react";

interface Message {
    role: "user" | "assistant";
    content: string;
}

const COMMANDS = [
    "Why this verdict?",
    "Explain hedge",
    "What changed?",
    "Risk assessment",
];

export function CopilotChat({ onClose }: { onClose: () => void }) {
    const [messages, setMessages] = useState<Message[]>([
        { role: "assistant", content: "Sovereign Copilot ready. Query the pipeline — verdict rationale, regime analysis, hedge logic, or risk state." }
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
        <div className="flex flex-col h-full" style={{ background: "var(--bg)", borderTop: "1px solid var(--b)" }}>

            {/* Header */}
            <div className="flex items-center gap-2 px-4 h-10 shrink-0" style={{ borderBottom: "1px solid var(--b)" }}>
                <Terminal size={12} className="text-[var(--regime)]" />
                <span className="font-mono text-11 font-semibold text-t2 tracking-wider">COMMAND</span>
                <span className="font-mono text-10 text-t3 ml-1">— strategic copilot</span>
                <button onClick={onClose} className="ml-auto text-t3 hover:text-t1 transition-colors">
                    <X size={13} />
                </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2.5 min-h-0">
                {messages.map((m, i) => (
                    <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                        <div className={cn(
                            "max-w-[85%] rounded-lg px-3 py-2 font-mono text-12 leading-relaxed",
                            m.role === "user"
                                ? "text-t1"
                                : "text-t2"
                        )} style={
                            m.role === "user"
                                ? { background: "var(--regime-dim)", border: "1px solid var(--regime-edge)" }
                                : { background: "var(--bg-s)", border: "1px solid var(--b)" }
                        }>
                            {m.content}
                        </div>
                    </div>
                ))}
                {isPending && (
                    <div className="flex justify-start">
                        <div className="rounded-lg px-3 py-2 font-mono text-11 text-t3"
                            style={{ background: "var(--bg-s)", border: "1px solid var(--b)" }}>
                            Processing<span className="animate-pulse">…</span>
                        </div>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            {/* Quick commands */}
            <div className="px-4 py-2 flex gap-1.5 overflow-x-auto shrink-0" style={{ borderTop: "1px solid var(--b)" }}>
                {COMMANDS.map((q) => (
                    <button key={q} onClick={() => send(q)} disabled={isPending}
                        className="font-mono text-10 text-t3 px-2.5 py-1 rounded whitespace-nowrap transition-colors hover:text-[var(--regime)] hover:bg-[var(--regime-dim)] disabled:opacity-30 shrink-0"
                        style={{ border: "1px solid var(--b)" }}>
                        {q}
                    </button>
                ))}
            </div>

            {/* Input */}
            <div className="flex gap-2 p-3 shrink-0" style={{ borderTop: "1px solid var(--b)" }}>
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send(input))}
                    placeholder="Query the pipeline…"
                    className="flex-1 rounded-lg px-3 py-2 font-mono text-13 text-t1 placeholder:text-t3 outline-none transition-colors"
                    style={{ background: "var(--bg-s)", border: "1px solid var(--b)" }}
                />
                <button onClick={() => send(input)} disabled={!input.trim() || isPending}
                    className="px-3 py-2 rounded-lg font-mono text-11 transition-colors disabled:opacity-30"
                    style={{ background: "var(--regime-dim)", border: "1px solid var(--regime-edge)", color: "var(--regime)" }}>
                    <Send size={13} />
                </button>
            </div>
        </div>
    );
}

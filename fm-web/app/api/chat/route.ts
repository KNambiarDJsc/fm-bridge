// Next.js API route: POST /api/chat
// Proxies to fm-agents:8003/api/chat

import { NextRequest, NextResponse } from "next/server";

const AGENTS_URL = process.env.AGENTS_URL || "http://localhost:8003";

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();

        const upstream = await fetch(`${AGENTS_URL}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        const data = await upstream.json();
        return NextResponse.json(data, { status: upstream.ok ? 200 : upstream.status });

    } catch (err: unknown) {
        return NextResponse.json(
            { status: "error", answer: `Chat unavailable: ${err instanceof Error ? err.message : "unknown"}` },
            { status: 502 }
        );
    }
}

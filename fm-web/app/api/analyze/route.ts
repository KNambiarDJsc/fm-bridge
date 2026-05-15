// Next.js API route: POST /api/analyze
// Proxies to fm-agents:8003/api/analyze
// Avoids CORS when frontend is on a different port in production.
// Also adds server-side error handling and timeout.

import { NextRequest, NextResponse } from "next/server";

const AGENTS_URL = process.env.AGENTS_URL || "http://localhost:8003";
const TIMEOUT_MS = 90_000; // 90s — pipeline can take up to 60s

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();

        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

        const upstream = await fetch(`${AGENTS_URL}/api/analyze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            signal: controller.signal,
        });

        clearTimeout(timer);

        const data = await upstream.json();

        if (!upstream.ok) {
            return NextResponse.json(
                { status: "error", error: data.detail || "Agent pipeline error" },
                { status: upstream.status }
            );
        }

        return NextResponse.json(data, { status: 200 });

    } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Unknown error";
        const isAbort = message.includes("abort") || message.includes("AbortError");

        return NextResponse.json(
            {
                status: "error",
                error: isAbort
                    ? "Analysis timed out after 90s — agents may be overloaded"
                    : `Proxy error: ${message}`,
            },
            { status: isAbort ? 504 : 502 }
        );
    }
}

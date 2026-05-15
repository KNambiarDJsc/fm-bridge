// Next.js API route: /api/bridge/[...path]
// Catch-all proxy to fm-bridge:8002
//
// Maps:
//   GET  /api/bridge/api/ltp?index=NIFTY+50  → bridge:8002/api/ltp?index=NIFTY+50
//   GET  /api/bridge/api/capital-shield       → bridge:8002/api/capital-shield
//   POST /api/bridge/api/capital-shield/reset-kill-switch → bridge:8002/...
//
// This means the frontend never needs to call localhost:8002 directly.
// In production, only one origin (Next.js) calls the Python backends.

import { NextRequest, NextResponse } from "next/server";

const BRIDGE_URL = process.env.BRIDGE_URL || "http://localhost:8002";

async function proxy(req: NextRequest, path: string) {
    const url = new URL(req.url);
    const upstream = `${BRIDGE_URL}/${path}${url.search}`;

    try {
        const opts: RequestInit = { method: req.method };

        if (req.method !== "GET" && req.method !== "HEAD") {
            const body = await req.text();
            if (body) {
                opts.body = body;
                opts.headers = { "Content-Type": "application/json" };
            }
        }

        const res = await fetch(upstream, opts);
        const data = await res.json();
        return NextResponse.json(data, { status: res.status });

    } catch (err: unknown) {
        return NextResponse.json(
            { error: `Bridge proxy error: ${err instanceof Error ? err.message : "unknown"}` },
            { status: 502 }
        );
    }
}

export async function GET(
    req: NextRequest,
    { params }: { params: { path: string[] } }
) {
    return proxy(req, params.path.join("/"));
}

export async function POST(
    req: NextRequest,
    { params }: { params: { path: string[] } }
) {
    return proxy(req, params.path.join("/"));
}

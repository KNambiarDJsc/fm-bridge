/**
 * FM Trading Agency — Journal API Proxy
 * Proxies all /api/journal/* requests to fm-journal :8004
 * 
 * This closes the feedback loop:
 *   fm-web (trader logs trade) → fm-journal (stores + analyses it)
 */

import { NextRequest, NextResponse } from "next/server";

const JOURNAL_URL = process.env.JOURNAL_URL || "http://localhost:8004";

async function handler(req: NextRequest, { params }: { params: { path: string[] } }) {
    const path = (params.path || []).join("/");
    const url = `${JOURNAL_URL}/api/${path}${req.nextUrl.search}`;

    try {
        const init: RequestInit = {
            method: req.method,
            headers: { "Content-Type": "application/json" },
        };
        if (req.method !== "GET" && req.method !== "HEAD") {
            init.body = await req.text();
        }
        const upstream = await fetch(url, init);
        const body = await upstream.text();
        return new NextResponse(body, {
            status: upstream.status,
            headers: { "Content-Type": "application/json" },
        });
    } catch (e) {
        return NextResponse.json({ error: "Journal service unavailable", detail: String(e) }, { status: 502 });
    }
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const DELETE = handler;
export const PATCH = handler;

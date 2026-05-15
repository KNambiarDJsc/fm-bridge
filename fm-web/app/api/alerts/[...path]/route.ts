/**
 * FM Trading Agency — Alerts API Proxy
 * Proxies all /api/alerts/* requests to fm-alerts :8005
 *
 * Used when trader clicks "I'm watching this" on a verdict —
 * tells fm-alerts price monitor to watch entry/SL/T1/T2 levels
 * and fire Telegram alerts when they're hit.
 */

import { NextRequest, NextResponse } from "next/server";

const ALERTS_URL = process.env.ALERTS_URL || "http://localhost:8005";

async function handler(req: NextRequest, { params }: { params: { path: string[] } }) {
    const path = (params.path || []).join("/");
    const url = `${ALERTS_URL}/api/alerts/${path}${req.nextUrl.search}`;

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
        return NextResponse.json({ error: "Alerts service unavailable", detail: String(e) }, { status: 502 });
    }
}

export const GET = handler;
export const POST = handler;
export const DELETE = handler;

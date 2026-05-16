"use client";

import { useEffect, useRef } from "react";
import { useHistorical } from "@/lib/api";

interface Props {
    symbol: string;
    interval?: string;
    range?: string;
    height?: number;
}

// LightweightCharts is loaded dynamically to avoid SSR issues
export function PriceChart({ symbol, interval = "day", range = "6mo", height = 260 }: Props) {
    const containerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<unknown>(null);
    const seriesRef = useRef<unknown>(null);
    const { data, isLoading, error } = useHistorical(symbol, interval, range);

    // Create chart once
    useEffect(() => {
        if (!containerRef.current) return;

        let chart: unknown;

        import("lightweight-charts").then(({ createChart, CrosshairMode, LineStyle }) => {
            if (!containerRef.current) return;

            chart = createChart(containerRef.current, {
                width: containerRef.current.clientWidth,
                height: height,
                layout: {
                    background: { color: "#050507" },
                    textColor: "#9aa0a6",
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10,
                },
                grid: {
                    vertLines: { color: "rgba(255,255,255,0.04)", style: LineStyle.Dotted },
                    horzLines: { color: "rgba(255,255,255,0.04)", style: LineStyle.Dotted },
                },
                crosshair: {
                    mode: CrosshairMode.Normal,
                    vertLine: { color: "rgba(96,165,250,0.2)", labelBackgroundColor: "#0a0b0f" },
                    horzLine: { color: "rgba(96,165,250,0.2)", labelBackgroundColor: "#0a0b0f" },
                },
                rightPriceScale: {
                    borderColor: "rgba(255,255,255,0.06)",
                    scaleMargins: { top: 0.08, bottom: 0.08 },
                },
                timeScale: {
                    borderColor: "#1a2232",
                    timeVisible: interval !== "day",
                    secondsVisible: false,
                    fixLeftEdge: true,
                    fixRightEdge: true,
                },
                handleScroll: { mouseWheel: true, pressedMouseMove: true },
                handleScale: { mouseWheel: true, pinch: true },
            });

            // Candlestick series
            const series = (chart as ReturnType<typeof createChart>).addCandlestickSeries({
                upColor: "#34d399",
                downColor: "#f87171",
                borderUpColor: "#34d399",
                borderDownColor: "#f87171",
                wickUpColor: "#34d39966",
                wickDownColor: "#f8717166",
            });

            chartRef.current = chart;
            seriesRef.current = series;

            // Responsive resize
            const ro = new ResizeObserver(() => {
                if (containerRef.current) {
                    (chart as ReturnType<typeof createChart>).applyOptions({
                        width: containerRef.current.clientWidth,
                    });
                }
            });
            ro.observe(containerRef.current);
        });

        return () => {
            if (chart) (chart as { remove: () => void }).remove();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [height, interval]);

    // Feed data when it arrives
    useEffect(() => {
        if (!seriesRef.current || !data?.data?.length) return;

        const bars = data.data
            .map((row) => ({
                time: row[0] as unknown as string,
                open: row[1] as number,
                high: row[2] as number,
                low: row[3] as number,
                close: row[4] as number,
            }))
            // LightweightCharts requires time strings sorted ascending
            .sort((a, b) => (a.time > b.time ? 1 : -1));

        (seriesRef.current as { setData: (d: unknown[]) => void }).setData(bars);
        (chartRef.current as { timeScale: () => { fitContent: () => void } })
            ?.timeScale()
            .fitContent();
    }, [data]);

    return (
        <div className="rounded-xl overflow-hidden" style={{ background: "var(--bg-s)", border: "1px solid var(--b)" }}>
            <div className="flex items-center gap-2 px-4 py-2" style={{ borderBottom: "1px solid var(--b)" }}>
                <span className="font-mono text-[10px] font-bold text-t2 uppercase tracking-[2px]">
                    {symbol}
                </span>
                <span className="font-mono text-[9px] text-t3">{interval === "day" ? "Daily" : interval} · {range}</span>
                {isLoading && (
                    <span className="ml-auto font-mono text-[9px] text-bl animate-pulse">Loading chart…</span>
                )}
                {error && (
                    <span className="ml-auto font-mono text-[9px] text-bear">Chart unavailable</span>
                )}
            </div>
            <div ref={containerRef} style={{ height }} />
        </div>
    );
}

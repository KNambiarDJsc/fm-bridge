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
                    background: { color: "#0b0f17" },
                    textColor: "#8a9ab5",
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10,
                },
                grid: {
                    vertLines: { color: "#1a2232", style: LineStyle.Dotted },
                    horzLines: { color: "#1a2232", style: LineStyle.Dotted },
                },
                crosshair: {
                    mode: CrosshairMode.Normal,
                    vertLine: { color: "#3a9eff40", labelBackgroundColor: "#101520" },
                    horzLine: { color: "#3a9eff40", labelBackgroundColor: "#101520" },
                },
                rightPriceScale: {
                    borderColor: "#1a2232",
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
                upColor: "#0db37a",
                downColor: "#f04f4f",
                borderUpColor: "#0db37a",
                borderDownColor: "#f04f4f",
                wickUpColor: "#0db37a66",
                wickDownColor: "#f04f4f66",
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
                time: row[0] as string,
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
        <div className="bg-bg2 border border-b rounded-xl overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-b">
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

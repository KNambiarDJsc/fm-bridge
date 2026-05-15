import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./app/**/*.{ts,tsx}",
        "./components/**/*.{ts,tsx}",
        "./hooks/**/*.{ts,tsx}",
        "./lib/**/*.{ts,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                mono: ["var(--font-mono)", "JetBrains Mono", "monospace"],
                head: ["var(--font-head)", "Syne", "sans-serif"],
                sans: ["var(--font-head)", "Syne", "sans-serif"],
            },
            colors: {
                bg: "#060816",
                bg2: "#0a0e1a",
                bg3: "#0e1428",
                b: "#182035",
                b2: "#1f2d4a",
                t1: "#e8edf8",
                t2: "#7d8ea8",
                t3: "#3d4f68",
                bull: "#00c896",
                bull2: "#4cffb2",
                bear: "#ff4d5a",
                bear2: "#ff8590",
                hedge: "#9d7dff",
                hedge2: "#c4b0ff",
                wait: "#f5a623",
                wait2: "#ffd07a",
                bl: "#3a9eff",
                cy: "#00e5d4",
                accent: "var(--accent)",
            },
            boxShadow: {
                "verdict-bull": "0 0 60px rgba(0,200,150,0.18), 0 0 120px rgba(0,200,150,0.07)",
                "verdict-bear": "0 0 60px rgba(255,77,90,0.18), 0 0 120px rgba(255,77,90,0.07)",
                "verdict-hedge": "0 0 60px rgba(157,125,255,0.18), 0 0 120px rgba(157,125,255,0.07)",
                "verdict-wait": "0 0 60px rgba(245,166,35,0.18), 0 0 120px rgba(245,166,35,0.07)",
                "glass": "0 4px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.04) inset",
                "glow-sm": "0 0 20px var(--accent-glow)",
                "glow-md": "0 0 40px var(--accent-glow)",
            },
            backdropBlur: {
                "2xl": "40px",
            },
            animation: {
                "verdict-in": "verdictMorphIn 0.45s cubic-bezier(0.34,1.56,0.64,1) forwards",
                "pulse-slow": "pulse 2.5s cubic-bezier(0.4,0,0.6,1) infinite",
                "fade-in": "fadeIn 0.3s ease",
                "slide-up": "slideUp 0.25s ease",
                "data-in": "dataIn 0.3s ease forwards",
                "spin-slow": "spin 3s linear infinite",
                "pulse-dot": "pulseDot 2s ease infinite",
            },
            keyframes: {
                verdictMorphIn: {
                    "0%": { opacity: "0", transform: "translateY(-12px) scale(0.97)", filter: "blur(4px)" },
                    "60%": { opacity: "1", transform: "translateY(2px) scale(1.005)", filter: "blur(0)" },
                    "100%": { opacity: "1", transform: "translateY(0) scale(1)", filter: "blur(0)" },
                },
                fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
                slideUp: { "0%": { opacity: "0", transform: "translateY(8px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
                dataIn: { "from": { opacity: "0", transform: "translateY(4px)" }, "to": { opacity: "1", transform: "translateY(0)" } },
                pulseDot: {
                    "0%,100%": { opacity: "1" },
                    "50%": { opacity: "0.4" },
                },
            },
            transitionTimingFunction: {
                "spring": "cubic-bezier(0.34, 1.56, 0.64, 1)",
            },
        },
    },
    plugins: [],
};
export default config;

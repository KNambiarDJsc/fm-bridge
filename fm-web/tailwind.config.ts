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
                sans: ["var(--font-mono)", "JetBrains Mono", "monospace"],
            },
            colors: {
                bg: "#08090f",
                bg2: "#0d1117",
                bg3: "#131924",
                bg4: "#1a2235",
                b: "#1e2d45",
                b2: "#28395a",
                t1: "#f0f4ff",
                t2: "#9dafc8",
                t3: "#556680",
                bull: "#12e89e",
                bear: "#ff5561",
                hedge: "#a78bfa",
                wait: "#fbbf24",
                bl: "#60a5fa",
                cy: "#22d3ee",
            },
            fontSize: {
                "10": "10px",
                "11": "11px",
                "12": "12px",
                "13": "13px",
            },
            boxShadow: {
                "verdict-bull": "0 0 48px rgba(18,232,158,0.2), 0 0 100px rgba(18,232,158,0.08)",
                "verdict-bear": "0 0 48px rgba(255,85,97,0.2),  0 0 100px rgba(255,85,97,0.08)",
                "verdict-hedge": "0 0 48px rgba(167,139,250,0.2),0 0 100px rgba(167,139,250,0.08)",
                "verdict-wait": "0 0 48px rgba(251,191,36,0.2), 0 0 100px rgba(251,191,36,0.08)",
                "glow": "0 0 30px var(--accent-glow)",
            },
            animation: {
                "verdict-in": "verdictIn 0.4s cubic-bezier(0.34,1.4,0.64,1) forwards",
                "pulse-slow": "pulseDot 2.5s ease infinite",
                "spin-slow": "spin 3s linear infinite",
                "fade-in": "fadeIn 0.25s ease forwards",
                "slide-up": "slideUp 0.2s ease forwards",
            },
            keyframes: {
                verdictIn: {
                    "0%": { opacity: "0", transform: "translateY(-10px) scale(0.98)", filter: "blur(3px)" },
                    "65%": { opacity: "1", transform: "translateY(1px) scale(1.002)", filter: "blur(0)" },
                    "100%": { opacity: "1", transform: "translateY(0) scale(1)", filter: "blur(0)" },
                },
                pulseDot: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.35" } },
                fadeIn: { from: { opacity: "0" }, to: { opacity: "1" } },
                slideUp: { from: { opacity: "0", transform: "translateY(6px)" }, to: { opacity: "1", transform: "translateY(0)" } },
            },
        },
    },
    plugins: [],
};
export default config;

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
                bg: "#07090d",
                bg2: "#0b0f17",
                bg3: "#101520",
                b: "#1a2232",
                b2: "#252f42",
                t1: "#ecf0f8",
                t2: "#8a9ab5",
                t3: "#48566a",
                bull: "#0db37a",
                bear: "#f04f4f",
                hedge: "#8b5cf6",
                wait: "#e8a020",
                bl: "#3a9eff",
                cy: "#00d4c8",
            },
            animation: {
                "verdict-in": "verdictIn 0.35s ease forwards",
                "pulse-slow": "pulse 2.5s cubic-bezier(0.4,0,0.6,1) infinite",
                "fade-in": "fadeIn 0.2s ease",
                "slide-up": "slideUp 0.25s ease",
            },
            keyframes: {
                verdictIn: {
                    "0%": { opacity: "0", transform: "translateY(-6px)" },
                    "100%": { opacity: "1", transform: "translateY(0)" },
                },
                fadeIn: {
                    "0%": { opacity: "0" },
                    "100%": { opacity: "1" },
                },
                slideUp: {
                    "0%": { opacity: "0", transform: "translateY(8px)" },
                    "100%": { opacity: "1", transform: "translateY(0)" },
                },
            },
        },
    },
    plugins: [],
};
export default config;

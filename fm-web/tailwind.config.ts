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
                sans: ["var(--font-sans)", "Inter", "sans-serif"],
            },
            colors: {
                bg: "var(--bg)",
                bg2: "var(--bg2)",
                bg3: "var(--bg3)",
                bg4: "var(--bg4)",
                b: "var(--b)",
                b2: "var(--b2)",
                t1: "var(--t1)",
                t2: "var(--t2)",
                t3: "var(--t3)",
                bull: "var(--bull)",
                bear: "var(--bear)",
                hedge: "var(--hedge)",
                wait: "var(--wait)",
                bl: "var(--bl)",
                cy: "var(--cy)",
                accent: "var(--accent)",
                "accent-dim": "var(--accent-dim)",
                "accent-glow": "var(--accent-glow)",
                "accent-edge": "var(--accent-edge)",
            },
            fontSize: {
                "10": "10px",
                "11": "11px",
                "12": "12px",
                "13": "13px",
            },
            boxShadow: {
                "verdict-bull": "0 8px 32px rgba(0, 255, 148, 0.15), 0 0 100px rgba(0, 255, 148, 0.05)",
                "verdict-bear": "0 8px 32px rgba(255, 42, 95, 0.15), 0 0 100px rgba(255, 42, 95, 0.05)",
                "verdict-hedge": "0 8px 32px rgba(192, 132, 252, 0.15), 0 0 100px rgba(192, 132, 252, 0.05)",
                "verdict-wait": "0 8px 32px rgba(252, 211, 77, 0.15), 0 0 100px rgba(252, 211, 77, 0.05)",
                "glow": "0 0 30px var(--accent-glow)",
                "glass": "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
            },
            animation: {
                "verdict-in": "verdictIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards",
                "pulse-slow": "pulseDot 3s ease-in-out infinite",
                "spin-slow": "spin 4s linear infinite",
                "fade-in": "fadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards",
                "slide-up": "slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards",
                "mesh": "meshGradient 15s ease infinite alternate",
            },
            keyframes: {
                verdictIn: {
                    "0%": { opacity: "0", transform: "translateY(-15px) scale(0.97)", filter: "blur(5px)" },
                    "100%": { opacity: "1", transform: "translateY(0) scale(1)", filter: "blur(0)" },
                },
                pulseDot: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.2" } },
                fadeIn: { from: { opacity: "0" }, to: { opacity: "1" } },
                slideUp: { from: { opacity: "0", transform: "translateY(10px)", filter: "blur(4px)" }, to: { opacity: "1", transform: "translateY(0)", filter: "blur(0)" } },
                meshGradient: {
                    "0%": { backgroundPosition: "0% 0%" },
                    "100%": { backgroundPosition: "100% 100%" },
                }
            },
            backdropBlur: {
                "xs": "2px",
                "glass": "12px",
            }
        },
    },
    plugins: [],
};
export default config;

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
                sans: ["var(--font-sans)", "Inter", "system-ui", "sans-serif"],
            },
            colors: {
                bg:     "var(--bg)",
                "bg-s": "var(--bg-s)",
                "bg-e": "var(--bg-e)",
                "bg-f": "var(--bg-f)",
                b:      "var(--b)",
                "b-h":  "var(--b-h)",
                t0:     "var(--t0)",
                t1:     "var(--t1)",
                t2:     "var(--t2)",
                t3:     "var(--t3)",
                bull:   "var(--bull)",
                bear:   "var(--bear)",
                hedge:  "var(--hedge)",
                wait:   "var(--wait)",
                bl:     "var(--blue)",
                cy:     "var(--cyan)",
                regime:      "var(--regime)",
                "regime-dim":"var(--regime-dim)",
                "regime-mid":"var(--regime-mid)",
                "regime-glow":"var(--regime-glow)",
                "regime-edge":"var(--regime-edge)",
            },
            fontSize: {
                "10": "10px",
                "11": "11px",
                "12": "12px",
                "13": "13px",
                "15": "15px",
            },
            boxShadow: {
                "verdict-bull":  "0 4px 40px rgba(52,211,153,0.12)",
                "verdict-bear":  "0 4px 40px rgba(248,113,113,0.12)",
                "verdict-hedge": "0 4px 40px rgba(167,139,250,0.12)",
                "verdict-wait":  "0 4px 40px rgba(251,191,36,0.12)",
                "regime":        "0 0 40px var(--regime-dim)",
                "glow":          "0 0 20px var(--regime-glow)",
            },
            animation: {
                "verdict-in":  "verdictIn 0.5s cubic-bezier(0.16,1,0.3,1) forwards",
                "pulse-slow":  "pulseDot 3s ease-in-out infinite",
                "spin-slow":   "spin 4s linear infinite",
                "fade-in":     "fadeIn 0.3s cubic-bezier(0.16,1,0.3,1) forwards",
                "slide-up":    "slideUp 0.4s cubic-bezier(0.16,1,0.3,1) forwards",
                "scale-in":    "scaleIn 0.3s cubic-bezier(0.16,1,0.3,1) forwards",
            },
            keyframes: {
                verdictIn: {
                    "0%":   { opacity: "0", transform: "translateY(-12px) scale(0.97)", filter: "blur(4px)" },
                    "100%": { opacity: "1", transform: "translateY(0) scale(1)", filter: "blur(0)" },
                },
                pulseDot: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.3" } },
                fadeIn:   { from: { opacity: "0" }, to: { opacity: "1" } },
                slideUp:  { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "translateY(0)" } },
                scaleIn:  { from: { opacity: "0", transform: "scale(0.96)" }, to: { opacity: "1", transform: "scale(1)" } },
            },
        },
    },
    plugins: [],
};
export default config;

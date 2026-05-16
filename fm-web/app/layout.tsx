import type { Metadata } from "next";
import { JetBrains_Mono, Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const mono = JetBrains_Mono({
    subsets: ["latin"],
    variable: "--font-mono",
    weight: ["400", "500", "600", "700"],
});

const inter = Inter({
    subsets: ["latin"],
    variable: "--font-sans",
    weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
    title: "FM Sovereign — AI Derivatives Intelligence",
    description: "Institutional-grade 9-layer AI pipeline for NSE derivatives. Trade market structure, not noise.",
    icons: { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" className={`${mono.variable} ${inter.variable}`}>
            <body>
                <Providers>{children}</Providers>
            </body>
        </html>
    );
}

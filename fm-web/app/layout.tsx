import type { Metadata } from "next";
import { JetBrains_Mono, Syne } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const mono = JetBrains_Mono({
    subsets: ["latin"],
    variable: "--font-mono",
    weight: ["400", "600", "700", "800"],
});

const syne = Syne({
    subsets: ["latin"],
    variable: "--font-head",
    weight: ["400", "700", "800"],
});

export const metadata: Metadata = {
    title: "FM Trading Agency",
    description: "AI-Native Derivatives Intelligence — NSE Copilot",
    icons: { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" className={`${mono.variable} ${syne.variable}`}>
            <body className="bg-bg text-t1 font-head antialiased">
                <Providers>{children}</Providers>
            </body>
        </html>
    );
}

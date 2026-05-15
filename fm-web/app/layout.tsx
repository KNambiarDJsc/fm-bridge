import type { Metadata } from "next";
import { JetBrains_Mono, Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const mono = JetBrains_Mono({
    subsets: ["latin"],
    variable: "--font-mono",
    weight: ["400", "500", "600", "700", "800"],
});

const inter = Inter({
    subsets: ["latin"],
    variable: "--font-sans",
    weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
    title: "FM Trading Agency",
    description: "AI-Native Derivatives Intelligence — NSE Copilot",
    icons: { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" className={`${mono.variable} ${inter.variable}`}>
            <body className="bg-bg text-t1 font-sans antialiased selection:bg-accent/30 selection:text-white">
                <Providers>{children}</Providers>
            </body>
        </html>
    );
}

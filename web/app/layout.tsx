import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-geist-sans" });

export const metadata: Metadata = {
  title: "Restaurant recommendations",
  description: "Phase 5 web UI — calls the Phase 4 FastAPI backend only.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans min-h-screen bg-zinc-50 text-zinc-950 antialiased`}>
        {children}
      </body>
    </html>
  );
}

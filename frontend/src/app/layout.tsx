import type { Metadata } from "next";
import { DM_Mono, Playfair_Display } from "next/font/google";
import "./globals.css";

const playfairDisplay = Playfair_Display({
  variable: "--font-wordmark",
  subsets: ["latin"],
  weight: ["600", "700"],
});

const dmMono = DM_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "PolicyPulse",
  description: "Multi-agent policy simulation frontend",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${playfairDisplay.variable} ${dmMono.variable} h-full antialiased`}>
      <body className="min-h-full bg-[var(--bg-primary)] text-[var(--text-primary)] font-sans">{children}</body>
    </html>
  );
}

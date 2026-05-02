import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

const jbMono = JetBrains_Mono({
  variable: "--font-jbmono",
  subsets: ["latin"],
  weight: ["400", "600"],
});

export const metadata: Metadata = {
  title: "SentinelSleep — AI Guardian for PTSD Nightmares",
  description:
    "SentinelSleep detects nightmare acoustic signatures from bedroom audio and plays calibrated therapeutic soundscapes to gently interrupt distress — without waking you.",
  openGraph: {
    title: "SentinelSleep",
    description: "AI-powered PTSD nightmare detection and therapeutic intervention.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jbMono.variable} h-full`}
    >
      <body className="min-h-full bg-bg text-text antialiased">
        {children}
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Video Transcriber",
  description:
    "Transcribe video and audio to TXT, SRT, VTT, and JSON — powered by Whisper.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ACC Claim Console",
  description:
    "Health New Zealand | Te Whatu Ora — ACC45 injury claim lodgement and ACC18 medical certification (research mockup).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-NZ">
      <body>{children}</body>
    </html>
  );
}

import type { Metadata } from "next";

import WarmBackend from "@/components/WarmBackend";

import "./globals.css";

export const metadata: Metadata = {
  title: "Lead Agent",
  description: "AI Lead Qualification",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <WarmBackend />
        {children}
      </body>
    </html>
  );
}

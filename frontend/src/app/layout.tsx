import type { Metadata } from "next";

import WarmBackend from "@/components/WarmBackend";

import "./globals.css";

export const metadata: Metadata = {
  // `template` lets each page set its own tab name (e.g. "Chat · LeadLoop")
  // by exporting `title`; `default` is used by pages that don't.
  title: {
    default: "LeadLoop — AI Lead Qualification & Follow-up",
    template: "%s · LeadLoop",
  },
  description:
    "LeadLoop qualifies, scores, assigns, and follows up on every inbound lead — so a human closes, and no high-value lead ever goes cold.",
  // Chrome shows this on the tab; the mark is src/app/icon.svg (brand loop).
  applicationName: "LeadLoop",
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

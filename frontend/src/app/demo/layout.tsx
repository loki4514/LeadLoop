import type { Metadata } from "next";

// page.tsx is a client component and can't export metadata itself, so the tab
// title for /demo lives in this server layout.
export const metadata: Metadata = {
  title: "Property Q&A",
  description:
    "Ask about buying property in India — home loans, stamp duty, registration and RERA — answered from a real real-estate knowledge base. No sign-up needed.",
};

export default function DemoLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

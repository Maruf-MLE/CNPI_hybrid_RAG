import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "CNPI RAG – Admin Panel",
  description: "Admin panel for managing CNPI RAG documents and captains",
};

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "#0f172a",
        color: "#e2e8f0",
        fontFamily: "system-ui, Segoe UI, Roboto, sans-serif",
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}

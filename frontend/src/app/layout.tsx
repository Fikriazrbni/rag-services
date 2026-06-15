import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/common/Sidebar";

export const metadata: Metadata = {
  title: "RAG Service - Knowledge Base Builder",
  description: "Model-agnostic RAG-as-a-Service platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex">
        <Sidebar />
        <main className="flex-1 ml-64">{children}</main>
      </body>
    </html>
  );
}

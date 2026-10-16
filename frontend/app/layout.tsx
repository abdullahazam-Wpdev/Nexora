import "./globals.css";
import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "NEXORA · Research workspace",
  description: "Independent intelligence, built locally.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

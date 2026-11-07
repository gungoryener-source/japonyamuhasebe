import type { Metadata, Viewport } from "next";
import "./globals.css";
import { LangProvider } from "./components/lang";

export const metadata: Metadata = {
  title: "J-SaaS 会計 | ダッシュボード",
  description: "日本の中小企業向けクラウド会計ダッシュボード",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#1E293B" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body className="font-sans"><LangProvider>{children}</LangProvider></body>
    </html>
  );
}

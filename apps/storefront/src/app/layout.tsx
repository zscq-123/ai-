import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NOVA 企业商城",
  description: "面向企业采购与零售客户的一站式智能商城",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

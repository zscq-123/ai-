import type { Metadata } from "next";
import { AuthPage } from "@/features/auth/components/AuthPage";

export const metadata: Metadata = { title: "登录 - NOVA 企业商城" };

export default function LoginPage() {
  return <AuthPage mode="login" />;
}

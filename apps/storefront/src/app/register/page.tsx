import type { Metadata } from "next";
import { AuthPage } from "@/features/auth/components/AuthPage";

export const metadata: Metadata = { title: "免费注册 - NOVA 企业商城" };

export default function RegisterPage() {
  return <AuthPage mode="register" />;
}

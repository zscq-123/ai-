import type { Metadata } from "next";
import { MerchantApplyForm } from "@/features/merchant/components/MerchantApplyForm";

export const metadata: Metadata = { title: "商家入驻 | NOVA 企业商城", description: "申请成为 NOVA 企业商城第三方商家" };

export default function MerchantApplyPage() { return <MerchantApplyForm />; }

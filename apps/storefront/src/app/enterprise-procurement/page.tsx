import type { Metadata } from "next";
import { ChannelPage } from "@/features/channel/components/ChannelPage";
import { channels } from "@/features/channel/model/channelContent";

export const metadata: Metadata = { title: "企业集采 | NOVA 企业商城", description: "企业集中采购、协议价格与统一履约服务" };

export default function Page() {
  return <ChannelPage config={channels["enterprise-procurement"]} />;
}

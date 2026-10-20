import type { Metadata } from "next";
import { ChannelPage } from "@/features/channel/components/ChannelPage";
import { channels } from "@/features/channel/model/channelContent";

export const metadata: Metadata = { title: "工业品 | NOVA 企业商城", description: "企业工业品、五金工具与劳保物资采购频道" };

export default function Page() {
  return <ChannelPage config={channels["industrial"]} />;
}

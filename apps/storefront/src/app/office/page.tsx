import type { Metadata } from "next";
import { ChannelPage } from "@/features/channel/components/ChannelPage";
import { channels } from "@/features/channel/model/channelContent";

export const metadata: Metadata = { title: "办公设备 | NOVA 企业商城", description: "商用电脑、会议设备与办公耗材采购频道" };

export default function Page() {
  return <ChannelPage config={channels["office"]} />;
}

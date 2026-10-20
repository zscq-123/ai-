import type { Metadata } from "next";
import { ChannelPage } from "@/features/channel/components/ChannelPage";
import { channels } from "@/features/channel/model/channelContent";

export const metadata: Metadata = { title: "品牌馆 | NOVA 企业商城", description: "NOVA 企业商城官方授权品牌频道" };

export default function Page() {
  return <ChannelPage config={channels["brands"]} />;
}

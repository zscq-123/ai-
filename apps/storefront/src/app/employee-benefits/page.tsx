import type { Metadata } from "next";
import { ChannelPage } from "@/features/channel/components/ChannelPage";
import { channels } from "@/features/channel/model/channelContent";

export const metadata: Metadata = { title: "员工福利 | NOVA 企业商城", description: "企业员工福利、节日礼盒与生活好物采购频道" };

export default function Page() {
  return <ChannelPage config={channels["employee-benefits"]} />;
}

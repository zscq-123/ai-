import { Suspense } from "react";
import type { ChannelConfig } from "../model/channelContent";
import { ChannelLanding } from "./ChannelLanding";
import styles from "./channelLanding.module.css";

export function ChannelPage({ config }: { config: ChannelConfig }) {
  return (
    <Suspense fallback={<div className={styles.pageSkeleton}><span /><div /><section><i /><i /><i /></section></div>}>
      <ChannelLanding config={config} />
    </Suspense>
  );
}

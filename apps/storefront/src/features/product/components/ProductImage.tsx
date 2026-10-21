"use client";

import { useState } from "react";
import Image from "next/image";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import type { CommerceIconName } from "@commerce/icon-assets";

export function ProductImage({ src, name, fallback = "package", size = 240, priority = false }: {
  src?: string | null;
  name: string;
  fallback?: CommerceIconName;
  size?: number;
  priority?: boolean;
}) {
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const url = src?.startsWith("/api/public/")
    ? `${process.env.NEXT_PUBLIC_COMMERCE_API_URL ?? "http://127.0.0.1:8080"}${src}`
    : src;
  if (!url || failedSource === url) return <CommerceIcon name={fallback} size={size} largeSource priority={priority} />;
  return <Image src={url} alt={name} width={size} height={size} unoptimized
    loading={priority ? "eager" : "lazy"} onError={() => setFailedSource(url)}
    style={{ width: "100%", height: "100%", objectFit: "contain", filter: "none" }} />;
}

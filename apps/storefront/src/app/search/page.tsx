import type { Metadata } from "next";
import { SearchPage } from "@/features/search/components/SearchPage";

export const metadata: Metadata = {
  title: "商品搜索 | NOVA 企业商城",
  description: "搜索 NOVA 企业商城的企业采购商品与服务。",
};

type SearchRouteProps = {
  searchParams: Promise<{ q?: string | string[] }>;
};

export default function SearchRoute({ searchParams }: SearchRouteProps) {
  return <SearchPage searchParams={searchParams} />;
}

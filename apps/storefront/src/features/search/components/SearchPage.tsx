import { Suspense } from "react";
import { SearchResults } from "./SearchResults";
import styles from "./search.module.css";

type SearchPageProps = {
  searchParams: Promise<{ q?: string | string[] }>;
};

export function SearchPage({ searchParams }: SearchPageProps) {
  return (
    <Suspense fallback={<SearchSkeleton />}>
      <SearchResults searchParams={searchParams} />
    </Suspense>
  );
}

function SearchSkeleton() {
  return (
    <div className={styles.skeleton} aria-label="正在加载搜索结果">
      <span />
      <div />
      <section>{Array.from({ length: 8 }, (_, index) => <i key={index} />)}</section>
    </div>
  );
}

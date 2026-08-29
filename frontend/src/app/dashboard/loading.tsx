import { CardSkeleton, Skeleton } from "@/components/Skeleton";

/** Route-level fallback: shown by Next during navigation, before page JS runs. */
export default function Loading() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <Skeleton className="h-7 w-48" />
      <Skeleton className="mt-2 h-4 w-80" />
      <div className="mt-6 space-y-3">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
    </div>
  );
}

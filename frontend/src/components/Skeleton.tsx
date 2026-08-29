/**
 * Shimmer placeholders shown while data loads. Sized to match the real content
 * so swapping skeleton -> data doesn't shift layout.
 */

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded bg-neutral-200/80 dark:bg-neutral-800 ${className}`}
    />
  );
}

/** Placeholder rows for a table, matching its column count. */
export function TableSkeleton({
  rows = 6,
  cols = 8,
}: {
  rows?: number;
  cols?: number;
}) {
  return (
    <>
      {Array.from({ length: rows }).map((_, r) => (
        <tr
          key={r}
          className="border-b border-neutral-100 last:border-0 dark:border-neutral-800/60"
        >
          {Array.from({ length: cols }).map((_, c) => (
            <td key={c} className="px-4 py-3">
              {/* Vary widths so rows read as content, not a grid of bars. */}
              <Skeleton
                className={`h-4 ${c === 0 ? "w-32" : c % 3 === 0 ? "w-16" : "w-24"}`}
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

/** Generic card/list placeholder for non-table pages. */
export function CardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <Skeleton className="h-5 w-40" />
      <div className="mt-3 space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton key={i} className={`h-4 ${i === lines - 1 ? "w-2/3" : "w-full"}`} />
        ))}
      </div>
    </div>
  );
}

import Link from "next/link";

/**
 * LeadLoop brand mark. A continuous "loop" — an open circular arrow whose head
 * feeds back into a filled node — evoking the lead lifecycle that always loops
 * back to follow-up. Rendered as inline SVG with the brand gradient so it stays
 * crisp at any size and adapts to light/dark automatically.
 */

const SIZES = {
  sm: { box: 24, text: "text-sm" },
  md: { box: 32, text: "text-lg" },
  lg: { box: 40, text: "text-xl" },
} as const;

export function LogoMark({
  size = 32,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  // Unique gradient id per render size to avoid collisions when multiple marks
  // appear on one page.
  const gid = `ll-grad-${size}`;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      role="img"
      aria-label="LeadLoop"
      className={className}
    >
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="40" y2="40">
          <stop offset="0%" stopColor="#6366f1" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
      </defs>
      {/* Rounded tile */}
      <rect width="40" height="40" rx="10" fill={`url(#${gid})`} />
      {/* The loop: an open ring (arc) that leaves a gap where the arrow feeds in */}
      <path
        d="M27.5 13.2A9 9 0 1 0 29 20"
        stroke="white"
        strokeWidth="3"
        strokeLinecap="round"
      />
      {/* Arrowhead closing the loop */}
      <path
        d="M25.4 9.4 29.4 13l-4.4 3"
        stroke="white"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Center node — the captured lead */}
      <circle cx="20" cy="20" r="3.1" fill="white" />
    </svg>
  );
}

export default function Logo({
  size = "md",
  wordmark = true,
  href,
  className = "",
}: {
  size?: keyof typeof SIZES;
  wordmark?: boolean;
  /** If set, the whole logo is a link (e.g. "/" or "/dashboard"). */
  href?: string;
  className?: string;
}) {
  const s = SIZES[size];
  const content = (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <LogoMark size={s.box} className="shadow-sm" />
      {wordmark && (
        <span className={`${s.text} font-semibold tracking-tight`}>
          LeadLoop
        </span>
      )}
    </span>
  );

  if (href) {
    return (
      <Link href={href} className="inline-flex items-center">
        {content}
      </Link>
    );
  }
  return content;
}

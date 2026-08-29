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

      {/* Loop mark — Lucide "refresh-cw" cycle arrows, scaled/centered into the
          tile (source viewBox 24 -> placed at 8,8 with scale 1). Two arcs with
          arrowheads read as a continuous loop: the lead lifecycle. */}
      <g
        transform="translate(8 8)"
        stroke="white"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      >
        <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
        <path d="M3 3v5h5" />
        <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
        <path d="M16 16h5v5" />
      </g>
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

import React from "react";

/**
 * Lightweight message formatter (no markdown dependency). Renders the subset of
 * markdown the agent actually emits: paragraphs, **bold**, "-"/"*" bullet lists,
 * "1." numbered lists, and "Label: value" detail lines (the label is bolded).
 * Used for both the employee chat and the public widget so property results and
 * follow-ups read cleanly instead of blurring into an undifferentiated wall.
 *
 * The agent's phrasing is inconsistent (sometimes it bolds/numbers, sometimes it
 * doesn't), so formatting is inferred from structure, not just from markdown.
 */

function renderInline(text: string, keyPrefix: string) {
  // Split on **bold** spans, keeping the delimiters via the capture group.
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**")) {
      return <strong key={`${keyPrefix}-${i}`}>{p.slice(2, -2)}</strong>;
    }
    return <span key={`${keyPrefix}-${i}`}>{p}</span>;
  });
}

// Short leading label like "Location:", "Price:", "Area:" — bold the label.
const LABEL_RE = /^([A-Z][A-Za-z /]{1,20}):\s+(.*)$/;

export default function RichText({ text }: { text: string }) {
  const rawLines = text.split("\n");
  const blocks: React.ReactNode[] = [];

  let bullets: string[] = [];
  let numbers: string[] = [];
  // Running counter so a numbered list keeps counting (1, 2, 3…) even when its
  // items are separated by sub-content like bullet lists — which is exactly how
  // the agent formats property results (title, then Location/Price bullets).
  let numberSeq = 0;

  const flushBullets = (key: string) => {
    if (bullets.length === 0) return;
    const items = bullets;
    bullets = [];
    blocks.push(
      <ul key={key} className="my-1 list-disc space-y-0.5 pl-5">
        {items.map((b, i) => (
          <li key={i}>{renderInline(b, `${key}-${i}`)}</li>
        ))}
      </ul>,
    );
  };

  const flushNumbers = (key: string) => {
    if (numbers.length === 0) return;
    const items = numbers;
    numbers = [];
    // Explicit `start` continues the sequence across interruptions.
    const start = numberSeq - items.length + 1;
    blocks.push(
      <ol
        key={key}
        start={start}
        className="my-1 list-decimal space-y-0.5 pl-5"
      >
        {items.map((n, i) => (
          <li key={i}>{renderInline(n, `${key}-${i}`)}</li>
        ))}
      </ol>,
    );
  };

  rawLines.forEach((raw, i) => {
    const line = raw.trim();
    const numbered = line.match(/^\d+[.)]\s+(.*)$/);
    const bullet = line.match(/^[-*]\s+(.*)$/);
    const label = line.match(LABEL_RE);

    if (numbered) {
      flushBullets(`ul-${i}`);
      numberSeq += 1; // continue the running sequence
      numbers.push(numbered[1]);
      return;
    }
    if (bullet) {
      // Bullets are sub-content of the current numbered item — flush the number
      // block (so its <ol start> is emitted) but DON'T reset the sequence.
      flushNumbers(`ol-${i}`);
      bullets.push(bullet[1]);
      return;
    }

    // A blank line is just spacing between items — skip without flushing/reset.
    if (!line) return;

    // Any real content line ends open lists.
    flushBullets(`ul-${i}`);
    flushNumbers(`ol-${i}`);

    // "Label: value" detail line — bold the label, tight spacing so the
    // details of one property group visually.
    if (label) {
      blocks.push(
        <p key={`d-${i}`} className="leading-snug">
          <span className="font-medium text-neutral-500 dark:text-neutral-400">
            {label[1]}:
          </span>{" "}
          {renderInline(label[2], `d-${i}`)}
        </p>,
      );
      return;
    }

    // A plain line immediately followed by a "Label:" line is a heading (e.g. a
    // property title like "Marina Vista — 2BHK"). Give it weight + top spacing
    // so consecutive properties are clearly separated.
    const next = (rawLines[i + 1] ?? "").trim();
    const isHeading = LABEL_RE.test(next) && !LABEL_RE.test(line);
    if (isHeading) {
      blocks.push(
        <p key={`h-${i}`} className="mt-3 font-semibold first:mt-0">
          {renderInline(line, `h-${i}`)}
        </p>,
      );
      return;
    }

    // A genuine prose paragraph breaks any numbered sequence — a later numbered
    // list should restart at 1.
    numberSeq = 0;
    blocks.push(
      <p key={`p-${i}`} className="my-1 leading-relaxed">
        {renderInline(line, `p-${i}`)}
      </p>,
    );
  });

  flushBullets("ul-end");
  flushNumbers("ol-end");
  return <div className="space-y-0.5">{blocks}</div>;
}

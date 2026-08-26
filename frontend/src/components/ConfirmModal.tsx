"use client";

import { useEffect, useRef, useState } from "react";

export interface ConfirmModalProps {
  open: boolean;
  title: string;
  /** Body text or nodes explaining the action. */
  message?: React.ReactNode;
  /** Optional bullet warnings rendered as an amber callout. */
  warnings?: string[];
  confirmLabel?: string;
  cancelLabel?: string;
  /** Visual weight of the confirm button. */
  tone?: "primary" | "danger";
  /**
   * When set, the modal shows a countdown and auto-confirms when it reaches 0.
   * Used by delete: "Deleting in 5…" with a chance to cancel.
   */
  countdownSeconds?: number;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * In-app confirmation dialog (replaces window.confirm/alert). Renders a modal
 * overlay; confirms on Enter, cancels on Escape or backdrop click. When
 * `countdownSeconds` is provided it counts down and auto-confirms at 0.
 */
export default function ConfirmModal({
  open,
  title,
  message,
  warnings,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "primary",
  countdownSeconds,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const [remaining, setRemaining] = useState<number | null>(
    countdownSeconds ?? null,
  );
  // Keep the latest onConfirm without retriggering the timer effect.
  const confirmRef = useRef(onConfirm);
  confirmRef.current = onConfirm;

  // (Re)start the countdown whenever the modal opens with a countdown set.
  useEffect(() => {
    if (!open || countdownSeconds == null) {
      setRemaining(countdownSeconds ?? null);
      return;
    }
    setRemaining(countdownSeconds);
    const started = Date.now();
    const id = setInterval(() => {
      const left = countdownSeconds - Math.floor((Date.now() - started) / 1000);
      if (left <= 0) {
        clearInterval(id);
        setRemaining(0);
        confirmRef.current();
      } else {
        setRemaining(left);
      }
    }, 250);
    return () => clearInterval(id);
  }, [open, countdownSeconds]);

  // Keyboard: Enter confirms, Escape cancels.
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
      if (e.key === "Enter") onConfirm();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel, onConfirm]);

  if (!open) return null;

  const counting = countdownSeconds != null && (remaining ?? 0) > 0;
  const confirmText =
    countdownSeconds != null
      ? counting
        ? `${confirmLabel} now`
        : confirmLabel
      : confirmLabel;

  const confirmBtn =
    tone === "danger"
      ? "bg-red-600 hover:bg-red-500"
      : "bg-indigo-600 hover:bg-indigo-500";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-neutral-900/50 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Panel */}
      <div className="relative w-full max-w-sm rounded-2xl border border-neutral-200 bg-white p-5 shadow-xl dark:border-neutral-800 dark:bg-neutral-900">
        <h3 className="text-base font-semibold">{title}</h3>

        {message && (
          <div className="mt-2 text-sm leading-relaxed text-neutral-600 dark:text-neutral-300">
            {message}
          </div>
        )}

        {warnings && warnings.length > 0 && (
          <ul className="mt-3 space-y-1.5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
            {warnings.map((w, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <span aria-hidden>⚠</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
        )}

        {counting && (
          <p className="mt-3 text-sm font-medium text-red-600 dark:text-red-400">
            Deleting in {remaining}s… cancel to stop.
          </p>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-lg border border-neutral-300 px-3.5 py-1.5 text-sm font-medium text-neutral-700 transition hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-200 dark:hover:bg-neutral-800"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={`rounded-lg px-3.5 py-1.5 text-sm font-medium text-white transition ${confirmBtn}`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

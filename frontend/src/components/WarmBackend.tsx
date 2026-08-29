"use client";

import { useEffect } from "react";

import { API_BASE } from "@/lib/api";

/**
 * Both services scale to zero on Railway, so a visitor's first real API call
 * would otherwise pay the backend's cold start on top of the frontend's. Ping
 * /health as soon as the app mounts: the backend wakes while the user is still
 * reading the page, and the request that matters lands on a warm container.
 *
 * Fire-and-forget by design — a failed wake-up must never surface to the user,
 * and the real call retries anyway.
 */
export default function WarmBackend() {
  useEffect(() => {
    const controller = new AbortController();
    // keepalive so the ping survives a fast navigation away from the page.
    fetch(`${API_BASE}/health`, {
      signal: controller.signal,
      keepalive: true,
      cache: "no-store",
    }).catch(() => {});
    return () => controller.abort();
  }, []);

  return null;
}

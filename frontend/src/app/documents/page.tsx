"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import AppShell from "@/components/AppShell";
import {
  getToken,
  listDocuments,
  uploadDocument,
  type DocumentRead,
  type DocumentStatus,
} from "@/lib/api";

const STATUS_STYLES: Record<DocumentStatus, string> = {
  pending: "bg-neutral-200 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200",
  processing: "bg-amber-200 text-amber-900 dark:bg-amber-500/30 dark:text-amber-200",
  ready: "bg-green-200 text-green-900 dark:bg-green-500/30 dark:text-green-200",
  failed: "bg-red-200 text-red-900 dark:bg-red-500/30 dark:text-red-200",
};

function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentRead[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    try {
      setDocs(await listDocuments(token));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents");
    }
  }, []);

  // Initial load + poll while anything is still ingesting.
  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const inFlight = docs.some(
      (d) => d.status === "pending" || d.status === "processing",
    );
    if (!inFlight) return;
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [docs, refresh]);

  async function handleFiles(files: FileList | null) {
    const token = getToken();
    if (!token || !files || files.length === 0) return;
    setError(null);
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        await uploadDocument(token, file);
      }
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <AppShell>
      {() => (
        <div>
          <h1 className="text-2xl font-semibold">Documents</h1>
          <p className="mt-1 text-neutral-500">
            Upload files to the knowledge base. They&apos;re embedded and become
            searchable once <span className="font-medium">ready</span>.
          </p>

          <div className="mt-6 flex items-center gap-3">
            <label className="cursor-pointer rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-neutral-700 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200">
              {uploading ? "Uploading…" : "Upload file"}
              <input
                ref={fileRef}
                type="file"
                multiple
                disabled={uploading}
                onChange={(e) => handleFiles(e.target.files)}
                className="hidden"
                accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md,.csv"
              />
            </label>
            <button
              onClick={refresh}
              className="rounded-md border border-neutral-300 px-4 py-2 text-sm text-neutral-700 transition hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-200 dark:hover:bg-neutral-800"
            >
              Refresh
            </button>
          </div>

          {error && (
            <p className="mt-3 rounded-md bg-red-100 px-3 py-2 text-sm text-red-800 dark:bg-red-500/20 dark:text-red-200">
              {error}
            </p>
          )}

          <div className="mt-6 overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-800">
            {docs.length === 0 ? (
              <p className="p-6 text-center text-sm text-neutral-500">
                No documents yet. Upload one to get started.
              </p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="bg-neutral-100 text-neutral-500 dark:bg-neutral-800/50">
                  <tr>
                    <th className="px-4 py-2 font-medium">File</th>
                    <th className="px-4 py-2 font-medium">Status</th>
                    <th className="px-4 py-2 font-medium">Uploaded</th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map((d) => (
                    <tr
                      key={d.id}
                      className="border-t border-neutral-200 dark:border-neutral-800"
                    >
                      <td className="px-4 py-2">
                        <span className="font-medium">{d.filename}</span>
                        {d.status === "failed" && d.error && (
                          <span
                            className="ml-2 text-xs text-red-600 dark:text-red-400"
                            title={d.error}
                          >
                            — {d.error.slice(0, 60)}
                            {d.error.length > 60 ? "…" : ""}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2">
                        <StatusBadge status={d.status} />
                      </td>
                      <td className="px-4 py-2 text-neutral-500">
                        {new Date(d.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}

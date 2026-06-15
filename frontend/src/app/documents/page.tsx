"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch, apiUpload, getSSEUrl } from "@/lib/api";
import type { Document } from "@/types";

const statusColors: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  processing: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    loadDocuments();
    // SSE for status updates
    const evtSource = new EventSource(getSSEUrl("/documents/status/stream"));
    evtSource.addEventListener("status_change", () => {
      loadDocuments();
    });
    return () => evtSource.close();
  }, []);

  async function loadDocuments() {
    try {
      const res = await apiFetch("/documents?page_size=100");
      setDocuments(res.data || []);
    } catch {}
  }

  async function handleFiles(files: FileList | File[]) {
    setError(null);
    setUploading(true);
    try {
      await apiUpload(Array.from(files));
      loadDocuments();
    } catch (err: any) {
      setError(err.message);
    }
    setUploading(false);
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this document and all its chunks?")) return;
    try {
      await apiFetch(`/documents/${id}`, { method: "DELETE" });
      loadDocuments();
    } catch (err: any) {
      setError(err.message);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files.length) {
      handleFiles(e.dataTransfer.files);
    }
  }

  function formatSize(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">Documents</h1>

      {/* Upload area */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center mb-6 transition-colors ${
          dragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-gray-400"
        }`}
      >
        <p className="text-gray-600 mb-2">
          {uploading ? "Uploading..." : "Drag & drop files here, or click to browse"}
        </p>
        <p className="text-xs text-gray-400">Supported: PDF, DOCX, TXT (max 50MB each)</p>
        <input
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
          className="hidden"
          id="file-upload"
        />
        <label
          htmlFor="file-upload"
          className="mt-3 inline-block bg-blue-600 text-white px-4 py-2 rounded cursor-pointer hover:bg-blue-700"
        >
          Browse Files
        </label>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 mb-4">
          {error}
        </div>
      )}

      {/* Documents table */}
      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">File</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Size</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Chunks</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="px-6 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {documents.map((doc) => (
              <tr key={doc.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm font-medium">{doc.filename}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{formatSize(doc.file_size)}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex px-2 py-1 text-xs rounded-full font-medium ${statusColors[doc.status]}`}>
                    {doc.status}
                    {doc.pipeline_stage && ` (${doc.pipeline_stage})`}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">{doc.chunk_count}</td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {new Date(doc.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={doc.status === "pending" || doc.status === "processing"}
                    className="text-red-600 hover:text-red-800 text-sm disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {documents.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                  No documents uploaded yet. Drag files above to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

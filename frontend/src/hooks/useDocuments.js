/**
 * hooks/useDocuments.js
 * Fetches the list of ingested documents and handles PDF upload.
 *
 * Returned values
 * ---------------
 * documents      – Array<{ file_name: string, file_size_kb: number }>
 * isLoading      – true while the document list is being fetched
 * isUploading    – true while a file upload + ingestion is in progress
 * uploadError    – error string or null
 * uploadResult   – { message, file_name, chunks } or null (last upload)
 * uploadDocument(file) – upload a File object via POST /api/upload
 * refresh()      – re-fetch the document list
 */

import { useState, useCallback, useEffect } from "react";
import axios from "axios";

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "",
  timeout: 120_000, // 2 min — ingestion can be slow for large PDFs
});

// ── API helpers ──────────────────────────────────────────────────────────────

async function fetchDocuments() {
  const { data } = await http.get("/api/documents");
  return data; // Array<{ file_name, file_size_kb }>
}

async function uploadPdf(file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await http.post("/api/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data; // { message, file_name, chunks }
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useDocuments() {
  const [documents,    setDocuments]    = useState([]);
  const [isLoading,    setIsLoading]    = useState(false);
  const [isUploading,  setIsUploading]  = useState(false);
  const [uploadError,  setUploadError]  = useState(null);
  const [uploadResult, setUploadResult] = useState(null);

  // Fetch the document list from GET /api/documents.
  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
    } catch {
      // Silently ignore — server may not be running yet.
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch once on mount.
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Upload a single PDF file and refresh the list on success.
  const uploadDocument = useCallback(async (file) => {
    if (!file) return;

    // Client-side guard — server also validates.
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Only PDF files are accepted.");
      return;
    }

    setUploadError(null);
    setUploadResult(null);
    setIsUploading(true);

    try {
      const result = await uploadPdf(file);
      setUploadResult(result);
      // Refresh document list so the new file appears immediately.
      await refresh();
    } catch (err) {
      setUploadError(
        err?.response?.data?.detail ??
        err?.message ??
        "Upload failed. Please try again."
      );
    } finally {
      setIsUploading(false);
    }
  }, [refresh]);

  return {
    documents,
    isLoading,
    isUploading,
    uploadError,
    uploadResult,
    uploadDocument,
    refresh,
  };
}

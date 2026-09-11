/**
 * components/UploadPanel.jsx
 * PDF upload panel — drag-and-drop or file-picker.
 *
 * Features
 * --------
 * - Drag-and-drop zone (highlights on dragover)
 * - File-picker button fallback
 * - Upload progress state (spinner + "Ingesting…" label)
 * - Success toast: file name + chunk count
 * - Error message with retry-friendly UX
 * - Scrollable list of already-ingested documents
 * - Refresh button
 *
 * Props — none (all state lives in useDocuments)
 */

import { useRef, useState } from "react";
import { useDocuments } from "../hooks/useDocuments";

// ── Small helpers ────────────────────────────────────────────────────────────

function FileIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10"/>
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
    </svg>
  );
}

function Spinner() {
  return (
    <span style={{
      display:      "inline-block",
      width:        16,
      height:       16,
      border:       "2px solid #bfdbfe",
      borderTop:    "2px solid var(--clr-primary)",
      borderRadius: "50%",
      animation:    "spin .7s linear infinite",
      flexShrink:   0,
    }} />
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function UploadPanel() {
  const {
    documents,
    isLoading,
    isUploading,
    uploadError,
    uploadResult,
    uploadDocument,
    refresh,
  } = useDocuments();

  const inputRef          = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  // ── Drag handlers ──────────────────────────────────────────────────────────

  function handleDragOver(e) {
    e.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(e) {
    // Only clear when leaving the drop zone itself, not its children.
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setIsDragging(false);
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadDocument(file);
  }

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (file) uploadDocument(file);
    // Reset the input so the same file can be re-uploaded.
    e.target.value = "";
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div style={{
      flex:          1,
      overflowY:     "auto",
      padding:       "20px 20px 32px",
      display:       "flex",
      flexDirection: "column",
      gap:           20,
    }}>

      {/* Keyframe for spinner */}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      {/* ── Intro ── */}
      <div style={{
        background:   "#eff6ff",
        border:       "1px solid #bfdbfe",
        borderRadius: "var(--radius-md)",
        padding:      "12px 16px",
        fontSize:     13,
        color:        "#1e40af",
        lineHeight:   1.6,
      }}>
        <strong>Document Management</strong><br />
        Upload official college PDF documents here. The agent will read and
        index them so it can answer questions from the actual content.
      </div>

      {/* ── Drop zone ── */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isUploading && inputRef.current?.click()}
        style={{
          border:        `2px dashed ${isDragging ? "var(--clr-primary)" : "var(--clr-border)"}`,
          borderRadius:  "var(--radius-md)",
          background:    isDragging ? "#eff6ff" : "var(--clr-source-bg)",
          padding:       "32px 20px",
          textAlign:     "center",
          cursor:        isUploading ? "not-allowed" : "pointer",
          transition:    "border-color .15s, background .15s",
          display:       "flex",
          flexDirection: "column",
          alignItems:    "center",
          gap:           10,
        }}
      >
        {isUploading ? (
          <>
            <Spinner />
            <span style={{ fontSize: 14, color: "var(--clr-primary)", fontWeight: 600 }}>
              Ingesting document…
            </span>
            <span style={{ fontSize: 12, color: "var(--clr-text-muted)" }}>
              This may take a moment for large PDFs.
            </span>
          </>
        ) : (
          <>
            {/* Upload cloud icon */}
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none"
              stroke={isDragging ? "var(--clr-primary)" : "var(--clr-border)"}
              strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 16 12 12 8 16"/>
              <line x1="12" y1="12" x2="12" y2="21"/>
              <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
            </svg>
            <div style={{ fontSize: 14, fontWeight: 600, color: "var(--clr-text-main)" }}>
              {isDragging ? "Drop your PDF here" : "Drag & drop a PDF here"}
            </div>
            <div style={{ fontSize: 12, color: "var(--clr-text-muted)" }}>
              or{" "}
              <span style={{ color: "var(--clr-primary)", fontWeight: 600, textDecoration: "underline" }}>
                browse to upload
              </span>
            </div>
          </>
        )}

        {/* Hidden file input */}
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
      </div>

      {/* ── Upload success toast ── */}
      {uploadResult && !isUploading && (
        <div style={{
          background:   "#f0fdf4",
          border:       "1px solid #86efac",
          borderRadius: "var(--radius-md)",
          padding:      "12px 16px",
          fontSize:     13,
          color:        "#166534",
          display:      "flex",
          alignItems:   "flex-start",
          gap:          8,
          lineHeight:   1.6,
        }}>
          <span style={{ fontWeight: 700, fontSize: 16, lineHeight: 1 }}>✓</span>
          <div>
            <strong>{uploadResult.file_name}</strong> ingested successfully.
            <br />
            <span style={{ color: "#15803d" }}>
              {uploadResult.chunks} chunk{uploadResult.chunks !== 1 ? "s" : ""} stored in the vector database.
            </span>
          </div>
        </div>
      )}

      {/* ── Upload error ── */}
      {uploadError && !isUploading && (
        <div style={{
          background:   "var(--clr-error-bg)",
          border:       "1px solid var(--clr-error-border)",
          borderRadius: "var(--radius-md)",
          padding:      "12px 16px",
          fontSize:     13,
          color:        "var(--clr-error-text)",
          display:      "flex",
          alignItems:   "flex-start",
          gap:          8,
        }}>
          <span style={{ fontWeight: 700, fontSize: 15 }}>⚠</span>
          <span>{uploadError}</span>
        </div>
      )}

      {/* ── Document list ── */}
      <div>
        {/* Section header */}
        <div style={{
          display:      "flex",
          alignItems:   "center",
          justifyContent: "space-between",
          marginBottom: 10,
        }}>
          <span style={{
            fontSize:      12,
            fontWeight:    700,
            color:         "var(--clr-text-muted)",
            textTransform: "uppercase",
            letterSpacing: ".05em",
          }}>
            Ingested Documents ({documents.length})
          </span>

          <button
            onClick={refresh}
            disabled={isLoading}
            title="Refresh document list"
            style={{
              display:    "flex",
              alignItems: "center",
              gap:        4,
              fontSize:   12,
              color:      isLoading ? "var(--clr-border)" : "var(--clr-primary)",
              background: "none",
              border:     "none",
              cursor:     isLoading ? "default" : "pointer",
              padding:    "2px 4px",
            }}
          >
            <RefreshIcon />
            Refresh
          </button>
        </div>

        {/* Loading skeleton */}
        {isLoading && documents.length === 0 && (
          <div style={{
            background:   "var(--clr-source-bg)",
            border:       "1px solid var(--clr-border)",
            borderRadius: "var(--radius-md)",
            padding:      "16px",
            textAlign:    "center",
            fontSize:     13,
            color:        "var(--clr-text-muted)",
          }}>
            Loading…
          </div>
        )}

        {/* Empty state */}
        {!isLoading && documents.length === 0 && (
          <div style={{
            background:   "var(--clr-source-bg)",
            border:       "1px dashed var(--clr-border)",
            borderRadius: "var(--radius-md)",
            padding:      "24px 16px",
            textAlign:    "center",
            fontSize:     13,
            color:        "var(--clr-text-muted)",
            lineHeight:   1.7,
          }}>
            No documents uploaded yet.<br />
            Upload a college PDF above to get started.
          </div>
        )}

        {/* Document rows */}
        {documents.length > 0 && (
          <ul style={{
            listStyle:     "none",
            display:       "flex",
            flexDirection: "column",
            gap:           6,
          }}>
            {documents.map((doc) => (
              <li
                key={doc.file_name}
                style={{
                  display:       "flex",
                  alignItems:    "center",
                  gap:           10,
                  background:    "var(--clr-source-bg)",
                  border:        "1px solid var(--clr-border)",
                  borderRadius:  "var(--radius-sm)",
                  padding:       "9px 13px",
                  fontSize:      13,
                }}
              >
                {/* Icon */}
                <span style={{ color: "var(--clr-primary)", flexShrink: 0 }}>
                  <FileIcon />
                </span>

                {/* File name — truncate if too long */}
                <span style={{
                  flex:         1,
                  fontWeight:   500,
                  overflow:     "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace:   "nowrap",
                  color:        "var(--clr-text-main)",
                }}>
                  {doc.file_name}
                </span>

                {/* Size badge */}
                <span style={{
                  flexShrink:   0,
                  fontSize:     11,
                  color:        "var(--clr-text-muted)",
                  background:   "var(--clr-border)",
                  borderRadius: 4,
                  padding:      "1px 6px",
                  whiteSpace:   "nowrap",
                }}>
                  {doc.file_size_kb} KB
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

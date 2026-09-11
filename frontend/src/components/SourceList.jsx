/**
 * components/SourceList.jsx
 * Shows the source documents and page numbers cited in an AI answer.
 *
 * Props
 * -----
 * sources – Array<{ document: string, page: number }>
 */

export default function SourceList({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div style={{
      marginTop:    10,
      padding:      "8px 12px",
      background:   "var(--clr-source-bg)",
      border:       "1px solid var(--clr-border)",
      borderRadius: "var(--radius-sm)",
      fontSize:     13,
      color:        "var(--clr-source-text)",
    }}>
      {/* Label */}
      <div style={{
        fontWeight:   600,
        marginBottom: 5,
        display:      "flex",
        alignItems:   "center",
        gap:          5,
      }}>
        {/* Book icon — inline SVG, no dependency needed */}
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2.2"
          strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
        </svg>
        Sources
      </div>

      {/* One row per citation */}
      <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 3 }}>
        {sources.map((src, i) => (
          <li key={i} style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            {/* Bullet */}
            <span style={{ color: "var(--clr-primary)", fontWeight: 700, fontSize: 10 }}>▸</span>
            {/* Document name */}
            <span style={{ fontWeight: 500 }}>{src.document}</span>
            {/* Page badge */}
            <span style={{
              marginLeft:   "auto",
              background:   "var(--clr-border)",
              borderRadius: 4,
              padding:      "1px 6px",
              fontSize:     11,
              whiteSpace:   "nowrap",
            }}>
              p. {src.page}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

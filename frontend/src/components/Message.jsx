/**
 * components/Message.jsx
 * One chat bubble — either user (right, blue) or assistant (left, white).
 *
 * Props
 * -----
 * role    – "user" | "assistant"
 * text    – message string
 * sources – Array<{ document, page }>  (only present on assistant messages)
 * isError – boolean; renders the bubble in red when true
 */

import SourceList from "./SourceList";

export default function Message({ role, text, sources = [], isError = false }) {
  const isUser = role === "user";

  /* ── Bubble container ──────────────────────────────────────── */
  const wrap = {
    display:        "flex",
    justifyContent: isUser ? "flex-end" : "flex-start",
    marginBottom:   8,
    padding:        "0 4px",
  };

  /* ── The bubble itself ─────────────────────────────────────── */
  const bubble = {
    maxWidth:             "75%",
    padding:              "10px 14px",
    borderRadius:         "var(--radius-lg)",
    // User bubble: round all corners except bottom-right
    // Bot bubble:  round all corners except bottom-left
    ...(isUser
      ? { borderBottomRightRadius: 4, background: "var(--clr-user-bg)", color: "var(--clr-user-text)" }
      : { borderBottomLeftRadius:  4, background: isError ? "var(--clr-error-bg)" : "var(--clr-bot-bg)",
          color: isError ? "var(--clr-error-text)" : "var(--clr-bot-text)",
          border: isError ? "1px solid var(--clr-error-border)" : "1px solid var(--clr-border)" }),
    boxShadow:     "var(--shadow-sm)",
    fontSize:       14,
    lineHeight:     1.6,
    wordBreak:      "break-word",
    whiteSpace:     "pre-wrap",   // preserve line-breaks from the model
  };

  /* ── Role label (only on assistant bubbles) ───────────────── */
  const label = {
    fontSize:     11,
    fontWeight:   600,
    marginBottom: 4,
    color:        isError ? "var(--clr-error-text)" : "var(--clr-primary)",
    letterSpacing: ".04em",
    textTransform: "uppercase",
  };

  return (
    <div style={wrap}>
      <div style={{ maxWidth: "75%" }}>
        {/* Show "Agent" label on AI bubbles */}
        {!isUser && (
          <div style={label}>{isError ? "⚠ Error" : "Agent"}</div>
        )}

        <div style={bubble}>
          {text}
        </div>

        {/* Source citations — only visible on non-error AI messages */}
        {!isUser && !isError && sources.length > 0 && (
          <SourceList sources={sources} />
        )}
      </div>
    </div>
  );
}

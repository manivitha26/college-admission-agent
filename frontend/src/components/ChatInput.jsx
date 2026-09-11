/**
 * components/ChatInput.jsx
 * Text area + Send button docked at the bottom of the chat.
 *
 * Props
 * -----
 * onSend   – function(text: string) — called when the user submits
 * disabled – boolean — true while the AI is loading
 */

import { useState } from "react";

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState("");

  /* Submit on Enter (without Shift). Shift+Enter inserts a newline. */
  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleSend() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  }

  const canSend = text.trim().length > 0 && !disabled;

  return (
    <div style={{
      display:       "flex",
      alignItems:    "flex-end",
      gap:           10,
      padding:       "12px 16px",
      borderTop:     "1px solid var(--clr-border)",
      background:    "var(--clr-surface)",
    }}>
      {/* ── Text area ── */}
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder="Ask about admissions, fees, eligibility…"
        rows={1}
        style={{
          flex:         1,
          resize:       "none",
          border:       "1px solid var(--clr-border)",
          borderRadius: "var(--radius-md)",
          padding:      "9px 13px",
          fontSize:     14,
          lineHeight:   1.5,
          outline:      "none",
          background:   disabled ? "#f8fafc" : "#fff",
          color:        "var(--clr-text-main)",
          transition:   "border-color .15s",
          maxHeight:    120,
          overflowY:    "auto",
        }}
        onFocus={(e) => { e.target.style.borderColor = "var(--clr-primary)"; }}
        onBlur={(e)  => { e.target.style.borderColor = "var(--clr-border)";  }}
      />

      {/* ── Send button ── */}
      <button
        onClick={handleSend}
        disabled={!canSend}
        title="Send (Enter)"
        style={{
          flexShrink:   0,
          width:        40,
          height:       40,
          borderRadius: "50%",
          background:   canSend ? "var(--clr-primary)" : "var(--clr-border)",
          color:        canSend ? "#fff" : "#94a3b8",
          display:      "flex",
          alignItems:   "center",
          justifyContent:"center",
          transition:   "background .15s, transform .1s",
          cursor:       canSend ? "pointer" : "not-allowed",
        }}
        onMouseDown={(e) => { if (canSend) e.currentTarget.style.transform = "scale(.92)"; }}
        onMouseUp={(e)   => { e.currentTarget.style.transform = "scale(1)"; }}
      >
        {/* Paper-plane icon */}
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
        </svg>
      </button>
    </div>
  );
}

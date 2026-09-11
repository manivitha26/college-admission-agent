/**
 * components/ChatWindow.jsx
 * Scrollable list of chat messages.
 * Auto-scrolls to the bottom whenever a new message arrives.
 *
 * Props
 * -----
 * messages  – array from useChat()
 * isLoading – boolean — shows the typing indicator when true
 */

import { useEffect, useRef } from "react";
import Message          from "./Message";
import LoadingIndicator from "./LoadingIndicator";

// Suggestion chips shown on the empty-state screen.
// Each chip sends its label as the question when clicked.
const SUGGESTIONS = [
  { icon: "💰", label: "Tell me about fees" },
  { icon: "📄", label: "What documents do I need?" },
  { icon: "📅", label: "When is the deadline?" },
  { icon: "📚", label: "Which courses are available?" },
  { icon: "✅", label: "Am I eligible?" },
  { icon: "📝", label: "How do I apply?" },
  { icon: "🎓", label: "Are scholarships available?" },
];

export default function ChatWindow({ messages, isLoading, onSuggestion }) {
  const bottomRef = useRef(null);

  /* Scroll to bottom on every new message or loading state change */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div style={{
      flex:       1,
      overflowY:  "auto",
      padding:    "20px 16px 8px",
      display:    "flex",
      flexDirection: "column",
    }}>
      {/* ── Empty state ── */}
      {messages.length === 0 && !isLoading && (
        <div style={{
          margin:    "auto",
          textAlign: "center",
          color:     "var(--clr-text-muted)",
          maxWidth:  440,
          width:     "100%",
        }}>
          {/* Graduation cap icon */}
          <svg width="44" height="44" viewBox="0 0 24 24" fill="none"
            stroke="var(--clr-border)" strokeWidth="1.5"
            strokeLinecap="round" strokeLinejoin="round"
            style={{ marginBottom: 10 }}>
            <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
            <path d="M6 12v5c0 2 6 3 6 3s6-1 6-3v-5"/>
          </svg>
          <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>
            Ask me anything about admissions
          </p>
          <p style={{ fontSize: 12, marginBottom: 20 }}>
            Try one of these questions to get started:
          </p>

          {/* ── Suggestion chips ── */}
          <div style={{
            display:        "flex",
            flexWrap:       "wrap",
            gap:            8,
            justifyContent: "center",
          }}>
            {SUGGESTIONS.map(({ icon, label }) => (
              <button
                key={label}
                onClick={() => onSuggestion?.(label)}
                style={{
                  display:      "flex",
                  alignItems:   "center",
                  gap:          6,
                  padding:      "7px 13px",
                  borderRadius: 20,          // pill shape
                  border:       "1px solid var(--clr-border)",
                  background:   "#fff",
                  color:        "var(--clr-text-main)",
                  fontSize:     13,
                  cursor:       "pointer",
                  transition:   "border-color .15s, background .15s",
                  textAlign:    "left",
                  userSelect:   "none",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--clr-primary)";
                  e.currentTarget.style.background  = "#eff6ff";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--clr-border)";
                  e.currentTarget.style.background  = "#fff";
                }}
              >
                <span>{icon}</span>
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Messages ── */}
      {messages.map((msg) => (
        <Message
          key={msg.id}
          role={msg.role}
          text={msg.text}
          sources={msg.sources}
          isError={msg.isError}
        />
      ))}

      {/* ── Loading dots ── */}
      {isLoading && (
        <div style={{ paddingLeft: 4, marginBottom: 8 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: "var(--clr-primary)",
            textTransform: "uppercase", letterSpacing: ".04em", marginBottom: 4 }}>
            Agent
          </div>
          <LoadingIndicator />
        </div>
      )}

      {/* Invisible anchor for auto-scroll */}
      <div ref={bottomRef} />
    </div>
  );
}

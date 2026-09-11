/**
 * App.jsx
 * Root component — full-page layout with two tabs:
 *
 *  ┌──────────────────────────────────────┐
 *  │  Header (title + subtitle)           │
 *  ├─────────────┬────────────────────────┤
 *  │  💬 Chat    │  🎓 Eligibility Checker │  ← tab bar
 *  ├─────────────┴────────────────────────┤
 *  │                                      │
 *  │   Active tab content                 │
 *  │                                      │
 *  ├──────────────────────────────────────┤
 *  │   ChatInput  (Chat tab only)         │
 *  └──────────────────────────────────────┘
 */

import { useState } from "react";
import ChatWindow         from "./components/ChatWindow";
import ChatInput          from "./components/ChatInput";
import EligibilityChecker from "./components/EligibilityChecker";
import UploadPanel        from "./components/UploadPanel";
import { useChat }        from "./hooks/useChat";

// ── Tab bar button ─────────────────────────────────────────────────────────
function Tab({ label, icon, active, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        flex:          1,
        padding:       "10px 0",
        fontSize:      13,
        fontWeight:    active ? 700 : 500,
        color:         active ? "var(--clr-primary)" : "var(--clr-text-muted)",
        borderBottom:  active ? "2px solid var(--clr-primary)" : "2px solid transparent",
        background:    "none",
        cursor:        "pointer",
        transition:    "color .15s, border-color .15s",
        display:       "flex",
        alignItems:    "center",
        justifyContent:"center",
        gap:           6,
        userSelect:    "none",
      }}
    >
      <span>{icon}</span>
      {label}
    </button>
  );
}

// ── Root component ─────────────────────────────────────────────────────────
export default function App() {
  const [activeTab, setActiveTab]         = useState("chat");   // "chat" | "eligibility"
  const { messages, isLoading, sendMessage } = useChat();

  return (
    <div style={{
      height:         "100%",
      display:        "flex",
      flexDirection:  "column",
      alignItems:     "center",
      background:     "var(--clr-bg)",
    }}>

      {/* ── Centred card ── */}
      <div style={{
        width:          "100%",
        maxWidth:       760,
        height:         "100%",
        display:        "flex",
        flexDirection:  "column",
        background:     "var(--clr-surface)",
        boxShadow:      "var(--shadow-md)",
      }}>

        {/* ── Header ── */}
        <header style={{
          padding:      "18px 20px 16px",
          borderBottom: "1px solid var(--clr-border)",
          flexShrink:   0,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {/* Logo mark */}
            <div style={{
              width: 42, height: 42,
              borderRadius: "var(--radius-md)",
              background:   "var(--clr-primary)",
              display:      "flex",
              alignItems:   "center",
              justifyContent: "center",
              flexShrink:   0,
            }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
                stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
                <path d="M6 12v5c0 2 6 3 6 3s6-1 6-3v-5"/>
              </svg>
            </div>
            <div>
              <h1 style={{ fontSize: 17, fontWeight: 700, lineHeight: 1.2 }}>
                College Admission Agent
              </h1>
              <p style={{ fontSize: 12, color: "var(--clr-text-muted)", marginTop: 2 }}>
                Powered by IBM Granite · Answers from official documents
              </p>
            </div>
            {/* Online dot */}
            <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{
                width: 8, height: 8, borderRadius: "50%",
                background: "#22c55e", boxShadow: "0 0 0 2px #dcfce7",
              }} />
              <span style={{ fontSize: 12, color: "var(--clr-text-muted)" }}>Online</span>
            </div>
          </div>
        </header>

        {/* ── Tab bar ── */}
        <div style={{
          display:      "flex",
          borderBottom: "1px solid var(--clr-border)",
          flexShrink:   0,
          background:   "var(--clr-surface)",
        }}>
          <Tab
            icon="💬"
            label="Chat"
            active={activeTab === "chat"}
            onClick={() => setActiveTab("chat")}
          />
          <Tab
            icon="🎓"
            label="Eligibility"
            active={activeTab === "eligibility"}
            onClick={() => setActiveTab("eligibility")}
          />
          <Tab
            icon="📁"
            label="Documents"
            active={activeTab === "documents"}
            onClick={() => setActiveTab("documents")}
          />
        </div>

        {/* ── Tab content ── */}

        {/* Chat tab */}
        {activeTab === "chat" && (
          <>
            <ChatWindow
              messages={messages}
              isLoading={isLoading}
              onSuggestion={sendMessage}
            />
            <ChatInput onSend={sendMessage} disabled={isLoading} />
          </>
        )}

        {/* Eligibility tab */}
        {activeTab === "eligibility" && (
          <EligibilityChecker />
        )}

        {/* Documents tab */}
        {activeTab === "documents" && (
          <UploadPanel />
        )}

      </div>
    </div>
  );
}

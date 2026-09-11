/**
 * components/EligibilityChecker.jsx
 * Form + result card for the course eligibility recommendation feature.
 *
 * Renders:
 *   - Five labelled inputs (12th %, Maths, Physics, Chemistry, Preferred course)
 *   - Check Eligibility button (disabled while loading)
 *   - Loading indicator
 *   - Validation / API error message
 *   - Result card: analysis sections + disclaimer + source citations
 */

import { useEligibility } from "../hooks/useEligibility";
import LoadingIndicator from "./LoadingIndicator";

// ── Small reusable components ──────────────────────────────────────────────

function Field({ label, name, value, onChange, placeholder, disabled, type = "number" }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <label style={{ fontSize: 12, fontWeight: 600, color: "var(--clr-text-muted)" }}>
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(name, e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        min={type === "number" ? 0 : undefined}
        max={type === "number" ? 100 : undefined}
        step={type === "number" ? "0.1" : undefined}
        style={{
          border:       "1px solid var(--clr-border)",
          borderRadius: "var(--radius-sm)",
          padding:      "8px 11px",
          fontSize:     14,
          outline:      "none",
          background:   disabled ? "#f8fafc" : "#fff",
          color:        "var(--clr-text-main)",
          transition:   "border-color .15s",
          width:        "100%",
        }}
        onFocus={(e) => { e.target.style.borderColor = "var(--clr-primary)"; }}
        onBlur={(e)  => { e.target.style.borderColor = "var(--clr-border)";  }}
      />
    </div>
  );
}

function SectionCard({ children, style }) {
  return (
    <div style={{
      background:   "var(--clr-source-bg)",
      border:       "1px solid var(--clr-border)",
      borderRadius: "var(--radius-md)",
      padding:      "14px 16px",
      ...style,
    }}>
      {children}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export default function EligibilityChecker() {
  const { fields, setField, isLoading, result, error, submit, reset } = useEligibility();

  return (
    <div style={{
      flex:          1,
      overflowY:     "auto",
      padding:       "20px 20px 32px",
      display:       "flex",
      flexDirection: "column",
      gap:           20,
    }}>

      {/* ── Intro banner ── */}
      <div style={{
        background:   "#eff6ff",
        border:       "1px solid #bfdbfe",
        borderRadius: "var(--radius-md)",
        padding:      "12px 16px",
        fontSize:     13,
        color:        "#1e40af",
        lineHeight:   1.6,
      }}>
        <strong>Course Eligibility Checker</strong><br />
        Enter your 12th grade marks and preferred course. The agent will look up
        the official eligibility criteria from the college documents and tell you
        whether your profile appears to meet them.
      </div>

      {/* ── Input form ── */}
      <SectionCard>
        <div style={{
          display:             "grid",
          gridTemplateColumns: "1fr 1fr",
          gap:                 14,
        }}>
          <Field
            label="12th Overall Percentage (%)"
            name="percentage_12th"
            value={fields.percentage_12th}
            onChange={setField}
            placeholder="e.g. 85.5"
            disabled={isLoading}
          />
          <Field
            label="Mathematics Marks (%)"
            name="maths_marks"
            value={fields.maths_marks}
            onChange={setField}
            placeholder="e.g. 90"
            disabled={isLoading}
          />
          <Field
            label="Physics Marks (%)"
            name="physics_marks"
            value={fields.physics_marks}
            onChange={setField}
            placeholder="e.g. 88"
            disabled={isLoading}
          />
          <Field
            label="Chemistry Marks (%)"
            name="chemistry_marks"
            value={fields.chemistry_marks}
            onChange={setField}
            placeholder="e.g. 82"
            disabled={isLoading}
          />
        </div>

        {/* Preferred course — full width */}
        <div style={{ marginTop: 14 }}>
          <Field
            label="Preferred Course"
            name="preferred_course"
            value={fields.preferred_course}
            onChange={setField}
            placeholder="e.g. B.Tech CSE, MBA, M.Sc Physics"
            disabled={isLoading}
            type="text"
          />
        </div>

        {/* Buttons */}
        <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
          <button
            onClick={submit}
            disabled={isLoading}
            style={{
              flex:         1,
              padding:      "10px 0",
              borderRadius: "var(--radius-sm)",
              background:   isLoading ? "var(--clr-border)" : "var(--clr-primary)",
              color:        isLoading ? "#94a3b8" : "#fff",
              fontWeight:   600,
              fontSize:     14,
              cursor:       isLoading ? "not-allowed" : "pointer",
              transition:   "background .15s",
            }}
          >
            {isLoading ? "Checking…" : "Check Eligibility"}
          </button>

          {(result || error) && (
            <button
              onClick={reset}
              disabled={isLoading}
              style={{
                padding:      "10px 18px",
                borderRadius: "var(--radius-sm)",
                border:       "1px solid var(--clr-border)",
                background:   "#fff",
                color:        "var(--clr-text-muted)",
                fontSize:     13,
                cursor:       "pointer",
              }}
            >
              Clear
            </button>
          )}
        </div>
      </SectionCard>

      {/* ── Loading ── */}
      {isLoading && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 6 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--clr-primary)",
            textTransform: "uppercase", letterSpacing: ".04em" }}>
            Agent is analysing…
          </div>
          <LoadingIndicator />
        </div>
      )}

      {/* ── Error message ── */}
      {error && !isLoading && (
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
          <span>{error}</span>
        </div>
      )}

      {/* ── Result card ── */}
      {result && !isLoading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

          {/* Student profile summary */}
          <SectionCard style={{ background: "#f0f9ff", border: "1px solid #bae6fd" }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#0369a1",
              textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 8 }}>
              Your Profile
            </div>
            <div style={{
              display:             "grid",
              gridTemplateColumns: "repeat(2, 1fr)",
              gap:                 "4px 20px",
              fontSize:            13,
              color:               "#1e293b",
            }}>
              <span><strong>12th %:</strong> {fields.percentage_12th}%</span>
              <span><strong>Maths:</strong> {fields.maths_marks}%</span>
              <span><strong>Physics:</strong> {fields.physics_marks}%</span>
              <span><strong>Chemistry:</strong> {fields.chemistry_marks}%</span>
              <span style={{ gridColumn: "span 2" }}>
                <strong>Preferred Course:</strong> {fields.preferred_course}
              </span>
            </div>
          </SectionCard>

          {/* Analysis */}
          <SectionCard>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--clr-primary)",
              textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 10 }}>
              Eligibility Analysis
            </div>
            <div style={{
              fontSize:    14,
              lineHeight:  1.7,
              color:       "var(--clr-text-main)",
              whiteSpace:  "pre-wrap",  // preserve Granite's structured output
            }}>
              {result.analysis}
            </div>
          </SectionCard>

          {/* Sources */}
          {result.sources && result.sources.length > 0 && (
            <SectionCard>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--clr-text-muted)",
                textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 8,
                display: "flex", alignItems: "center", gap: 5 }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2.2"
                  strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                </svg>
                Sources
              </div>
              <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 4 }}>
                {result.sources.map((src, i) => (
                  <li key={i} style={{ display: "flex", alignItems: "baseline", gap: 6, fontSize: 13 }}>
                    <span style={{ color: "var(--clr-primary)", fontWeight: 700, fontSize: 10 }}>▸</span>
                    <span style={{ fontWeight: 500 }}>{src.document}</span>
                    <span style={{
                      marginLeft: "auto", background: "var(--clr-border)",
                      borderRadius: 3, padding: "0 5px", fontSize: 11,
                    }}>p. {src.page}</span>
                  </li>
                ))}
              </ul>
            </SectionCard>
          )}

          {/* Disclaimer — always shown, always prominent */}
          <div style={{
            background:   "#fefce8",
            border:       "1px solid #fde047",
            borderRadius: "var(--radius-md)",
            padding:      "12px 16px",
            fontSize:     12,
            color:        "#713f12",
            lineHeight:   1.6,
          }}>
            {result.disclaimer}
          </div>

        </div>
      )}
    </div>
  );
}

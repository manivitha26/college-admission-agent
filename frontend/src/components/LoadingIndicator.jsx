/**
 * components/LoadingIndicator.jsx
 * Three animated dots shown while the AI is thinking.
 */

const dotStyle = {
  display: "inline-block",
  width: 7,
  height: 7,
  borderRadius: "50%",
  background: "#94a3b8",
  margin: "0 3px",
  animation: "bounce 1.2s infinite ease-in-out",
};

export default function LoadingIndicator() {
  return (
    <>
      {/* Keyframe injected once as a style tag — avoids a CSS-in-JS dependency */}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0);   opacity: .4; }
          40%            { transform: translateY(-6px); opacity: 1;  }
        }
      `}</style>

      <div style={{
        display:        "flex",
        alignItems:     "center",
        gap:            2,
        padding:        "12px 16px",
        background:     "var(--clr-bot-bg)",
        borderRadius:   "var(--radius-lg)",
        borderBottomLeftRadius: 4,
        boxShadow:      "var(--shadow-sm)",
        width:          "fit-content",
        maxWidth:       320,
      }}>
        <span style={{ ...dotStyle, animationDelay: "0s"   }} />
        <span style={{ ...dotStyle, animationDelay: ".2s"  }} />
        <span style={{ ...dotStyle, animationDelay: ".4s"  }} />
      </div>
    </>
  );
}

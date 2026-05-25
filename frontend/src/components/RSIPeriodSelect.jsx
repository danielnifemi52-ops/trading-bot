import { useEffect } from 'react';

const RSI_PRESETS = [
  { label: "Fast",     value: 7,  desc: "More signals, more noise" },
  { label: "Default",  value: 14, desc: "Wilder's original" },
  { label: "Smooth",   value: 21, desc: "Fewer signals, more reliable" },
  { label: "Slow",     value: 28, desc: "Long-term trend only" },
];

export default function RSIPeriodSelect({ value, onChange }) {
  useEffect(() => {
    if (value !== "" && Number(value) < 5) {
      onChange(14)
    }
  }, [value, onChange])

  return (
    <div style={{ marginTop: "6px" }}>
      {/* Preset buttons */}
      <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
        {RSI_PRESETS.map(p => (
          <button
            key={p.value}
            type="button"
            onClick={() => onChange(p.value)}
            title={p.desc}
            style={{
              flex: 1, padding: "6px 4px", fontSize: 11, borderRadius: 5,
              background: value === p.value ? "#3b82f6" : "#0f1117",
              color: value === p.value ? "#fff" : "#64748b",
              border: `1px solid ${value === p.value ? "#3b82f6" : "#2a2d3a"}`,
              cursor: "pointer"
            }}
          >
            {p.label}<br/>
            <span style={{ fontSize: 10, opacity: 0.8 }}>{p.value}</span>
          </button>
        ))}
      </div>

      {/* Slider for custom value */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <input
          type="range" min={5} max={50} step={1}
          value={value}
          onChange={e => onChange(+e.target.value)}
          style={{ flex: 1, accentColor: "#3b82f6" }}
        />
        <input
          type="number"
          min={5}
          max={50}
          value={value}
          onChange={e => {
            const val = parseInt(e.target.value)
            if (!isNaN(val) && val >= 5 && val <= 50) {
              onChange(val)
            } else if (e.target.value === "") {
              onChange("")
            }
          }}
          onBlur={() => {
            if (value === "" || isNaN(value) || Number(value) < 5) {
              onChange(14)
            }
          }}
          style={{
            width: 52,
            textAlign: "center",
            fontSize: 16,
            fontWeight: 600,
            color: "#e2e8f0",
            background: "#0f1117",
            border: "1px solid #3b82f6",
            borderRadius: 5,
            padding: "2px 6px",
            outline: "none",
          }}
        />
      </div>
      <p style={{ fontSize: 10, color: "#475569", marginTop: 6, marginBottom: 0 }}>
        {RSI_PRESETS.find(p => p.value === value)?.desc || "Custom period"}
      </p>
    </div>
  );
}

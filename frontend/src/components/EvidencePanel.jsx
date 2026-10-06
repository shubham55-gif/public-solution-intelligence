import { evidenceRows } from "../utils/mapping";

export default function EvidencePanel({ risk }) {
  if (!risk) {
    return <p className="muted">Evidence unavailable.</p>;
  }
  return (
    <div className="evidence-list">
      {evidenceRows(risk).map(([label, component]) => (
        <div className="evidence-row" key={label}>
          <div>
            <strong>{label}</strong>
            <small>
              {component?.available
                ? `${component.percent.toFixed(1)}% · ${component.points.toFixed(2)} points`
                : "Evidence unavailable"}
            </small>
          </div>
          <span className={`status-pill ${component?.available ? "available" : "missing"}`}>
            {component?.available ? "Available" : "Unavailable"}
          </span>
        </div>
      ))}
      <div className="evidence-summary">
        <span>Recurrence: {risk.evidence_summary?.recurrence_level || "Unavailable"}</span>
        <span>Trend: {risk.evidence_summary?.trend || "Unavailable"}</span>
        <span>
          Severity index:{" "}
          {risk.evidence_summary?.severity_index_percent == null
            ? "Unavailable"
            : `${risk.evidence_summary.severity_index_percent.toFixed(1)}%`}
        </span>
      </div>
    </div>
  );
}

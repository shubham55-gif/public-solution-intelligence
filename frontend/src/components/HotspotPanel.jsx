import EvidencePanel from "./EvidencePanel";
import { riskBadge } from "../utils/mapping";

export default function HotspotPanel({
  hotspot,
  risk,
  recommendations,
  impact,
  onCreateIntervention,
}) {
  if (!hotspot) {
    return (
      <aside className="panel empty-panel">
        <p>Select a hotspot on the map to inspect its evidence.</p>
      </aside>
    );
  }

  const items = recommendations?.recommendations || [];
  return (
    <aside className="panel hotspot-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Selected hotspot</p>
          <h2>{String(hotspot.hotspot_id).slice(0, 12)}…</h2>
        </div>
        {risk && (
          <span className={`risk-badge ${riskBadge(risk.risk_level)}`}>
            {risk.risk_level}
          </span>
        )}
      </div>
      <div className="risk-score">
        <strong>{risk?.risk_score != null ? Number(risk.risk_score).toFixed(1) : "Unavailable"}</strong>
        <span>Explainable location-priority score / 100</span>
      </div>
      <dl className="detail-grid">
        <div><dt>Reports</dt><dd>{hotspot.report_count}</dd></div>
        <div><dt>Latitude</dt><dd>{Number(hotspot.latitude).toFixed(4)}</dd></div>
        <div><dt>Longitude</dt><dd>{Number(hotspot.longitude).toFixed(4)}</dd></div>
      </dl>
      <h3>Evidence</h3>
      <EvidencePanel risk={risk} />
      <h3>Recommendations</h3>
      {items.length ? (
        <ul className="recommendation-list">
          {items.map((item, index) => (
            <li key={`${item.action_type}-${index}`}>
              <strong>{item.action}</strong>
              <span>{item.priority} · {item.reason}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">Recommendations unavailable.</p>
      )}
      {items.length > 0 && (
        <button type="button" className="button button-primary" onClick={() => onCreateIntervention?.(recommendations)}>
          Create intervention
        </button>
      )}
      <h3>Impact</h3>
      {impact ? (
        <div className="impact-box">
          <span>Risk reduction</span>
          <strong>{Number(impact.risk_reduction_percent).toFixed(1)}%</strong>
          <span>Report reduction</span>
          <strong>{Number(impact.report_reduction_percent).toFixed(1)}%</strong>
        </div>
      ) : (
        <p className="muted">No impact measurement available.</p>
      )}
    </aside>
  );
}

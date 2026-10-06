function statusClass(value) {
  const map = {
    pending: "pending",
    in_progress: "in-progress",
    resolved: "resolved",
  };
  return map[String(value || "").toLowerCase()] || "";
}

function severityClass(value) {
  const s = String(value || "").toLowerCase();
  return ["low", "medium", "high", "critical"].includes(s) ? s : "";
}

function formatStatus(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ReportTable({ reports, error, loading, onSelectReport }) {
  if (loading) return <p className="muted">Loading reports&hellip;</p>;
  if (error) return <p className="error-text">Reports unavailable: {error}</p>;
  if (!reports?.items?.length)
    return <p className="muted" style={{ padding: "24px 0", textAlign: "center" }}>No reports match the current filters.</p>;

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Issue & ID</th>
            <th>Location</th>
            <th>Risk / Severity</th>
            <th>Status</th>
            <th>Evidence Status</th>
            <th>Reported Date</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {reports.items.map((report) => (
            <tr key={report.id}>
              <td title={report.id}>
                <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>{report.issue_category}</div>
                <code style={{ fontSize: "0.72rem", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
                  #{String(report.id).slice(0, 8)}
                </code>
              </td>
              <td style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                <span style={{ fontFamily: "var(--font-mono)" }}>
                  {Number(report.latitude).toFixed(4)}, {Number(report.longitude).toFixed(4)}
                </span>
              </td>
              <td>
                <span className={`status-pill ${severityClass(report.severity)}`}>
                  {report.severity ? report.severity.toUpperCase() : "STANDARD"}
                </span>
              </td>
              <td>
                <span className={`status-pill ${statusClass(report.status)}`}>
                  {formatStatus(report.status)}
                </span>
              </td>
              <td>
                {report.has_ai_analysis ? (
                  <span className="status-pill available">Verified</span>
                ) : (
                  <span className="status-pill missing">Not run</span>
                )}
              </td>
              <td style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                {new Date(report.reported_at).toLocaleDateString()}
              </td>
              <td>
                <button
                  type="button"
                  className="button button-secondary"
                  style={{ padding: "5px 10px", fontSize: "0.75rem", whiteSpace: "nowrap" }}
                  onClick={() => onSelectReport?.(report)}
                >
                  View Case →
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

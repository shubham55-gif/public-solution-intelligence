export default function SummaryCards({ reports, hotspots, risk, interventions }) {
  const reportItems = reports?.items || [];
  const riskItems = Array.isArray(risk) ? risk : [];
  const highRisk = riskItems.filter((item) =>
    ["high", "critical"].includes(String(item.risk_level).toLowerCase()),
  ).length;

  const total = reports?.total ?? reportItems.length;
  const pending = reportItems.filter((item) => item.status === "pending").length;
  const inProgress = reportItems.filter((item) => item.status === "in_progress").length;
  const resolved = reportItems.filter((item) => item.status === "resolved").length;
  const hotspotCount = Array.isArray(hotspots) ? hotspots.length : 0;

  const cards = [
    {
      id: "total",
      cls: "card-total",
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      ),
      label: "Total Reports",
      value: total,
      subtext: "All citizen submissions",
    },
    {
      id: "pending",
      cls: "card-pending",
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      ),
      label: "Pending",
      value: pending,
      subtext: "Awaiting authority action",
    },
    {
      id: "in_progress",
      cls: "card-progress",
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      ),
      label: "In Progress",
      value: inProgress,
      subtext: "Active field interventions",
    },
    {
      id: "resolved",
      cls: "card-resolved",
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
      ),
      label: "Resolved",
      value: resolved,
      subtext: "Completed & verified",
    },
    {
      id: "risk",
      cls: "card-risk",
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      ),
      label: "High / Critical Risk",
      value: highRisk > 0 ? highRisk : reportItems.filter(r => ["high", "critical"].includes(String(r.severity).toLowerCase())).length,
      subtext: "Immediate attention required",
    },
    {
      id: "hotspot",
      cls: "card-hotspot",
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
          <circle cx="12" cy="10" r="3" />
        </svg>
      ),
      label: "Active Hotspots",
      value: hotspotCount,
      subtext: "DBSCAN spatial clusters",
    },
  ];

  return (
    <section className="summary-grid" aria-label="Municipal command KPI summary">
      {cards.map((card) => (
        <article className={`summary-card ${card.cls}`} key={card.id}>
          <div className="summary-card-top">
            <span className="label">{card.label}</span>
            <div className="summary-card-icon">{card.icon}</div>
          </div>
          <div className="value">{card.value == null ? "—" : card.value}</div>
          <div className="subtext">{card.subtext}</div>
        </article>
      ))}
    </section>
  );
}

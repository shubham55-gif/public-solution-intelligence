import { useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { API_BASE_URL } from "./config/env";
import { useDashboardData } from "./hooks/useDashboardData";
import MapView from "./components/MapView";
import SummaryCards from "./components/SummaryCards";
import HotspotPanel from "./components/HotspotPanel";
import ReportTable from "./components/ReportTable";
import EvidencePanel from "./components/EvidencePanel";
import { mapHotspots, mapReports } from "./utils/mapping";

export function normalizeStatus(value = "") {
  return String(value || "").replace(/_/g, " ").trim().toLowerCase();
}

export function filterReports(reports = [], filters = {}) {
  const { category = "", status = "", severity = "", search = "" } = filters;
  const query = search.trim().toLowerCase();
  return reports.filter((report) => {
    if (category && report.issue_category !== category) return false;
    if (status && normalizeStatus(report.status) !== normalizeStatus(status)) return false;
    if (severity && normalizeStatus(report.severity) !== normalizeStatus(severity)) return false;
    if (
      query &&
      ![
        report.id,
        report.issue_category,
        report.description,
        report.status,
        report.severity,
        report.citizen_name,
        report.assigned_admin_name,
      ]
        .join(" ")
        .toLowerCase()
        .includes(query)
    )
      return false;
    return true;
  });
}

export function summarizeReports(items = []) {
  const summary = { pending: 0, in_progress: 0, resolved: 0 };
  items.forEach((report) => {
    const key = normalizeStatus(report.status).replace("in progress", "in_progress");
    if (key in summary) summary[key] += 1;
  });
  return summary;
}

function resolveImageUrl(imagePath) {
  if (!imagePath) return null;
  const clean = imagePath.replace(/^\/+/, "");
  return `${API_BASE_URL}/${clean}`;
}

function statusPillClass(status) {
  const map = { pending: "pending", in_progress: "in-progress", resolved: "resolved" };
  return map[String(status || "").toLowerCase()] || "available";
}

function fmtStatus(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function calculatePriority(report) {
  const sev = String(report.severity || "").toLowerCase();
  const isHighRisk = sev === "critical" || sev === "high";
  const isPending = report.status === "pending";

  if (sev === "critical" && isPending) return "CRITICAL";
  if (isHighRisk || report.is_duplicate) return "HIGH";
  if (sev === "medium" || isPending) return "MODERATE";
  return "LOW";
}

// Crisp Vector / SVG Icons (replacing all emojis)
const Icons = {
  Dashboard: () => (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>
  ),
  Priority: () => (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
  ),
  Reports: () => (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
  ),
  Map: () => (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>
  ),
  Ai: () => (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
  ),
  Hotspots: () => (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
  ),
  Analytics: () => (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
  ),
  Citizens: () => (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
  ),
  Admins: () => (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
  ),
  Notifications: () => (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
  ),
  Impact: () => (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
  ),
  Search: () => (
    <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
  ),
};

const NAV_SECTIONS = [
  { label: "Dashboard", id: "section-dashboard", icon: <Icons.Dashboard /> },
  { label: "Priority Queue", id: "section-priority", icon: <Icons.Priority /> },
  { label: "Reports", id: "section-reports", icon: <Icons.Reports /> },
  { label: "Live Map", id: "section-map", icon: <Icons.Map /> },
  { label: "AI Intelligence", id: "section-ai", icon: <Icons.Ai /> },
  { label: "Hotspots", id: "section-hotspots", icon: <Icons.Hotspots /> },
  { label: "Analytics", id: "section-analytics", icon: <Icons.Analytics /> },
  { label: "Citizens", id: "section-citizens", icon: <Icons.Citizens /> },
  { label: "Administrators", id: "section-admins", icon: <Icons.Admins /> },
  { label: "Notifications", id: "section-notifications", icon: <Icons.Notifications /> },
  { label: "Impact & Outcome", id: "section-impact", icon: <Icons.Impact /> },
];

export default function App() {
  const [filters, setFilters] = useState({ category: "", status: "", severity: "", search: "" });
  const [selectedReportId, setSelectedReportId] = useState(null);
  const [selectedHotspotId, setSelectedHotspotId] = useState(null);
  const [selectedCitizenId, setSelectedCitizenId] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [statusDraft, setStatusDraft] = useState("");
  const [resolutionNoteDraft, setResolutionNoteDraft] = useState("");
  const [statusError, setStatusError] = useState("");
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [aiResult, setAiResult] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  const [hotspotEvidence, setHotspotEvidence] = useState(null);
  const [hotspotLoading, setHotspotLoading] = useState(false);
  const [hotspotError, setHotspotError] = useState("");
  const [impact, setImpact] = useState(null);
  const [interventionForm, setInterventionForm] = useState(null);
  const [interventionSaving, setInterventionSaving] = useState(false);
  const [interventionError, setInterventionError] = useState("");
  const [activeSection, setActiveSection] = useState("section-dashboard");
  const [beforeImageError, setBeforeImageError] = useState(false);
  const [afterImageError, setAfterImageError] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [detectResult, setDetectResult] = useState(null);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const requestFilters = useMemo(
    () => Object.fromEntries(Object.entries(filters).filter(([, value]) => value)),
    [filters],
  );
  const data = useDashboardData(requestFilters, refreshKey);
  const reportPage = data.reports.value || { items: [], total: 0 };
  const allReports = reportPage.items || [];
  const filteredReports = useMemo(() => filterReports(allReports, filters), [allReports, filters]);
  const reports = mapReports({ items: filteredReports });
  const hotspots = mapHotspots(data.hotspots.value);
  const risk = Array.isArray(data.risk.value) ? data.risk.value : [];
  const riskById = useMemo(
    () => new Map(risk.map((item) => [String(item.hotspot_id), item])),
    [risk],
  );
  const selectedReport = allReports.find((item) => item.id === selectedReportId) || null;
  const selectedHotspot = hotspots.find(
    (item) => String(item.hotspot_id) === String(selectedHotspotId),
  );
  const selectedRisk = selectedHotspotId ? riskById.get(String(selectedHotspotId)) : null;
  const loading = Object.values(data).some((item) => item.loading);
  const connected = !data.reports.error;

  useEffect(() => {
    setStatusDraft(selectedReport?.status || "");
    setResolutionNoteDraft(selectedReport?.resolution_note || "");
    setBeforeImageError(false);
    setAfterImageError(false);
  }, [selectedReport?.id, selectedReport?.status, selectedReport?.resolution_note]);

  useEffect(() => {
    if (!selectedHotspotId) return undefined;
    let active = true;
    setHotspotLoading(true);
    setHotspotError("");
    setHotspotEvidence(null);
    setImpact(null);
    Promise.allSettled([
      api.hotspotRisk(selectedHotspotId),
      api.hotspotRecurrence(selectedHotspotId),
      api.hotspotTrend(selectedHotspotId),
      api.hotspotSeverity(selectedHotspotId),
      api.recommendation(selectedHotspotId),
      api.impact(selectedHotspotId),
    ]).then((results) => {
      if (!active) return;
      const [riskResult, recurrence, trend, severity, recommendation, impactResult] = results;
      setHotspotEvidence({
        risk: riskResult.status === "fulfilled" ? riskResult.value : null,
        recurrence: recurrence.status === "fulfilled" ? recurrence.value : null,
        trend: trend.status === "fulfilled" ? trend.value : null,
        severity: severity.status === "fulfilled" ? severity.value : null,
        recommendation: recommendation.status === "fulfilled" ? recommendation.value : null,
      });
      setImpact(impactResult.status === "fulfilled" ? impactResult.value : null);
      if (results.every((r) => r.status === "rejected"))
        setHotspotError("Unable to load hotspot evidence.");
      setHotspotLoading(false);
    });
    return () => {
      active = false;
    };
  }, [selectedHotspotId]);

  const selectReport = (report) => {
    setSelectedReportId(report.id);
    setAiResult(null);
    setAiError("");
  };

  useEffect(() => {
    if (!selectedReportId) return;
    let active = true;
    setAiLoading(true);
    setAiError("");
    api.getReportAnalysis(selectedReportId)
      .then((res) => {
        if (active) setAiResult(res);
      })
      .catch((err) => {
        if (active) {
          setAiResult(null);
          setAiError(err instanceof Error ? err.message : "AI analysis unavailable.");
        }
      })
      .finally(() => {
        if (active) setAiLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedReportId]);

  const updateStatus = async () => {
    if (!selectedReport) return;
    setStatusUpdating(true);
    setStatusError("");
    try {
      await api.updateReportStatus(selectedReport.id, statusDraft);
      setRefreshKey((v) => v + 1);
    } catch (error) {
      setStatusError(error instanceof Error ? error.message : "Unable to update report status.");
    } finally {
      setStatusUpdating(false);
    }
  };

  const analyzeReport = async () => {
    if (!selectedReport) return;
    setAiLoading(true);
    setAiError("");
    try {
      setAiResult(await api.analyzeReport(selectedReport.id));
      setRefreshKey((v) => v + 1);
    } catch (error) {
      setAiError(error instanceof Error ? error.message : "AI analysis unavailable.");
    } finally {
      setAiLoading(false);
    }
  };

  const createIntervention = async (event) => {
    event.preventDefault();
    setInterventionSaving(true);
    setInterventionError("");
    try {
      await api.createIntervention({
        hotspot_id: interventionForm.hotspot_id,
        action_type: interventionForm.action_type,
        description: interventionForm.description,
        status: "planned",
      });
      setInterventionForm(null);
      setRefreshKey((v) => v + 1);
    } catch (error) {
      setInterventionError(
        error instanceof Error ? error.message : "Unable to create intervention.",
      );
    } finally {
      setInterventionSaving(false);
    }
  };

  const detectHotspots = async () => {
    setDetecting(true);
    setDetectResult(null);
    try {
      const result = await api.detectHotspots();
      setDetectResult({ success: true, count: result.detected_hotspots_count });
      setRefreshKey((v) => v + 1);
    } catch (err) {
      setDetectResult({ success: false, error: err instanceof Error ? err.message : "Detection failed." });
    } finally {
      setDetecting(false);
    }
  };

  const scrollToSection = (sectionId) => {
    setActiveSection(sectionId);
    const el = document.getElementById(sectionId);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // Extract Citizens and Admins from real live data
  const citizensList = useMemo(() => {
    const map = new Map();
    allReports.forEach((r) => {
      const id = r.user_id || "unknown";
      if (!map.has(id)) {
        map.set(id, {
          id,
          name: r.citizen_name || "Citizen Reporter",
          reportsCount: 0,
          pendingCount: 0,
          inProgressCount: 0,
          resolvedCount: 0,
          latestCategory: r.issue_category,
          reports: [],
        });
      }
      const c = map.get(id);
      c.reportsCount++;
      c.reports.push(r);
      if (r.status === "pending") c.pendingCount++;
      if (r.status === "in_progress") c.inProgressCount++;
      if (r.status === "resolved") c.resolvedCount++;
    });
    return Array.from(map.values());
  }, [allReports]);

  const selectedCitizen = useMemo(() => {
    if (!selectedCitizenId) return null;
    return citizensList.find((c) => String(c.id) === String(selectedCitizenId)) || null;
  }, [citizensList, selectedCitizenId]);

  const adminsList = useMemo(() => {
    const map = new Map();
    allReports.forEach((r) => {
      const name = r.assigned_admin_name || r.resolved_by_admin_name;
      if (name) {
        if (!map.has(name)) {
          map.set(name, {
            name,
            role: "Municipal Operations Authority",
            assigned: 0,
            resolved: 0,
          });
        }
        const adm = map.get(name);
        if (r.assigned_admin_name === name) adm.assigned++;
        if (r.resolved_by_admin_name === name && r.status === "resolved") adm.resolved++;
      }
    });
    if (map.size === 0) {
      map.set("Admin Officer", {
        name: "Admin Officer",
        role: "Chief Municipal Operations",
        assigned: allReports.length,
        resolved: allReports.filter((r) => r.status === "resolved").length,
      });
    }
    return Array.from(map.values());
  }, [allReports]);

  // Priority Queue sorted list
  const priorityQueue = useMemo(() => {
    const order = { CRITICAL: 0, HIGH: 1, MODERATE: 2, LOW: 3 };
    return [...allReports]
      .filter((r) => r.status !== "resolved")
      .map((r) => ({ ...r, priorityLevel: calculatePriority(r) }))
      .sort((a, b) => order[a.priorityLevel] - order[b.priorityLevel]);
  }, [allReports]);

  // Dominant Top Priority Case
  const dominantCase = priorityQueue[0] || null;
  const remainingQueue = priorityQueue.slice(1);

  // Unresolved High Risk Count
  const criticalAttentionCount = priorityQueue.filter((r) =>
    ["CRITICAL", "HIGH"].includes(r.priorityLevel),
  ).length;

  return (
    <div className="app-shell">
      {/* ── Professional Sidebar ── */}
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-logo-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 21h18M5 21V7l7-4 7 4v14M9 10v11M15 10v11"/></svg>
          </div>
          <div className="brand-text">
            <p className="eyebrow">Public Solution Intelligence</p>
            <h2>Civic Connect</h2>
          </div>
        </div>
        <nav className="nav-list" aria-label="Dashboard navigation">
          {NAV_SECTIONS.map(({ label, id, icon }) => (
            <button
              type="button"
              className={`nav-item${activeSection === id ? " active" : ""}`}
              key={id}
              onClick={() => scrollToSection(id)}
            >
              {icon}
              <span>{label}</span>
              {id === "section-priority" && priorityQueue.length > 0 && (
                <span className="nav-badge">{priorityQueue.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="responsible-ai">
          <strong>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            Responsible AI Engine
          </strong>
          <p>Analyzing physical infrastructure hazards and spatial patterns with full accountability.</p>
        </div>
      </aside>

      {/* ── Content Shell ── */}
      <div className="content-shell">
        {/* Top Header */}
        <header className="topbar">
          <div className="topbar-brand">
            <h1>Civic Connect Operations Console</h1>
            <p className="subtitle">Real-Time Municipal Operations &amp; Evidence-Driven Prioritization</p>
          </div>
          <div className="header-actions">
            <div className="global-search">
              <Icons.Search />
              <input
                type="text"
                placeholder="Search cases, wards, citizens, admins…"
                value={filters.search}
                onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
              />
            </div>
            <div className={`status-pill ${connected ? "online" : "offline"}`}>
              <span className="dot" />
              {connected ? "PostgreSQL & AI Engine Online" : "System Offline"}
            </div>
            <div className="admin-profile-badge">
              <div className="admin-avatar">AO</div>
              <div className="admin-info">
                <span className="admin-name">Admin Officer</span>
                <span className="admin-role">Operations Authority</span>
              </div>
            </div>
            <button
              type="button"
              className="button button-primary"
              disabled={loading}
              onClick={() => setRefreshKey((v) => v + 1)}
            >
              {loading ? "Syncing…" : "Sync"}
            </button>
            <span style={{ fontSize: "0.74rem", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
              {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          </div>
        </header>

        <main>
          {/* ── 1. "What Needs Attention Now?" Operational Focus Zone ── */}
          <section className="operational-attention-zone" id="section-dashboard">
            <div className="attention-left">
              <div className="attention-header">
                {criticalAttentionCount > 0 ? (
                  <span className="attention-badge-alert">
                    {criticalAttentionCount} Critical / High Priority Issue{criticalAttentionCount !== 1 ? "s" : ""}
                  </span>
                ) : (
                  <span className="attention-badge-clear">Operational Queue Nominal</span>
                )}
                <span style={{ fontSize: "0.74rem", color: "var(--text-muted)" }}>
                  Live Status Assessment
                </span>
              </div>

              <h2 className="attention-title">
                {dominantCase
                  ? `Immediate Attention Required: ${dominantCase.issue_category}`
                  : "All current civic reports resolved or within acceptable response thresholds"}
              </h2>

              <p className="attention-desc">
                {dominantCase
                  ? `Case #${String(dominantCase.id).slice(0, 8)} elevated due to ${dominantCase.severity || "standard"} severity and pending dispatch. Immediate field inspection recommended.`
                  : "No critical infrastructure emergencies detected across active municipal wards."}
              </p>

              {dominantCase && (
                <div style={{ marginTop: "4px" }}>
                  <button
                    type="button"
                    className="button button-teal"
                    onClick={() => selectReport(dominantCase)}
                  >
                    Investigate Top Case →
                  </button>
                </div>
              )}
            </div>

            <div className="attention-right">
              <div className="metric-card-compact">
                <span className="m-label">Active Queue</span>
                <span className="m-val">{priorityQueue.length}</span>
                <span className="m-sub">Awaiting closure</span>
              </div>
              <div className="metric-card-compact">
                <span className="m-label">Hotspot Clusters</span>
                <span className="m-val">{hotspots.length}</span>
                <span className="m-sub">DBSCAN recurring</span>
              </div>
              <div className="metric-card-compact">
                <span className="m-label">Resolution Rate</span>
                <span className="m-val" style={{ color: "var(--resolved)" }}>
                  {allReports.length > 0
                    ? `${((allReports.filter((r) => r.status === "resolved").length / allReports.length) * 100).toFixed(0)}%`
                    : "100%"}
                </span>
                <span className="m-sub">Verified closed</span>
              </div>
            </div>
          </section>

          {/* ── Secondary Summary KPI Bar ── */}
          <SummaryCards
            reports={reportPage}
            hotspots={data.hotspots.value}
            risk={data.risk.value}
            interventions={data.interventions.value}
          />

          {/* ── Filter Bar ── */}
          <section className="filter-bar panel">
            <label>
              Category
              <select
                value={filters.category}
                onChange={(e) => setFilters((c) => ({ ...c, category: e.target.value }))}
              >
                <option value="">All Categories</option>
                <option>Road Damage</option>
                <option>Garbage Overflow</option>
                <option>Water Leakage</option>
                <option>Street Light Issue</option>
              </select>
            </label>
            <label>
              Status
              <select
                value={filters.status}
                onChange={(e) => setFilters((c) => ({ ...c, status: e.target.value }))}
              >
                <option value="">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
              </select>
            </label>
            <label>
              Severity
              <select
                value={filters.severity}
                onChange={(e) => setFilters((c) => ({ ...c, severity: e.target.value }))}
              >
                <option value="">All Severities</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </label>
          </section>

          {/* ── 2. Authority Priority Queue ── */}
          <section className="panel section-panel" id="section-priority">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Explainable Operations Signals</p>
                <h2>Authority Priority Queue</h2>
              </div>
              <span className="status-pill in-progress">
                {priorityQueue.length} Active Item{priorityQueue.length !== 1 ? "s" : ""}
              </span>
            </div>

            {dominantCase ? (
              <>
                {/* Visually Dominant Top Case Card */}
                <div className={`dominant-dispatch-card ${dominantCase.priorityLevel.toLowerCase()}`}>
                  <div className="dominant-left">
                    <div className="dominant-tags">
                      <span className={`status-pill ${dominantCase.priorityLevel.toLowerCase()}`}>
                        {dominantCase.priorityLevel} PRIORITY DISPATCH
                      </span>
                      <span className={`status-pill ${statusPillClass(dominantCase.status)}`}>
                        {fmtStatus(dominantCase.status)}
                      </span>
                      <code style={{ fontSize: "0.74rem", fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                        #{String(dominantCase.id).slice(0, 8)}
                      </code>
                    </div>
                    <h3 className="dominant-title">{dominantCase.issue_category}</h3>
                    <div className="dominant-meta">
                      <span>📍 Lat {Number(dominantCase.latitude).toFixed(4)}, Lng {Number(dominantCase.longitude).toFixed(4)}</span>
                      <span>• Reporter: {dominantCase.citizen_name || "Citizen"}</span>
                      <span>• Reported: {new Date(dominantCase.reported_at).toLocaleDateString()}</span>
                    </div>
                    <div className="dominant-rationale">
                      Operational Signal: Elevated due to {dominantCase.severity || "standard"} severity and pending field intervention.
                    </div>
                  </div>
                  <div className="dominant-right">
                    <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", textAlign: "right" }}>
                      Severity: <strong>{dominantCase.severity ? dominantCase.severity.toUpperCase() : "STANDARD"}</strong>
                    </div>
                    <button
                      type="button"
                      className="button button-primary"
                      style={{ padding: "8px 16px" }}
                      onClick={() => selectReport(dominantCase)}
                    >
                      Investigate &amp; Dispatch →
                    </button>
                  </div>
                </div>

                {/* Remaining Queue in Compact Scannable Table */}
                {remainingQueue.length > 0 && (
                  <div className="table-wrap">
                    <table className="queue-compact-table">
                      <thead>
                        <tr>
                          <th>Priority</th>
                          <th>Category &amp; ID</th>
                          <th>Location</th>
                          <th>Status</th>
                          <th>Severity</th>
                          <th>Reporter</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {remainingQueue.map((report) => (
                          <tr key={report.id}>
                            <td>
                              <span className={`status-pill ${report.priorityLevel.toLowerCase()}`}>
                                {report.priorityLevel}
                              </span>
                            </td>
                            <td>
                              <strong>{report.issue_category}</strong>
                              <code style={{ display: "block", fontSize: "0.7rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                                #{String(report.id).slice(0, 8)}
                              </code>
                            </td>
                            <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
                              {Number(report.latitude).toFixed(4)}, {Number(report.longitude).toFixed(4)}
                            </td>
                            <td>
                              <span className={`status-pill ${statusPillClass(report.status)}`}>
                                {fmtStatus(report.status)}
                              </span>
                            </td>
                            <td>{report.severity ? report.severity.toUpperCase() : "STANDARD"}</td>
                            <td style={{ color: "var(--text-secondary)", fontSize: "0.78rem" }}>
                              {report.citizen_name || "Citizen"}
                            </td>
                            <td>
                              <button
                                type="button"
                                className="button button-secondary"
                                style={{ padding: "4px 8px", fontSize: "0.74rem" }}
                                onClick={() => selectReport(report)}
                              >
                                View Case →
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            ) : (
              <p className="muted" style={{ padding: "16px 0", textAlign: "center" }}>
                All current reports are below the high-priority threshold or resolved.
              </p>
            )}
          </section>

          {/* ── 4. Live Municipal Command Map ── */}
          <section className="workspace-grid" id="section-map">
            <div className="panel map-panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">GIS Command Operations</p>
                  <h2>Live Municipal Issue Map</h2>
                  <p style={{ margin: "2px 0 0", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                    Reports, risk zones and recurring incidents
                  </p>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span style={{ display: "block", marginBottom: "6px", fontSize: "0.74rem", color: "var(--text-secondary)" }}>
                    {reports.length} Mapped Issue{reports.length !== 1 ? "s" : ""} · {hotspots.length} Spatial Cluster{hotspots.length !== 1 ? "s" : ""}
                  </span>
                  <button type="button" className="button button-teal" onClick={detectHotspots} disabled={detecting}>
                    {detecting ? "Running DBSCAN…" : "Detect Hotspots"}
                  </button>
                  {detectResult?.success && (
                    <span style={{ display: "block", fontSize: ".74rem", color: "var(--resolved)", marginTop: "3px", fontWeight: "bold" }}>
                      Detected {detectResult.count} active cluster(s).
                    </span>
                  )}
                </div>
              </div>
              <MapView
                reports={reports}
                hotspots={hotspots}
                riskById={riskById}
                onSelectReport={selectReport}
                onSelectHotspot={(id) => {
                  setSelectedHotspotId(id);
                  scrollToSection("section-hotspots");
                }}
              />
            </div>

            <div id="section-hotspots">
              <HotspotPanel
                hotspot={selectedHotspot}
                risk={hotspotEvidence?.risk || selectedRisk}
                recommendations={hotspotEvidence?.recommendation}
                impact={impact}
                onCreateIntervention={(recommendation) =>
                  setInterventionForm({
                    hotspot_id: selectedHotspotId,
                    action_type:
                      recommendation?.recommendations?.[0]?.action_type || "inspection",
                    description:
                      recommendation?.recommendations?.[0]?.action ||
                      "Inspect the selected hotspot.",
                  })
                }
              />
            </div>
          </section>

          {/* ── 3. All Civic Reports Operations Table ── */}
          <section className="panel section-panel" id="section-reports">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Case Management Directory</p>
                <h2>All Civic Reports</h2>
              </div>
              <span style={{ fontSize: "0.76rem", color: "var(--text-secondary)" }}>
                {filteredReports.length} records matching filters
              </span>
            </div>
            <ReportTable
              reports={{ items: filteredReports }}
              loading={data.reports.loading}
              error={data.reports.error}
              onSelectReport={selectReport}
            />
          </section>

          {/* ── 5. Evidence Intelligence (AI/VLM) ── */}
          <section className="panel section-panel" id="section-ai">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Multimodal Validation &amp; Hazard Detection</p>
                <h2>Evidence Intelligence</h2>
                <p style={{ margin: "2px 0 0", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                  AI decision-support verifying physical evidence and recommending field interventions.
                </p>
              </div>
            </div>
            <div className="spotlight-ai-grid">
              <div className="ai-intel-card">
                <h4>Image Validation</h4>
                <div className="intel-value" style={{ color: "var(--resolved)" }}>
                  Vision-Language Model
                </div>
                <div className="intel-desc">
                  Autonomous validation of visual evidence against reported category to eliminate false positives.
                </div>
              </div>
              <div className="ai-intel-card">
                <h4>Decision Signals</h4>
                <div className="intel-value" style={{ color: "var(--pending)" }}>
                  Multi-Factor Synthesis
                </div>
                <div className="intel-desc">
                  Risk score synthesis combining severity index, cluster proximity, and repeat frequency.
                </div>
              </div>
              <div className="ai-intel-card">
                <h4>Authority Recommendation</h4>
                <div className="intel-value" style={{ color: "var(--civic-teal)" }}>
                  Field Action Guidance
                </div>
                <div className="intel-desc">
                  Provides actionable recommendations to municipal supervisors before dispatching field teams.
                </div>
              </div>
            </div>
          </section>

          {/* ── 6. Citizen Stakeholder Directory ── */}
          <section className="panel section-panel" id="section-citizens">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Stakeholder Registry</p>
                <h2>Citizen Directory</h2>
                <p style={{ margin: "2px 0 0", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                  Verified citizen accounts with strict account isolation.
                </p>
              </div>
              <span className="status-pill available">{citizensList.length} Registered Citizen{citizensList.length !== 1 ? "s" : ""}</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px", marginBottom: "14px" }}>
              <div className="citizen-stat-box">
                <div className="num">{citizensList.length}</div>
                <div className="lbl">Total Citizens</div>
              </div>
              <div className="citizen-stat-box">
                <div className="num">{citizensList.filter((c) => c.reportsCount > 0).length}</div>
                <div className="lbl">Active Reporters</div>
              </div>
              <div className="citizen-stat-box">
                <div className="num">{allReports.length}</div>
                <div className="lbl">Total Reports</div>
              </div>
              <div className="citizen-stat-box">
                <div className="num">{allReports.filter((r) => r.status === "resolved").length}</div>
                <div className="lbl">Resolved Reports</div>
              </div>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Citizen Name</th>
                    <th>Identifier</th>
                    <th>Total Reports</th>
                    <th>Pending</th>
                    <th>In Progress</th>
                    <th>Resolved</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {citizensList.map((citizen) => (
                    <tr key={citizen.id}>
                      <td><strong>{citizen.name}</strong></td>
                      <td>
                        <code style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: "var(--text-secondary)" }}>
                          {String(citizen.id).slice(0, 8)}…
                        </code>
                      </td>
                      <td>{citizen.reportsCount}</td>
                      <td><span className="status-pill pending">{citizen.pendingCount}</span></td>
                      <td><span className="status-pill in-progress">{citizen.inProgressCount}</span></td>
                      <td><span className="status-pill resolved">{citizen.resolvedCount}</span></td>
                      <td>
                        <button
                          type="button"
                          className="button button-secondary"
                          style={{ padding: "4px 8px", fontSize: "0.74rem" }}
                          onClick={() => setSelectedCitizenId(citizen.id)}
                        >
                          View Profile →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* ── 7. Analytics & Incident Trends ── */}
          <section className="panel section-panel" id="section-analytics">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Temporal &amp; Cluster Analysis</p>
                <h2>Incident Trends &amp; Spatial Analytics</h2>
              </div>
            </div>
            {data.temporal.value ? (
              <div className="analytics-grid">
                <article>
                  <strong>Total Recorded Submissions</strong>
                  <p>{data.temporal.value.total_reports} Reports</p>
                </article>
                <article>
                  <strong>Peak Reporting Hour</strong>
                  <p>{data.temporal.value.peak_hour != null ? `${data.temporal.value.peak_hour}:00` : "Unavailable"}</p>
                </article>
                <article>
                  <strong>Active Incident Frequency</strong>
                  <p>{Number(data.temporal.value.current_report_frequency || 0).toFixed(2)} / day</p>
                </article>
                <article>
                  <strong>Frequency Trend Velocity</strong>
                  <p>{Number(data.temporal.value.frequency_change_percent || 0).toFixed(1)}%</p>
                </article>
                <article>
                  <strong>Resolution Rate</strong>
                  <p>
                    {allReports.length > 0
                      ? `${((allReports.filter((r) => r.status === "resolved").length / allReports.length) * 100).toFixed(0)}%`
                      : "0%"}
                  </p>
                </article>
                <article>
                  <strong>Active DBSCAN Clusters</strong>
                  <p>{hotspots.length} Identified</p>
                </article>
              </div>
            ) : (
              <p className="muted">Analytics aggregating from live database…</p>
            )}
          </section>

          {/* ── Administrators Workload ── */}
          <section className="panel section-panel" id="section-admins">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Municipal Accountability</p>
                <h2>Authority Officers &amp; Operational Workload</h2>
              </div>
              <span className="status-pill in-progress">{adminsList.length} Active Officer{adminsList.length !== 1 ? "s" : ""}</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Admin Officer</th>
                    <th>Role</th>
                    <th>Assigned Cases</th>
                    <th>Resolved Cases</th>
                    <th>Accountability State</th>
                  </tr>
                </thead>
                <tbody>
                  {adminsList.map((admin, idx) => (
                    <tr key={idx}>
                      <td><strong>{admin.name}</strong></td>
                      <td>{admin.role}</td>
                      <td>{admin.assigned}</td>
                      <td>{admin.resolved}</td>
                      <td><span className="status-pill available">Active Duty</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* ── Notifications Stream ── */}
          <section className="panel section-panel" id="section-notifications">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Operational Stream</p>
                <h2>Real-Time Event &amp; Status Stream</h2>
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {allReports.slice(0, 6).map((report) => (
                <div
                  key={report.id}
                  style={{
                    background: "var(--bg-surface-subtle)",
                    border: "1px solid var(--border-color)",
                    padding: "9px 12px",
                    borderRadius: "var(--radius-sm)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <strong>Report #{String(report.id).slice(0, 8)} ({report.issue_category})</strong>
                    <div style={{ fontSize: "0.76rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                      Status: <span className={`status-pill ${statusPillClass(report.status)}`} style={{ padding: "2px 6px" }}>{fmtStatus(report.status)}</span>
                      {" · "}Reported by {report.citizen_name || "Citizen"}
                    </div>
                  </div>
                  <button
                    type="button"
                    className="button button-secondary"
                    style={{ padding: "4px 8px", fontSize: "0.74rem" }}
                    onClick={() => selectReport(report)}
                  >
                    View
                  </button>
                </div>
              ))}
            </div>
          </section>

          {/* ── 8. Impact & Outcome Framework ── */}
          <section className="panel section-panel" id="section-impact">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Municipal Governance Framework</p>
                <h2>Report → Understand → Prioritize → Act → Measure</h2>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "10px", marginTop: "8px" }}>
              <div className="ai-intel-card">
                <h4>1. Report</h4>
                <div className="intel-value">{allReports.length} Submissions</div>
                <div className="intel-desc">Citizen geo-located mobile reports with photos.</div>
              </div>
              <div className="ai-intel-card">
                <h4>2. Understand</h4>
                <div className="intel-value">AI / VLM Analysis</div>
                <div className="intel-desc">Automated validation of visual and textual evidence.</div>
              </div>
              <div className="ai-intel-card">
                <h4>3. Prioritize</h4>
                <div className="intel-value">Risk &amp; DBSCAN</div>
                <div className="intel-desc">Multi-factor risk score and spatial recurrence detection.</div>
              </div>
              <div className="ai-intel-card">
                <h4>4. Act</h4>
                <div className="intel-value">Field Interventions</div>
                <div className="intel-desc">Authority assignment, status dispatch, and repair.</div>
              </div>
              <div className="ai-intel-card">
                <h4>5. Measure</h4>
                <div className="intel-value">{allReports.filter((r) => r.status === "resolved").length} Verified</div>
                <div className="intel-desc">Side-by-side Before/After evidence and citizen updates.</div>
              </div>
            </div>
          </section>
        </main>

        <footer>
          Civic Connect · Public Solution Intelligence Platform · Technathon Final Round
        </footer>
      </div>

      {/* ── Citizen Profile Modal (Strict Isolation) ── */}
      {selectedCitizen && (
        <aside className="drawer-backdrop" onClick={() => setSelectedCitizenId(null)}>
          <div className="report-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div>
                <p className="eyebrow">Citizen Stakeholder Profile</p>
                <h3>{selectedCitizen.name}</h3>
                <code style={{ fontSize: "0.74rem", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
                  ID: {selectedCitizen.id}
                </code>
              </div>
              <button
                type="button"
                className="close-button"
                onClick={() => setSelectedCitizenId(null)}
              >
                ✕
              </button>
            </div>

            <div className="citizen-stats-row">
              <div className="citizen-stat-box">
                <div className="num">{selectedCitizen.reportsCount}</div>
                <div className="lbl">Total</div>
              </div>
              <div className="citizen-stat-box">
                <div className="num">{selectedCitizen.pendingCount}</div>
                <div className="lbl">Pending</div>
              </div>
              <div className="citizen-stat-box">
                <div className="num">{selectedCitizen.inProgressCount}</div>
                <div className="lbl">In Progress</div>
              </div>
              <div className="citizen-stat-box">
                <div className="num">{selectedCitizen.resolvedCount}</div>
                <div className="lbl">Resolved</div>
              </div>
            </div>

            <div>
              <h4 style={{ margin: "0 0 8px", fontSize: "0.84rem", textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-secondary)" }}>
                Citizen's Submitted Reports ({selectedCitizen.reports.length})
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {selectedCitizen.reports.map((rep) => (
                  <div
                    key={rep.id}
                    style={{
                      background: "var(--bg-surface-subtle)",
                      border: "1px solid var(--border-color)",
                      padding: "9px 12px",
                      borderRadius: "var(--radius-sm)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700, fontSize: "0.84rem" }}>{rep.issue_category}</div>
                      <div style={{ fontSize: "0.74rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                        📍 {Number(rep.latitude).toFixed(4)}, {Number(rep.longitude).toFixed(4)}
                        {" · "}{new Date(rep.reported_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span className={`status-pill ${statusPillClass(rep.status)}`}>
                        {fmtStatus(rep.status)}
                      </span>
                      <button
                        type="button"
                        className="button button-secondary"
                        style={{ padding: "4px 8px", fontSize: "0.74rem" }}
                        onClick={() => {
                          setSelectedCitizenId(null);
                          selectReport(rep);
                        }}
                      >
                        Investigate →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {selectedCitizen.reports.filter((r) => r.status === "resolved").length > 0 && (
              <div>
                <h4 style={{ margin: "0 0 8px", fontSize: "0.84rem", textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--resolved)" }}>
                  Resolution History
                </h4>
                {selectedCitizen.reports
                  .filter((r) => r.status === "resolved")
                  .map((rep) => (
                    <div key={rep.id} className="resolution-summary-card" style={{ marginBottom: "8px" }}>
                      <div className="title">Case #{String(rep.id).slice(0, 8)} — {rep.issue_category}</div>
                      <div className="item">
                        <strong>Resolved By:</strong> {rep.resolved_by_admin_name || "Municipal Officer"}
                      </div>
                      <div className="item">
                        <strong>Resolution Date:</strong> {rep.resolved_at ? new Date(rep.resolved_at).toLocaleString() : "Confirmed"}
                      </div>
                      <div className="item">
                        <strong>Resolution Note:</strong> {rep.resolution_note || "Resolved successfully."}
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </aside>
      )}

      {/* ── 9. Case Investigation Drawer (Modal) ── */}
      {selectedReport && (
        <aside className="drawer-backdrop" onClick={() => setSelectedReportId(null)}>
          <div className="report-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div>
                <p className="eyebrow">Case Investigation &amp; Evidence Audit</p>
                <h3>{selectedReport.issue_category}</h3>
                <code style={{ fontSize: "0.74rem", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
                  UUID: {selectedReport.id}
                </code>
              </div>
              <button
                type="button"
                className="close-button"
                onClick={() => setSelectedReportId(null)}
              >
                ✕
              </button>
            </div>

            {/* Status & Priority Pills */}
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <span className={`status-pill ${statusPillClass(selectedReport.status)}`}>
                Status: {fmtStatus(selectedReport.status)}
              </span>
              <span className={`status-pill ${selectedReport.severity || "standard"}`}>
                Severity: {selectedReport.severity ? selectedReport.severity.toUpperCase() : "STANDARD"}
              </span>
              <span className="status-pill in-progress">
                Priority: {calculatePriority(selectedReport)}
              </span>
            </div>

            {/* Metadata */}
            <dl className="drawer-grid">
              <div>
                <dt>Citizen Reporter</dt>
                <dd>{selectedReport.citizen_name || "Citizen Reporter"}</dd>
              </div>
              <div>
                <dt>Reported Timestamp</dt>
                <dd>{new Date(selectedReport.reported_at).toLocaleString()}</dd>
              </div>
              <div>
                <dt>Latitude Coordinate</dt>
                <dd style={{ fontFamily: "var(--font-mono)" }}>{Number(selectedReport.latitude).toFixed(6)}</dd>
              </div>
              <div>
                <dt>Longitude Coordinate</dt>
                <dd style={{ fontFamily: "var(--font-mono)" }}>{Number(selectedReport.longitude).toFixed(6)}</dd>
              </div>
            </dl>

            {/* Description */}
            <div style={{ background: "var(--bg-surface-subtle)", padding: "10px 12px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-color)" }}>
              <dt style={{ fontSize: "0.66rem", fontWeight: "700", textTransform: "uppercase", color: "var(--text-secondary)", marginBottom: "2px" }}>
                Incident Description
              </dt>
              <dd style={{ margin: 0, fontSize: "0.82rem", color: "var(--text-primary)" }}>
                {selectedReport.description || "No written description provided."}
              </dd>
            </div>

            {/* Side-by-side Evidence Photos */}
            <div>
              <h4 style={{ margin: "0 0 6px", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-secondary)" }}>
                Photographic Evidence Verification
              </h4>
              <div className="evidence-photos-grid">
                <div className="evidence-photo-box">
                  <label>BEFORE (Citizen Evidence)</label>
                  {selectedReport.image_path && !beforeImageError ? (
                    <img
                      src={resolveImageUrl(selectedReport.image_path)}
                      alt="Before evidence"
                      className="report-image"
                      onError={() => setBeforeImageError(true)}
                    />
                  ) : (
                    <div className="image-missing">
                      {selectedReport.image_path ? "Before photo could not be loaded." : "No photo submitted by citizen."}
                    </div>
                  )}
                </div>
                <div className="evidence-photo-box">
                  <label>AFTER (Authority Resolution)</label>
                  {selectedReport.resolution_image_path && !afterImageError ? (
                    <img
                      src={resolveImageUrl(selectedReport.resolution_image_path)}
                      alt="After resolution evidence"
                      className="report-image"
                      onError={() => setAfterImageError(true)}
                    />
                  ) : (
                    <div className="image-missing">
                      {selectedReport.status === "resolved" ? "After-resolution evidence not provided." : "Pending resolution by authority."}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Verified Resolution Summary or Status Controls */}
            {selectedReport.status === "resolved" ? (
              <div className="resolution-summary-card">
                <div className="title">RESOLVED CASE</div>
                <div className="item">
                  <strong>Resolved By:</strong> {selectedReport.resolved_by_admin_name || "Municipal Authority"}
                </div>
                <div className="item">
                  <strong>Resolved At:</strong> {selectedReport.resolved_at ? new Date(selectedReport.resolved_at).toLocaleString() : "Confirmed"}
                </div>
                <div className="item">
                  <strong>Resolution Note:</strong> {selectedReport.resolution_note || "Issue resolved and verified."}
                </div>
              </div>
            ) : (
              <div style={{ background: "var(--bg-surface-subtle)", padding: "12px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-color)" }}>
                <h4 style={{ margin: "0 0 8px", fontSize: "0.8rem" }}>Authority Status Action</h4>
                {statusError && <p className="error-text">{statusError}</p>}
                <div style={{ display: "flex", gap: "8px" }}>
                  <select
                    value={statusDraft}
                    onChange={(e) => setStatusDraft(e.target.value)}
                    disabled={statusUpdating}
                    style={{ flex: 1 }}
                  >
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="resolved">Resolved</option>
                  </select>
                  <button
                    type="button"
                    className="button button-primary"
                    onClick={updateStatus}
                    disabled={statusUpdating || statusDraft === selectedReport.status}
                  >
                    {statusUpdating ? "Applying…" : "Update Status"}
                  </button>
                </div>
              </div>
            )}

            {/* Evidence Intelligence (AI/VLM) */}
            <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <h4 style={{ margin: 0, fontSize: "0.8rem" }}>Evidence Intelligence (AI / VLM)</h4>
                <button
                  type="button"
                  className="button button-secondary"
                  style={{ padding: "3px 8px", fontSize: "0.72rem" }}
                  onClick={analyzeReport}
                  disabled={aiLoading}
                >
                  {aiLoading ? "Analyzing…" : aiResult ? "Re-evaluate" : "Run AI Analysis"}
                </button>
              </div>
              {aiError && <p className="error-text">{aiError}</p>}
              {aiResult && (
                <div style={{ background: "var(--bg-surface-subtle)", padding: "10px", borderRadius: "var(--radius-sm)", fontSize: "0.76rem", display: "flex", flexDirection: "column", gap: "5px" }}>
                  <div><strong>Summary:</strong> {aiResult.text_analysis?.summary || "Analysis evaluated."}</div>
                  <div><strong>Keywords:</strong> {(aiResult.text_analysis?.keywords || []).join(", ") || "Standard"}</div>
                  <div><strong>Image Consistent:</strong> {aiResult.image_analysis?.validation_result || "Not checked"}</div>
                  <div><strong>Needs Review:</strong> {aiResult.overall_needs_review ? "YES" : "NO"}</div>
                </div>
              )}
            </div>
          </div>
        </aside>
      )}

      {/* ── Create Intervention Drawer ── */}
      {interventionForm && (
        <aside className="drawer-backdrop" onClick={() => setInterventionForm(null)}>
          <form
            className="report-drawer"
            style={{ width: "min(460px, 95vw)" }}
            onSubmit={createIntervention}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="drawer-header">
              <h3>Create Field Intervention</h3>
              <button
                type="button"
                className="close-button"
                onClick={() => setInterventionForm(null)}
              >
                ✕
              </button>
            </div>
            <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.76rem", fontWeight: "700" }}>
              Action Type
              <input
                value={interventionForm.action_type}
                onChange={(e) => setInterventionForm({ ...interventionForm, action_type: e.target.value })}
                required
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.76rem", fontWeight: "700" }}>
              Description &amp; Protocol
              <textarea
                value={interventionForm.description}
                onChange={(e) => setInterventionForm({ ...interventionForm, description: e.target.value })}
                required
                style={{ minHeight: "80px" }}
              />
            </label>
            {interventionError && <p className="error-text">{interventionError}</p>}
            <button
              type="submit"
              className="button button-primary"
              disabled={interventionSaving}
            >
              {interventionSaving ? "Creating…" : "Schedule Intervention"}
            </button>
          </form>
        </aside>
      )}
    </div>
  );
}

import { API_BASE_URL, DEVELOPMENT_USER_ID } from "../config/env";

export function buildHeaders() {
  return DEVELOPMENT_USER_ID
    ? { "X-Development-User-Id": DEVELOPMENT_USER_ID }
    : {};
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...buildHeaders(),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let detail = `Request failed with HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // Keep the HTTP status when the server did not return JSON.
    }
    throw new Error(detail);
  }

  return response.json();
}

export const api = {
  reports: (params = {}) => {
    const query = new URLSearchParams({ page: "1", page_size: "100", ...params });
    return request(`/api/v1/reports?${query.toString()}`);
  },
  hotspots: () => request("/api/v1/analytics/hotspots"),
  detectHotspots: () => request("/api/v1/analytics/hotspots/detect", { method: "POST" }),
  risk: () => request("/api/v1/analytics/risk"),
  recommendations: () => request("/api/v1/recommendations"),
  interventions: (params = {}) => {
    const query = new URLSearchParams({ page: "1", page_size: "100", ...params });
    return request(`/api/v1/interventions?${query.toString()}`);
  },
  impact: (hotspotId) => request(`/api/v1/impact/${hotspotId}`),
  updateReportStatus: (reportId, status) =>
    request(`/api/v1/admin/reports/${reportId}/status`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status }),
    }),
  analyzeReport: (reportId) =>
    request(`/api/v1/ai/analyze-report/${reportId}`, { method: "POST" }),
  getReportAnalysis: (reportId) =>
    request(`/api/v1/ai/analyze-report/${reportId}`),
  hotspotRisk: (hotspotId) => request(`/api/v1/analytics/risk/${hotspotId}`),
  hotspotRecurrence: (hotspotId) =>
    request(`/api/v1/analytics/recurrence/${hotspotId}`),
  hotspotTrend: (hotspotId) =>
    request(`/api/v1/analytics/trend/${hotspotId}`),
  hotspotSeverity: (hotspotId) =>
    request(`/api/v1/analytics/severity/${hotspotId}`),
  temporal: () => request("/api/v1/analytics/temporal"),
  recommendation: (hotspotId) =>
    request(`/api/v1/recommendations/${hotspotId}`),
  createIntervention: (payload) =>
    request("/api/v1/interventions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  updateIntervention: (id, payload) =>
    request(`/api/v1/interventions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  interventionImpact: (id) =>
    request(`/api/v1/impact/interventions/${id}/impact`),
  snapshotImpact: (hotspotId, payload = {}) =>
    request(`/api/v1/impact/${hotspotId}/snapshot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  measureImpact: (hotspotId, payload) =>
    request(`/api/v1/impact/${hotspotId}/measure`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
};

export { request };

export function validCoordinate(latitude, longitude) {
  return (
    latitude !== null &&
    latitude !== undefined &&
    longitude !== null &&
    longitude !== undefined &&
    latitude !== "" &&
    longitude !== "" &&
    Number.isFinite(Number(latitude)) &&
    Number.isFinite(Number(longitude)) &&
    Number(latitude) >= -90 &&
    Number(latitude) <= 90 &&
    Number(longitude) >= -180 &&
    Number(longitude) <= 180
  );
}

export function mapReports(page) {
  return Array.isArray(page?.items)
    ? page.items.filter((report) =>
        validCoordinate(report.latitude, report.longitude),
      )
    : [];
}

export function mapHotspots(hotspots) {
  return Array.isArray(hotspots)
    ? hotspots.filter((hotspot) =>
        validCoordinate(hotspot.latitude, hotspot.longitude),
      )
    : [];
}

export function riskBadge(level = "") {
  const normalized = String(level).toLowerCase();
  return ["low", "moderate", "high", "critical"].includes(normalized)
    ? normalized
    : "unavailable";
}

export function evidenceRows(risk) {
  const components = risk?.components || {};
  return [
    ["Spatial", components.spatial],
    ["Temporal", components.temporal],
    ["Recurrence", components.recurrence],
    ["Trend", components.trend],
    ["Severity", components.severity],
    ["Related reports", components.related_reports],
  ];
}

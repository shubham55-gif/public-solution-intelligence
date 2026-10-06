import { useEffect, useState } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";

const DEFAULT_INDIA_CENTER = [20.5937, 78.9629];

function MapInvalidator() {
  const map = useMap();
  useEffect(() => {
    map.invalidateSize();
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 250);
    return () => clearTimeout(timer);
  }, [map]);
  return null;
}

function FitToData({ reports = [], hotspots = [] }) {
  const map = useMap();

  useEffect(() => {
    const points = [
      ...reports.map((r) => [Number(r.latitude), Number(r.longitude)]),
      ...hotspots.map((h) => [Number(h.latitude), Number(h.longitude)]),
    ].filter(
      ([lat, lng]) =>
        !isNaN(lat) &&
        !isNaN(lng) &&
        lat >= -90 &&
        lat <= 90 &&
        lng >= -180 &&
        lng <= 180 &&
        !(lat === 0 && lng === 0),
    );

    if (points.length > 0) {
      map.fitBounds(points, { padding: [40, 40], maxZoom: 13 });
    } else {
      map.setView(DEFAULT_INDIA_CENTER, 4);
    }
  }, [hotspots, map, reports]);

  return null;
}

// Android-unified marker colors matching MapsActivity.java
export function getReportMarkerColor(report) {
  const status = String(report?.status || "").toLowerCase().replace(/_/g, " ");
  const severity = String(report?.severity || "").toLowerCase();

  if (severity === "high" || severity === "critical") {
    return { color: "#c2410c", fillColor: "#ea580c", fillOpacity: 0.85 }; // Orange / High-risk
  }
  if (status === "resolved") {
    return { color: "#15803d", fillColor: "#16a34a", fillOpacity: 0.85 }; // Green
  }
  if (status === "in progress") {
    return { color: "#b45309", fillColor: "#d97706", fillOpacity: 0.85 }; // Amber/Yellow
  }
  return { color: "#b91c1c", fillColor: "#dc2626", fillOpacity: 0.85 }; // Red (Pending)
}

export function riskColor(level) {
  const lvl = String(level || "").toLowerCase();
  if (lvl === "critical") return "#b42318";
  if (lvl === "high") return "#ea580c";
  if (lvl === "moderate") return "#2563eb";
  if (lvl === "low") return "#16803c";
  return "#64748b";
}

export default function MapView({
  reports = [],
  hotspots = [],
  riskById = new Map(),
  onSelectHotspot,
  onSelectReport,
}) {
  const [showReports, setShowReports] = useState(true);
  const [showHotspots, setShowHotspots] = useState(true);
  const [showRiskOverlay, setShowRiskOverlay] = useState(true);

  // Clean and filter reports & hotspots with valid coordinates
  const validReports = reports.filter((r) => {
    const lat = Number(r?.latitude);
    const lng = Number(r?.longitude);
    return !isNaN(lat) && !isNaN(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180 && !(lat === 0 && lng === 0);
  });

  const validHotspots = hotspots.filter((h) => {
    const lat = Number(h?.latitude);
    const lng = Number(h?.longitude);
    return !isNaN(lat) && !isNaN(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180 && !(lat === 0 && lng === 0);
  });

  return (
    <div className="map-container">
      {/* Map layer toggle bar */}
      <div className="map-layer-controls">
        <label>
          <input
            type="checkbox"
            checked={showReports}
            onChange={(e) => setShowReports(e.target.checked)}
          />
          Reports ({validReports.length})
        </label>
        <label>
          <input
            type="checkbox"
            checked={showHotspots}
            onChange={(e) => setShowHotspots(e.target.checked)}
          />
          Hotspots ({validHotspots.length})
        </label>
        <label>
          <input
            type="checkbox"
            checked={showRiskOverlay}
            onChange={(e) => setShowRiskOverlay(e.target.checked)}
          />
          Risk Heat
        </label>
      </div>

      <MapContainer
        className="map"
        center={DEFAULT_INDIA_CENTER}
        zoom={4}
        scrollWheelZoom
        style={{ height: "100%", width: "100%", minHeight: "540px" }}
      >
        <MapInvalidator />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitToData reports={validReports} hotspots={validHotspots} />

        {/* Report Markers */}
        {showReports &&
          validReports.map((report) => {
            const style = getReportMarkerColor(report);
            return (
              <CircleMarker
                key={`report-${report.id}`}
                center={[Number(report.latitude), Number(report.longitude)]}
                radius={7}
                pathOptions={{
                  color: style.color,
                  fillColor: style.fillColor,
                  fillOpacity: style.fillOpacity,
                  weight: 2,
                }}
                eventHandlers={{
                  click: () => onSelectReport?.(report),
                }}
              >
                <Popup>
                  <div className="map-popup-content">
                    <strong>{report.issue_category}</strong>
                    <div style={{ margin: "4px 0" }}>
                      <span className={`status-pill ${report.status}`}>{report.status}</span>{" "}
                      <span className={`status-pill ${report.severity}`}>{report.severity}</span>
                    </div>
                    <p style={{ margin: "4px 0", fontSize: ".82rem" }}>
                      {report.description ? report.description.slice(0, 80) : "No description"}
                    </p>
                    <button
                      type="button"
                      className="popup-link"
                      style={{ marginTop: "6px", display: "inline-block" }}
                      onClick={() => onSelectReport?.(report)}
                    >
                      Open Report Investigation &rarr;
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}

        {/* Hotspot Markers */}
        {showHotspots &&
          validHotspots.map((hotspot) => {
            const risk = riskById.get(String(hotspot.hotspot_id));
            const color = showRiskOverlay ? riskColor(risk?.risk_level) : "#d97706";
            return (
              <CircleMarker
                key={`hotspot-${hotspot.hotspot_id}`}
                center={[Number(hotspot.latitude), Number(hotspot.longitude)]}
                radius={Math.max(12, Math.min(28, 10 + (hotspot.report_count || 1) * 2))}
                pathOptions={{
                  color: color,
                  fillColor: color,
                  fillOpacity: 0.35,
                  weight: 3,
                }}
                eventHandlers={{ click: () => onSelectHotspot?.(hotspot.hotspot_id) }}
              >
                <Popup>
                  <div className="map-popup-content">
                    <strong>Active Hotspot</strong>
                    <p style={{ margin: "4px 0", fontSize: ".85rem" }}>
                      Report count: <strong>{hotspot.report_count}</strong>
                    </p>
                    <p style={{ margin: "4px 0", fontSize: ".85rem" }}>
                      Risk: <strong>{risk ? `${risk.risk_score}/100 (${risk.risk_level})` : "Calculated"}</strong>
                    </p>
                    <button
                      type="button"
                      className="popup-link"
                      style={{ marginTop: "6px", display: "inline-block" }}
                      onClick={() => onSelectHotspot?.(hotspot.hotspot_id)}
                    >
                      View Hotspot Intelligence &rarr;
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
      </MapContainer>

      {/* Map Legend matching Android app */}
      <div className="map-legend">
        <div className="legend-title">Operational Map Legend</div>
        <div className="legend-grid">
          <div className="legend-item"><span className="legend-dot" style={{ background: "#dc2626" }} /> Pending</div>
          <div className="legend-item"><span className="legend-dot" style={{ background: "#d97706" }} /> In Progress</div>
          <div className="legend-item"><span className="legend-dot" style={{ background: "#16a34a" }} /> Resolved</div>
          <div className="legend-item"><span className="legend-dot" style={{ background: "#ea580c" }} /> High Risk</div>
          <div className="legend-item"><span className="legend-circle" /> Hotspot Area</div>
        </div>
      </div>
    </div>
  );
}

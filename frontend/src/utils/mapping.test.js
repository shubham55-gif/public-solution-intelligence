import { describe, expect, it } from "vitest";
import { evidenceRows, mapHotspots, mapReports, riskBadge, validCoordinate } from "./mapping";

describe("dashboard mapping helpers", () => {
  it("rejects invalid coordinates", () => {
    expect(validCoordinate(28.6, 77.2)).toBe(true);
    expect(validCoordinate(null, 77.2)).toBe(false);
    expect(validCoordinate(NaN, 77.2)).toBe(false);
    expect(validCoordinate(91, 77.2)).toBe(false);
    expect(validCoordinate(28.6, Infinity)).toBe(false);
  });

  it("maps only report and hotspot records with valid coordinates", () => {
    expect(mapReports({ items: [{ id: "1", latitude: 28, longitude: 77 }, { id: "2", latitude: null, longitude: 77 }] })).toHaveLength(1);
    expect(mapHotspots([{ hotspot_id: "1", latitude: 28, longitude: 77 }, { hotspot_id: "2", latitude: 200, longitude: 77 }])).toHaveLength(1);
  });

  it("maps known risk levels and preserves unavailable state", () => {
    expect(riskBadge("CRITICAL")).toBe("critical");
    expect(riskBadge("not-known")).toBe("unavailable");
  });

  it("returns all evidence components without inventing missing values", () => {
    const rows = evidenceRows({ components: { spatial: { available: false } } });
    expect(rows).toHaveLength(6);
    expect(rows[0][1].available).toBe(false);
  });
});

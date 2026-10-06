import { describe, expect, it, vi } from "vitest";

vi.mock("../config/env", () => ({
  API_BASE_URL: "http://api.test",
  DEVELOPMENT_USER_ID: "authority-user",
}));

import { api, buildHeaders } from "./client";

describe("API client", () => {
  it("builds the centralized development-user header", () => {
    expect(buildHeaders()).toEqual({ "X-Development-User-Id": "authority-user" });
  });

  it("sends the header for API requests", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [] }),
    });
    await api.reports();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/reports"),
      expect.objectContaining({
        headers: expect.objectContaining({ "X-Development-User-Id": "authority-user" }),
      }),
    );
  });

  it("surfaces API errors instead of fabricating data", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: "Unavailable" }),
    });
    await expect(api.hotspots()).rejects.toThrow("Unavailable");
  });

  it("keeps authority mutations centralized", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ report_id: "report-1", analysis_available: false }),
    });
    await api.analyzeReport("report-1");
    expect(global.fetch).toHaveBeenCalledWith(
      "http://api.test/api/v1/ai/analyze-report/report-1",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

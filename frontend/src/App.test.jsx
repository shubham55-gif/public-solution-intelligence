import { describe, expect, it } from "vitest";
import { filterReports, summarizeReports } from "./App";

describe("dashboard core helpers", () => {
  it("filters real report data without inventing values", () => {
    const reports = [
      {
        id: "1",
        issue_category: "Road Damage",
        description: "Pothole near the school",
        severity: "low",
        status: "pending",
      },
      {
        id: "2",
        issue_category: "Garbage Overflow",
        description: "Overflow near market",
        severity: "high",
        status: "in_progress",
      },
      {
        id: "3",
        issue_category: "Water Leakage",
        description: "Leak under bridge",
        severity: "critical",
        status: "resolved",
      },
    ];

    expect(filterReports(reports, { category: "Road Damage" })).toHaveLength(1);
    expect(filterReports(reports, { status: "in_progress" })).toHaveLength(1);
    expect(filterReports(reports, { severity: "high" })).toHaveLength(1);
    expect(filterReports(reports, { search: "bridge" })).toHaveLength(1);
  });

  it("summarizes report status counts from the backend data", () => {
    const summary = summarizeReports([
      { status: "pending" },
      { status: "in_progress" },
      { status: "pending" },
      { status: "resolved" },
    ]);

    expect(summary).toEqual({ pending: 2, in_progress: 1, resolved: 1 });
  });
});

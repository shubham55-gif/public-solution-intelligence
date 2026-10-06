import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it, vi } from "vitest";
import ReportTable from "./ReportTable";

describe("ReportTable", () => {
  it("renders reports and triggers selection when the user clicks View", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    const onSelectReport = vi.fn();

    await act(async () => {
      root.render(
        <ReportTable
          reports={{
            items: [
              {
                id: "report-1",
                issue_category: "Road Damage",
                severity: "high",
                status: "pending",
                reported_at: "2026-09-19T08:00:00+05:30",
                latitude: 19.08,
                longitude: 72.88,
              },
            ],
            total: 1,
          }}
          loading={false}
          error={null}
          onSelectReport={onSelectReport}
        />,
      );
    });

    expect(container.textContent).toContain("Road Damage");
    expect(container.textContent).toContain("Not run");

    const button = container.querySelector("button");
    await act(async () => {
      button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(onSelectReport).toHaveBeenCalledWith(
      expect.objectContaining({ id: "report-1", issue_category: "Road Damage" }),
    );

    root.unmount();
    container.remove();
  });
});

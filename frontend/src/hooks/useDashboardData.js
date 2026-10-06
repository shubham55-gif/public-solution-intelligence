import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

const initialState = {
  reports: { value: null, error: null, loading: true },
  hotspots: { value: null, error: null, loading: true },
  risk: { value: null, error: null, loading: true },
  recommendations: { value: null, error: null, loading: true },
  interventions: { value: null, error: null, loading: true },
  temporal: { value: null, error: null, loading: true },
};

export function useDashboardData(filters, refreshKey = 0) {
  const [state, setState] = useState(initialState);

  useEffect(() => {
    let active = true;
    const load = async (key, loader) => {
      setState((current) => ({
        ...current,
        [key]: { value: current[key]?.value ?? null, error: null, loading: true },
      }));
      try {
        const value = await loader();
        if (active) {
          setState((current) => ({
            ...current,
            [key]: { value, error: null, loading: false },
          }));
        }
      } catch (error) {
        if (active) {
          setState((current) => ({
            ...current,
            [key]: {
              value: current[key]?.value ?? null,
              error: error instanceof Error ? error.message : "Unavailable",
              loading: false,
            },
          }));
        }
      }
    };

    load("reports", () => api.reports(filters));
    load("hotspots", api.hotspots);
    load("risk", api.risk);
    load("recommendations", api.recommendations);
    load("interventions", api.interventions);
    load("temporal", api.temporal);

    return () => {
      active = false;
    };
  }, [filters, refreshKey]);

  return useMemo(() => state, [state]);
}

# Public Solution Intelligence Authority Command Center

This is the React + Leaflet read-only authority dashboard foundation for PS12.
It consumes the existing FastAPI APIs and does not duplicate hotspot detection,
analytics, risk scoring, recommendations, or AI inference in the browser.

## Setup

From this directory:

```powershell
npm install
Copy-Item .env.example .env
```

Set `.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_DEVELOPMENT_USER_ID=<existing-authority-user-uuid>
```

The development UUID is sent centrally as `X-Development-User-Id`. This is the
project's temporary development mechanism, not JWT authentication. Do not put
passwords or other secrets in Vite environment variables.

## Run and build

```powershell
npm run dev
npm run test
npm run build
```

The backend must be running at the configured API base URL. The dashboard calls:

- `GET /api/v1/reports`
- `GET /api/v1/analytics/hotspots`
- `GET /api/v1/analytics/risk`
- `GET /api/v1/recommendations`
- `GET /api/v1/interventions`
- `GET /api/v1/impact/{hotspot_id}` when a hotspot is selected

## Dashboard behavior

- Report and hotspot coordinates are validated before map rendering.
- Invalid, missing, infinite, or out-of-range coordinates are ignored.
- India is the default map view when there is no valid data.
- Risk values come from FastAPI and are displayed as an **explainable
  location-priority score**, not a crime prediction.
- Evidence components are shown separately; missing evidence is displayed as
  unavailable.
- Reports, interventions, risk, recommendations, and impact sections handle
  loading, empty, HTTP error, and network error states without crashing.
- Filters use existing report query parameters for category, status, and
  severity.
- No browser-side LLM/VLM calls are made.

Responsible-AI principle:

> AI analyzes places, hazards and observable patterns — not individuals.

The dashboard is a visualization layer for human authorities. It does not
identify people, profile citizens, determine report truth, create interventions,
or make autonomous enforcement decisions.

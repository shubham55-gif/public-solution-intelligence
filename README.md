# Public Solution Intelligence

**Technathon 2026 — PS12 Community Public-Space Safety Intelligence**  
*Team W* | GitHub: `shubham55-gif`

---

## 🌟 Overview

**Public Solution Intelligence** is an end-to-end municipal civic intelligence and community safety platform. It bridges citizens and local authorities through AI-assisted incident reporting, real-time spatial clustering, risk assessment, and transparent verification workflows.

The platform provides:
1. **Android Citizen & Admin Application**: Native Android mobile client with JWT authentication, isolated citizen report lifecycles, and authority operations console.
2. **FastAPI Civic Intelligence Backend**: High-performance asynchronous API backend powered by PostgreSQL, Alembic migrations, DBSCAN spatial hotspot clustering, temporal pattern recognition, recurrence analytics, and multimodal VLM evidence analysis.
3. **React Authority Command Center**: Interactive web dashboard with Leaflet GIS mapping, risk-ranked hotzones, decision support, and intervention tracking.

---

## 🏛️ System Architecture

```
                               ┌─────────────────────────────────────────┐
                               │       Citizen & Admin Android App       │
                               │  (Camera, GPS, Offline Room DB, JWT)    │
                               └────────────────────┬────────────────────┘
                                                    │ REST / JSON (Retrofit)
                                                    ▼
┌────────────────────────────────┐             ┌─────────────────────────┐
│     React Command Center       │◄───────────►│  FastAPI Backend Engine │
│ (GIS Leaflet, Decision Support)│  REST API   │  (Auth, AI, Analytics)  │
└────────────────────────────────┘             └────────────┬────────────┘
                                                            │ SQLAlchemy / async
                                                            ▼
                                               ┌─────────────────────────┐
                                               │   PostgreSQL Database   │
                                               │ (Reports, Users, Audits)│
                                               └─────────────────────────┘
```

---

## 📁 Repository Structure

```
SmartCivicApp3/
├── app/                        # Android Native Application
│   ├── src/main/java/          # Activities, Adapters, Repositories, Entities
│   ├── src/main/res/           # Layouts, Drawables, Values, Navigation
│   ├── AndroidManifest.xml     # Permissions, Manifest Configuration
│   └── build.gradle            # Android Build & Dependencies
├── backend/                    # FastAPI Backend Engine
│   ├── app/                    # API Endpoints, Core Security, DB Models, Services
│   │   ├── api/v1/             # Auth, Reports, Analytics, Hotspots, AI routes
│   │   ├── core/               # Database Engine, JWT Security, Config
│   │   ├── models/             # SQLAlchemy ORM Entities
│   │   ├── schemas/            # Pydantic Request/Response Models
│   │   └── services/           # DBSCAN, Spatial, Temporal, VLM Intelligence
│   ├── alembic/                # PostgreSQL Migration Scripts
│   ├── tests/                  # Pytest Unit & Integration Test Suite (136 tests)
│   ├── uploads/                # Runtime File Upload Storage (.gitkeep)
│   ├── requirements.txt        # Backend Python Dependencies
│   └── README.md               # Backend Technical Documentation
├── frontend/                   # React Authority Command Center
│   ├── src/                    # Components, Pages, GIS Map Hooks, State
│   ├── public/                 # Static Assets
│   ├── package.json            # Node.js Dependencies & Scripts
│   ├── vite.config.js          # Vite Build Configuration
│   └── README.md               # Web Dashboard Documentation
├── gradle/                     # Gradle Wrapper
├── .env.example                # Root Environment Configuration Template
├── ANDROID_BACKEND_SETUP.md    # Android-Backend Integration Guide
├── build.gradle                # Root Gradle Build Configuration
├── settings.gradle             # Project Gradle Settings
└── .gitignore                  # Git Version Control Exclusions
```

---

## 🚀 Quick Start Guide

### 1. Backend Setup (FastAPI & PostgreSQL)

```powershell
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment (copy template)
Copy-Item .env.example .env

# Run database migrations
alembic upgrade head

# Run unit and integration tests (136 tests)
pytest tests -q

# Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Command Center (React + Vite)

```powershell
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Copy environment template
Copy-Item .env.example .env

# Run development server
npm run dev

# Build production bundle
npm run build
```

### 3. Android Application

1. Open the project root in **Android Studio** (Ladybug / Iguana or newer).
2. Sync Gradle files (`.\gradlew.bat :app:assembleDebug`).
3. To render Google Maps, add a restricted Android Maps SDK key to the ignored
   root `local.properties` file as `MAPS_API_KEY=your_maps_key`. The key may
   also be supplied through the `MAPS_API_KEY` environment variable. Do not add
   a real key to tracked files. Without a key, the app remains buildable and
   displays a setup message, but Google map tiles cannot load.
4. For local emulator testing:
   - Default backend URL: `http://10.0.2.2:8000/`
5. For physical device testing over LAN:
   - Configure `-PBACKEND_BASE_URL=http://<YOUR_LAN_IP>:8000/` in Gradle properties (see `ANDROID_BACKEND_SETUP.md`).

---

## 🛡️ Responsible AI & Civic Principles

- **Place-Based Analytics**: AI and DBSCAN algorithms analyze geographic patterns, hazards, and civic infrastructure — never individual citizens.
- **Explainable Priority Scoring**: Transparent metrics combining spatial density, temporal recurrence, and severity.
- **Human-in-the-Loop Authority**: Automated intelligence assists municipal authorities; all final resolution decisions and dispatches require verified human approval.
- **End-to-End Accountability**: Audit trails capture timestamped status changes, before/after evidence photos, and assigned administrator credentials.

---

## 📄 License & Attribution

Developed for **Technathon 2026** under Problem Statement **PS12: Community Public-Space Safety Intelligence**.
All rights reserved by **Team W** (`shubham55-gif`).

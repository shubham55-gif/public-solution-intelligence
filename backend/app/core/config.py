"""Small environment-based settings used by the initial API layer."""

import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / ".env", override=False)

_uploads_setting = Path(os.getenv("UPLOADS_DIR", "uploads"))
UPLOADS_DIR = (
    _uploads_setting if _uploads_setting.is_absolute() else BACKEND_ROOT / _uploads_setting
).resolve()
MAX_IMAGE_SIZE_BYTES = int(os.getenv("MAX_IMAGE_SIZE_BYTES", "5242880"))
DUPLICATE_SPATIAL_THRESHOLD_METERS = float(
    os.getenv("DUPLICATE_SPATIAL_THRESHOLD_METERS", "50")
)
DUPLICATE_TEMPORAL_THRESHOLD_HOURS = float(
    os.getenv("DUPLICATE_TEMPORAL_THRESHOLD_HOURS", "24")
)
HOTSPOT_DBSCAN_RADIUS_METERS = float(
    os.getenv("HOTSPOT_DBSCAN_RADIUS_METERS", "75")
)
HOTSPOT_DBSCAN_MIN_SAMPLES = int(os.getenv("HOTSPOT_DBSCAN_MIN_SAMPLES", "3"))
TEMPORAL_ANALYSIS_WINDOW_DAYS = int(os.getenv("TEMPORAL_ANALYSIS_WINDOW_DAYS", "7"))
TEMPORAL_MORNING_START_HOUR = int(os.getenv("TEMPORAL_MORNING_START_HOUR", "6"))
TEMPORAL_AFTERNOON_START_HOUR = int(os.getenv("TEMPORAL_AFTERNOON_START_HOUR", "12"))
TEMPORAL_EVENING_START_HOUR = int(os.getenv("TEMPORAL_EVENING_START_HOUR", "17"))
TEMPORAL_NIGHT_START_HOUR = int(os.getenv("TEMPORAL_NIGHT_START_HOUR", "22"))
RECURRENCE_PERIOD_DAYS = int(os.getenv("RECURRENCE_PERIOD_DAYS", "7"))
RECURRENCE_ANALYSIS_WINDOW_DAYS = int(
    os.getenv("RECURRENCE_ANALYSIS_WINDOW_DAYS", "28")
)
TREND_PERIOD_DAYS = int(os.getenv("TREND_PERIOD_DAYS", "7"))
TREND_ANALYSIS_WINDOW_DAYS = int(os.getenv("TREND_ANALYSIS_WINDOW_DAYS", "28"))

LLM_ENABLED = os.getenv("LLM_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8081/v1")
LLM_MODEL_NAME = os.getenv(
    "LLM_MODEL_NAME", "Qwen2.5-3B-Instruct-GGUF:Q4_K_M"
)
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "256"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
VLM_ENABLED = os.getenv("VLM_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
VLM_BASE_URL = os.getenv("VLM_BASE_URL", "http://127.0.0.1:8082/v1")
VLM_MODEL_NAME = os.getenv(
    "VLM_MODEL_NAME", "Qwen2.5-VL-3B-Instruct-GGUF:Q4_K_M"
)
VLM_TEMPERATURE = float(os.getenv("VLM_TEMPERATURE", "0.1"))
VLM_MAX_TOKENS = int(os.getenv("VLM_MAX_TOKENS", "128"))
VLM_TIMEOUT_SECONDS = float(os.getenv("VLM_TIMEOUT_SECONDS", "30"))

RISK_SPATIAL_WEIGHT = float(os.getenv("RISK_SPATIAL_WEIGHT", "20"))
RISK_TEMPORAL_WEIGHT = float(os.getenv("RISK_TEMPORAL_WEIGHT", "20"))
RISK_RECURRENCE_WEIGHT = float(os.getenv("RISK_RECURRENCE_WEIGHT", "15"))
RISK_TREND_WEIGHT = float(os.getenv("RISK_TREND_WEIGHT", "15"))
RISK_SEVERITY_WEIGHT = float(os.getenv("RISK_SEVERITY_WEIGHT", "20"))
RISK_DUPLICATE_WEIGHT = float(os.getenv("RISK_DUPLICATE_WEIGHT", "10"))
RISK_SPATIAL_REPORT_COUNT_CAP = float(
    os.getenv("RISK_SPATIAL_REPORT_COUNT_CAP", "10")
)
RISK_TEMPORAL_FREQUENCY_CAP = float(
    os.getenv("RISK_TEMPORAL_FREQUENCY_CAP", "2")
)
RISK_DUPLICATE_COUNT_CAP = float(os.getenv("RISK_DUPLICATE_COUNT_CAP", "5"))

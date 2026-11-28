"""Central configuration, read from environment / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
REPORT_DIR = DATA_DIR / "reports"
VEHICLE_DIR = DATA_DIR / "vehicles"
VEHICLE_DOCS_DIR = VEHICLE_DIR / "documents"
VEHICLE_PHOTOS_DIR = VEHICLE_DIR / "photos"
CENTRAL_DOCS_DIR = DATA_DIR / "documents"
DB_PATH = DATA_DIR / "secondhour.db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
KNOWLEDGE_DIR = ROOT / "knowledge"
DEMO_ASSETS_DIR = ROOT / "demo_assets"

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()

# Fail-closed demo mode: defaults to False
raw_demo = os.getenv("DEMO_MODE", "0").strip().lower()
is_demo_requested = raw_demo in ("1", "true", "yes", "on")

# Production and staging environments must strictly reject demo mode
if ENVIRONMENT in ("production", "staging", "prod", "stage"):
    if is_demo_requested:
        raise RuntimeError(f"FATAL SECURITY CONFIGURATION: DEMO_MODE cannot be enabled in {ENVIRONMENT} environment!")
    DEMO_MODE = False
else:
    # In local development or testing, demo mode only activates when explicitly enabled
    DEMO_MODE = is_demo_requested

# Server-side HMAC secret for OTP hashing
OTP_HMAC_SECRET = os.getenv("OTP_HMAC_SECRET", "").strip()
if not OTP_HMAC_SECRET:
    if ENVIRONMENT in ("production", "staging", "prod", "stage"):
        raise RuntimeError(f"FATAL SECURITY CONFIGURATION: OTP_HMAC_SECRET must be configured in {ENVIRONMENT} environment!")
    # In local dev only, provide a fallback secret if unset
    OTP_HMAC_SECRET = "dev-insecure-otp-hmac-secret-local-only-do-not-use-in-prod"
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# PM-RAHAT constants (PIB, 11 March 2026)
COVER_LIMIT_INR = 150000
COVER_DAYS = 7
POLICE_WINDOW_HOURS = 24
POLICE_WINDOW_HOURS_LIFE_THREATENING = 48
PIB_MARCH_URL = "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2238637"
PIB_AUGUST_URL = "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2298285"

for d in (DATA_DIR, UPLOAD_DIR, REPORT_DIR, VEHICLE_DIR, VEHICLE_DOCS_DIR, VEHICLE_PHOTOS_DIR, CENTRAL_DOCS_DIR):
    d.mkdir(parents=True, exist_ok=True)

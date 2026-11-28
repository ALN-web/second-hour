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

# Server-managed authenticated encryption key for OAuth tokens and verifiers
TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "").strip()
if not TOKEN_ENCRYPTION_KEY:
    if ENVIRONMENT in ("production", "staging", "prod", "stage"):
        raise RuntimeError(f"FATAL SECURITY CONFIGURATION: TOKEN_ENCRYPTION_KEY must be configured in {ENVIRONMENT} environment!")
    # In local dev only, provide a deterministic fallback Fernet key
    TOKEN_ENCRYPTION_KEY = "dev-insecure-token-encryption-key-local-only-do-not-use-in-prod-32b="

# Institutional verification provider execution mode: MOCK | SANDBOX | PRODUCTION (default: MOCK)
raw_provider_mode = os.getenv("VERIFICATION_PROVIDER_MODE", "MOCK").strip().upper()
if raw_provider_mode in ("MOCK", "SANDBOX", "PRODUCTION"):
    VERIFICATION_PROVIDER_MODE = raw_provider_mode
else:
    VERIFICATION_PROVIDER_MODE = "MOCK"

# Verification provider credentials (required in PRODUCTION mode; missing credentials fail closed)
DIGILOCKER_CLIENT_ID = os.getenv("DIGILOCKER_CLIENT_ID", "").strip()
DIGILOCKER_CLIENT_SECRET = os.getenv("DIGILOCKER_CLIENT_SECRET", "").strip()
DIGILOCKER_API_BASE = os.getenv("DIGILOCKER_API_BASE", "https://digilocker.meripehchaan.gov.in/public/oauth2/1").strip()
DIGILOCKER_AUTH_URL = os.getenv("DIGILOCKER_AUTH_URL", f"{DIGILOCKER_API_BASE}/authorize").strip()
DIGILOCKER_TOKEN_URL = os.getenv("DIGILOCKER_TOKEN_URL", f"{DIGILOCKER_API_BASE}/token").strip()
DIGILOCKER_REVOKE_URL = os.getenv("DIGILOCKER_REVOKE_URL", f"{DIGILOCKER_API_BASE}/revoke").strip()
DIGILOCKER_REDIRECT_URI = os.getenv("DIGILOCKER_REDIRECT_URI", "http://localhost:8000/api/verify/digilocker/callback").strip()
DIGILOCKER_SCOPES = os.getenv("DIGILOCKER_SCOPES", "read").strip()

VAHAN_API_KEY = os.getenv("VAHAN_API_KEY", "").strip()
VAHAN_API_URL = os.getenv("VAHAN_API_URL", "https://api.parivahan.gov.in/vahan4").strip()

IIB_API_KEY = os.getenv("IIB_API_KEY", "").strip()
IIB_API_URL = os.getenv("IIB_API_URL", "https://api.iib.gov.in/v1").strip()
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

"""Central configuration, read from environment / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
REPORT_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "secondhour.db"
KNOWLEDGE_DIR = ROOT / "knowledge"
DEMO_ASSETS_DIR = ROOT / "demo_assets"

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")

# PM-RAHAT constants (PIB, 11 March 2026)
COVER_LIMIT_INR = 150000
COVER_DAYS = 7
POLICE_WINDOW_HOURS = 24
POLICE_WINDOW_HOURS_LIFE_THREATENING = 48
PIB_MARCH_URL = "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2238637"
PIB_AUGUST_URL = "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2298285"

for d in (DATA_DIR, UPLOAD_DIR, REPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)

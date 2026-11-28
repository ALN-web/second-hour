#!/usr/bin/env python3
"""Second Hour — Unified Cross-Platform Project Launcher.

Starts and orchestrates all local services with a single command:
    python scripts/dev.py

Services managed:
- MCP Server (MCP Python SDK v2, Streamable HTTP on :8001/mcp)
- Backend API (FastAPI / Uvicorn on :8000)
- Frontend (React / Vite on :5173)
- Database connectivity verification (PostgreSQL Neon / SQLite fallback)

Features:
- Cross-platform support (Windows PowerShell/CMD, macOS, Linux).
- Automatic virtual environment & runtime dependency resolution.
- Fail-closed environment configuration validation without secret leakage.
- Health checks and readiness polling.
- Real-time labeled log streaming.
- Process tree management and clean, graceful shutdown (zero orphaned processes).
"""
from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# -----------------------------------------------------------------------------
# Terminal Styling (ANSI with auto-disable fallback)
# -----------------------------------------------------------------------------
USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None

if USE_COLOR:
    CLR_RESET = "\033[0m"
    CLR_BOLD = "\033[1m"
    CLR_DIM = "\033[2m"
    CLR_RED = "\033[91m"
    CLR_GREEN = "\033[92m"
    CLR_YELLOW = "\033[93m"
    CLR_BLUE = "\033[94m"
    CLR_MAGENTA = "\033[95m"
    CLR_CYAN = "\033[96m"
    CLR_WHITE = "\033[97m"
else:
    CLR_RESET = ""
    CLR_BOLD = ""
    CLR_DIM = ""
    CLR_RED = ""
    CLR_GREEN = ""
    CLR_YELLOW = ""
    CLR_BLUE = ""
    CLR_MAGENTA = ""
    CLR_CYAN = ""
    CLR_WHITE = ""


def log_info(msg: str) -> None:
    print(f"{CLR_BLUE}[INFO]{CLR_RESET} {msg}", flush=True)


def log_ok(msg: str) -> None:
    print(f"{CLR_GREEN}[OK]{CLR_RESET} {msg}", flush=True)


def log_warn(msg: str) -> None:
    print(f"{CLR_YELLOW}[WARN]{CLR_RESET} {msg}", flush=True)


def log_err(msg: str) -> None:
    print(f"{CLR_RED}[FAIL]{CLR_RESET} {msg}", flush=True)


def log_banner(msg: str) -> None:
    print(f"{CLR_BOLD}{CLR_CYAN}{msg}{CLR_RESET}", flush=True)


# -----------------------------------------------------------------------------
# Repository & Executable Resolution
# -----------------------------------------------------------------------------
def get_repo_root() -> Path:
    """Resolve repository root directory reliably from script location."""
    return Path(__file__).resolve().parent.parent


def find_python_executable(repo_root: Path) -> Path:
    """Resolve the active Python interpreter, preferring .venv when available."""
    if os.name == "nt":
        venv_py = repo_root / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = repo_root / ".venv" / "bin" / "python"

    if venv_py.is_file() and os.access(venv_py, os.X_OK):
        return venv_py

    return Path(sys.executable).resolve()


def find_npm_command() -> str:
    """Resolve the npm executable cross-platform (handling npm.cmd on Windows)."""
    if os.name == "nt":
        npm_cmd = shutil.which("npm.cmd")
        if npm_cmd:
            return npm_cmd
        npm = shutil.which("npm")
        if npm:
            return npm
        return "npm.cmd"
    
    npm = shutil.which("npm")
    return npm or "npm"


def check_runtime_prerequisites(repo_root: Path, python_exe: Path) -> Tuple[bool, List[str]]:
    """Validate runtime environment, tools, and dependencies."""
    issues: List[str] = []

    # 1. Python version check (requires >= 3.10)
    if sys.version_info < (3, 10):
        issues.append(f"Python 3.10+ required. Current version: {platform.python_version()}")

    # 2. Node.js check
    node_path = shutil.which("node")
    if not node_path:
        issues.append("Node.js is not found in PATH. Please install Node.js (v18+) to run the frontend.")
    else:
        try:
            node_ver = subprocess.check_output([node_path, "--version"], text=True, timeout=5).strip()
        except Exception:
            node_ver = "unknown"

    # 3. npm check
    npm_cmd = find_npm_command()
    if not shutil.which(npm_cmd):
        issues.append("npm package manager is not found in PATH.")

    # 4. Frontend node_modules check
    frontend_dir = repo_root / "frontend"
    node_modules = frontend_dir / "node_modules"
    if not node_modules.is_dir():
        issues.append(
            f"Frontend dependencies missing at '{node_modules}'. "
            "Please run 'cd frontend && npm install' before starting the development server."
        )

    return len(issues) == 0, issues


# -----------------------------------------------------------------------------
# Environment & Configuration Validation
# -----------------------------------------------------------------------------
def sanitize_url(raw_url: str) -> str:
    """Mask credentials in database or API URLs to prevent secret leakage in logs."""
    if not raw_url:
        return ""
    return re.sub(r"://([^:@]+):([^@]+)@", r"://\1:****@", raw_url)


def load_env_file(repo_root: Path) -> Dict[str, str]:
    """Parse .env file into key-value pairs without modifying real files or leaking values."""
    env_file = repo_root / ".env"
    env_vars: Dict[str, str] = {}
    if not env_file.is_file():
        return env_vars

    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    env_vars[key] = val
    except Exception as exc:
        log_warn(f"Failed to read .env file cleanly: {exc}")

    return env_vars


def validate_environment(repo_root: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate application configuration, ensuring secrets are configured and never exposed."""
    env_vars = load_env_file(repo_root)
    env_file_exists = (repo_root / ".env").is_file()

    environment = env_vars.get("ENVIRONMENT", os.getenv("ENVIRONMENT", "development")).strip().lower()
    db_url = env_vars.get("DATABASE_URL", os.getenv("DATABASE_URL", "")).strip()
    demo_mode_val = env_vars.get("DEMO_MODE", os.getenv("DEMO_MODE", "0")).strip().lower()
    is_demo = demo_mode_val in ("1", "true", "yes", "on")
    otp_hmac_secret = env_vars.get("OTP_HMAC_SECRET", os.getenv("OTP_HMAC_SECRET", "")).strip()
    token_key = env_vars.get("TOKEN_ENCRYPTION_KEY", os.getenv("TOKEN_ENCRYPTION_KEY", "")).strip()
    trust_mode = env_vars.get("VERIFICATION_PROVIDER_MODE", os.getenv("VERIFICATION_PROVIDER_MODE", "MOCK")).strip().upper()
    anthropic_key = env_vars.get("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY", "")).strip()

    errors: List[str] = []
    metadata: Dict[str, Any] = {
        "env_file_exists": env_file_exists,
        "environment": environment,
        "has_postgres": bool(db_url and ("postgres" in db_url.lower())),
        "trust_mode": trust_mode,
        "has_anthropic": bool(anthropic_key),
    }

    # Security check: Production/staging must fail-closed if demo mode is enabled
    if environment in ("production", "staging", "prod", "stage"):
        if is_demo:
            errors.append("FATAL SECURITY: DEMO_MODE cannot be enabled in production or staging environment.")
        if not otp_hmac_secret or "replace-with" in otp_hmac_secret:
            errors.append("FATAL SECURITY: Real OTP_HMAC_SECRET must be configured in production/staging.")
        if not token_key:
            errors.append("FATAL SECURITY: TOKEN_ENCRYPTION_KEY must be configured in production/staging.")

    # Provider mode credential check
    if trust_mode == "PRODUCTION":
        dl_client = env_vars.get("DIGILOCKER_CLIENT_ID", os.getenv("DIGILOCKER_CLIENT_ID", "")).strip()
        dl_secret = env_vars.get("DIGILOCKER_CLIENT_SECRET", os.getenv("DIGILOCKER_CLIENT_SECRET", "")).strip()
        if not dl_client or not dl_secret:
            errors.append("VERIFICATION_PROVIDER_MODE is set to PRODUCTION but DIGILOCKER_CLIENT_ID / CLIENT_SECRET are missing.")

    return len(errors) == 0, errors, metadata


def verify_database_connectivity(repo_root: Path) -> Tuple[bool, str]:
    """Test database connectivity via app.db.check_connection without exposing credentials."""
    # Ensure repo root is on sys.path
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from app.db import check_connection
        res = check_connection()
        if res.get("ok"):
            dialect = res.get("dialect", "unknown")
            is_pg = res.get("is_postgres", False)
            if is_pg:
                return True, "Neon PostgreSQL (connected)"
            return True, f"SQLite ({dialect} fallback)"
        error_msg = res.get("error", "Unknown database connection failure")
        return False, sanitize_url(str(error_msg))
    except Exception as exc:
        return False, sanitize_url(str(exc))


# -----------------------------------------------------------------------------
# Port Checking & Readiness Utilities
# -----------------------------------------------------------------------------
def is_port_bound(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a TCP port is currently open and bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def check_http_endpoint(url: str, timeout: float = 5.0) -> Tuple[bool, Optional[int]]:
    """Poll an HTTP endpoint to verify service readiness."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SecondHourLauncher/1.0", "Accept": "*/*"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return True, response.status
    except urllib.error.HTTPError as e:
        # HTTP response codes (e.g., 200, 405, 406) confirm the server process is alive and answering
        return True, e.code
    except Exception:
        return False, None


# -----------------------------------------------------------------------------
# Managed Process & Process Tree Termination
# -----------------------------------------------------------------------------
class ManagedService:
    """Represents a managed application subprocess with labeled log streaming."""

    def __init__(
        self,
        name: str,
        cmd: List[str],
        cwd: Path,
        port: int,
        readiness_url: str,
        color_code: str,
        env: Optional[Dict[str, str]] = None,
    ):
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.port = port
        self.readiness_url = readiness_url
        self.color_code = color_code
        self.env = env or os.environ.copy()
        self.process: Optional[subprocess.Popen] = None
        self.is_reused: bool = False
        self.early_logs: List[str] = []
        self._streaming: bool = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the process in its own process group with redirected output."""
        effective_env = self.env.copy()
        effective_env["PYTHONUNBUFFERED"] = "1"
        effective_env["PYTHONIOENCODING"] = "utf-8"

        creationflags = 0
        preexec_fn = None
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            preexec_fn = os.setsid

        self.process = subprocess.Popen(
            self.cmd,
            cwd=str(self.cwd),
            env=effective_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            preexec_fn=preexec_fn,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )

        self._thread = threading.Thread(target=self._read_output, daemon=True)
        self._thread.start()

    def _read_output(self) -> None:
        """Background thread reading process output pipe."""
        if not self.process or not self.process.stdout:
            return

        for line in iter(self.process.stdout.readline, ""):
            line_str = line.rstrip()
            if not line_str:
                continue

            if not self._streaming:
                self.early_logs.append(line_str)
                if len(self.early_logs) > 100:
                    self.early_logs.pop(0)
            else:
                tag = f"{self.color_code}[{self.name.lower():<8}]{CLR_RESET}"
                print(f"{tag} {line_str}", flush=True)

    def enable_streaming(self) -> None:
        """Flush early buffered logs and enable continuous live streaming."""
        self._streaming = True
        if self.early_logs:
            for line_str in self.early_logs:
                tag = f"{self.color_code}[{self.name.lower():<8}]{CLR_RESET}"
                print(f"{tag} {line_str}", flush=True)
            self.early_logs.clear()

    def is_alive(self) -> bool:
        if self.is_reused:
            return True
        return self.process is not None and self.process.poll() is None

    def poll_exit_code(self) -> Optional[int]:
        if self.is_reused:
            return None
        return self.process.poll() if self.process else None

    def stop(self, timeout: float = 3.0) -> None:
        """Cleanly terminate the process and its full child process tree."""
        if self.is_reused or not self.process:
            return

        if self.process.poll() is not None:
            return

        pid = self.process.pid
        if os.name == "nt":
            # Graceful terminate first
            try:
                self.process.terminate()
                self.process.wait(timeout=timeout)
            except (subprocess.TimeoutExpired, Exception):
                # Forcefully kill process tree using taskkill
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                except Exception:
                    pass
        else:
            # POSIX process group termination
            try:
                pgid = os.getpgid(pid)
                os.killpg(pgid, signal.SIGTERM)
                self.process.wait(timeout=timeout)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except Exception:
                    pass
            except Exception:
                self.process.terminate()


# -----------------------------------------------------------------------------
# Main Launcher Orchestrator
# -----------------------------------------------------------------------------
class Launcher:
    """Manages pre-flight verification, service lifecycle, health checks, and shutdown."""

    def __init__(
        self,
        repo_root: Path,
        python_exe: Path,
        port_backend: int = 8000,
        port_mcp: int = 8001,
        port_frontend: int = 5173,
        include_mcp: bool = True,
        include_frontend: bool = True,
    ):
        self.repo_root = repo_root
        self.python_exe = python_exe
        self.port_backend = port_backend
        self.port_mcp = port_mcp
        self.port_frontend = port_frontend
        self.include_mcp = include_mcp
        self.include_frontend = include_frontend
        self.services: List[ManagedService] = []
        self.shutdown_event = threading.Event()
        self.is_shutting_down = False

    def setup_services(self) -> None:
        """Configure managed services with appropriate commands and working directories."""
        npm_cmd = find_npm_command()

        # 1. MCP Server
        if self.include_mcp:
            mcp_cmd = [str(self.python_exe), "-m", "app.mcp_server"]
            self.services.append(
                ManagedService(
                    name="MCP",
                    cmd=mcp_cmd,
                    cwd=self.repo_root,
                    port=self.port_mcp,
                    readiness_url=f"http://127.0.0.1:{self.port_mcp}/mcp",
                    color_code=CLR_CYAN,
                )
            )

        # 2. Backend API (Uvicorn)
        backend_cmd = [
            str(self.python_exe),
            "-m",
            "uvicorn",
            "app.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port_backend),
        ]
        self.services.append(
            ManagedService(
                name="Backend",
                cmd=backend_cmd,
                cwd=self.repo_root,
                port=self.port_backend,
                readiness_url=f"http://127.0.0.1:{self.port_backend}/api/health",
                color_code=CLR_GREEN,
            )
        )

        # 3. Frontend (Vite)
        if self.include_frontend:
            frontend_cmd = [npm_cmd, "run", "dev"]
            self.services.append(
                ManagedService(
                    name="Frontend",
                    cmd=frontend_cmd,
                    cwd=self.repo_root / "frontend",
                    port=self.port_frontend,
                    readiness_url=f"http://localhost:{self.port_frontend}",
                    color_code=CLR_MAGENTA,
                )
            )

    def wait_for_service_readiness(self, svc: ManagedService, timeout: float = 45.0) -> bool:
        """Poll readiness endpoint until service is healthy or timeout expires."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.shutdown_event.is_set():
                return False

            # Check if process terminated prematurely
            exit_code = svc.poll_exit_code()
            if exit_code is not None:
                log_err(f"Service '{svc.name}' exited prematurely with code {exit_code}.")
                if svc.early_logs:
                    print(f"\n{CLR_RED}--- {svc.name} Error Output ---{CLR_RESET}")
                    for line in svc.early_logs[-20:]:
                        print(f"  {line}")
                    print(f"{CLR_RED}--------------------------------{CLR_RESET}\n")
                return False

            # Check readiness via HTTP endpoint with sufficient timeout for DB/MCP checks
            is_ready, status = check_http_endpoint(svc.readiness_url, timeout=4.0)
            if not is_ready and svc.name == "Backend":
                # Fallback check to /docs if /api/health is performing heavy discovery
                docs_url = f"http://127.0.0.1:{svc.port}/docs"
                is_ready, _ = check_http_endpoint(docs_url, timeout=2.0)

            if is_ready:
                return True

            time.sleep(0.5)

        if svc.early_logs:
            print(f"\n{CLR_YELLOW}--- {svc.name} Recent Output ---{CLR_RESET}")
            for line in svc.early_logs[-20:]:
                print(f"  {line}")
            print(f"{CLR_YELLOW}---------------------------------{CLR_RESET}\n")

        return False

    def start_all(self) -> bool:
        """Start all configured services sequentially and confirm readiness."""
        for svc in self.services:
            # Check if service is already running on configured port
            if is_port_bound(svc.port):
                is_healthy, _ = check_http_endpoint(svc.readiness_url, timeout=1.0)
                if is_healthy:
                    svc.is_reused = True
                    log_ok(f"{svc.name} already running — {svc.readiness_url}")
                    continue
                else:
                    log_warn(
                        f"Port {svc.port} is already in use by an unrecognized process. "
                        f"Attempting to start {svc.name} anyway..."
                    )

            # Start service process
            try:
                svc.start()
            except Exception as exc:
                log_err(f"Failed to start service '{svc.name}': {exc}")
                return False

            # Wait for readiness
            ready = self.wait_for_service_readiness(svc, timeout=45.0)
            if not ready:
                log_err(f"Service '{svc.name}' failed readiness check within timeout.")
                return False

            log_ok(f"{svc.name} started — {svc.readiness_url}")

        return True

    def enable_all_streaming(self) -> None:
        """Enable live streaming for all managed child processes."""
        for svc in self.services:
            svc.enable_streaming()

    def run_monitor_loop(self) -> None:
        """Monitor running child processes until shutdown is requested."""
        try:
            while not self.shutdown_event.is_set():
                for svc in self.services:
                    if svc.is_reused:
                        continue
                    exit_code = svc.poll_exit_code()
                    if exit_code is not None:
                        log_err(f"Service '{svc.name}' terminated unexpectedly with code {exit_code}.")
                        self.shutdown_event.set()
                        break
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

    def shutdown(self) -> None:
        """Gracefully stop all child processes."""
        if self.is_shutting_down:
            return
        self.is_shutting_down = True
        self.shutdown_event.set()

        print(f"\n{CLR_YELLOW}[SHUTDOWN] Stopping all child processes gracefully...{CLR_RESET}", flush=True)
        for svc in reversed(self.services):
            if not svc.is_reused and svc.is_alive():
                print(f"  Stopping {svc.name}...", flush=True)
                svc.stop(timeout=2.5)

        print(f"{CLR_GREEN}[SHUTDOWN] All Second Hour services stopped. Goodbye!{CLR_RESET}\n", flush=True)


# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Second Hour — Developer Experience: Unified Project Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--no-frontend", action="store_true", help="Start backend & MCP without frontend")
    parser.add_argument("--no-mcp", action="store_true", help="Start backend & frontend without MCP server")
    parser.add_argument("--seed", action="store_true", help="Seed the database with sample demo cases before startup")
    parser.add_argument("--check-only", action="store_true", help="Run pre-flight checks and exit without starting services")
    parser.add_argument("--port-backend", type=int, default=8000, help="Backend API port (default: 8000)")
    parser.add_argument("--port-mcp", type=int, default=8001, help="MCP server port (default: 8001)")
    parser.add_argument("--port-frontend", type=int, default=5173, help="Frontend port (default: 5173)")

    args = parser.parse_args()

    repo_root = get_repo_root()
    python_exe = find_python_executable(repo_root)

    print()
    log_banner("=" * 66)
    log_banner(" Second Hour — Development Environment Launcher ")
    log_banner("=" * 66)
    print(f" OS:          {platform.system()} {platform.release()} ({platform.machine()})")
    print(f" Repository:  {repo_root}")
    print(f" Python:      {python_exe} ({platform.python_version()})")
    print()

    # 1. Check prerequisites
    prereqs_ok, prereq_issues = check_runtime_prerequisites(repo_root, python_exe)
    if not prereqs_ok:
        for issue in prereq_issues:
            log_err(issue)
        return 1

    # 2. Validate environment configuration
    env_ok, env_issues, env_meta = validate_environment(repo_root)
    if not env_ok:
        for err in env_issues:
            log_err(err)
        return 1

    log_ok("Environment configuration validated")

    # 3. Check database connectivity
    db_ok, db_desc = verify_database_connectivity(repo_root)
    if db_ok:
        log_ok(f"Database connection — {db_desc}")
    else:
        log_err(f"Database connection failed: {db_desc}")
        log_warn("Please check your DATABASE_URL in .env or see .env.example.")
        return 1

    # Optional: Run seed if requested
    if args.seed:
        log_info("Running database seeding (scripts.seed)...")
        try:
            res = subprocess.run([str(python_exe), "-m", "scripts.seed"], cwd=str(repo_root), check=True)
            log_ok("Database seeded successfully")
        except subprocess.CalledProcessError as exc:
            log_err(f"Seeding failed with exit code {exc.returncode}")
            return 1

    # If --check-only, print summary and exit cleanly
    if args.check_only:
        print()
        log_banner("=" * 66)
        log_ok("Pre-flight validation complete. All requirements satisfied.")
        log_banner("=" * 66)
        return 0

    # 4. Initialize Launcher
    launcher = Launcher(
        repo_root=repo_root,
        python_exe=python_exe,
        port_backend=args.port_backend,
        port_mcp=args.port_mcp,
        port_frontend=args.port_frontend,
        include_mcp=not args.no_mcp,
        include_frontend=not args.no_frontend,
    )
    launcher.setup_services()

    # Setup signal handlers for graceful shutdown
    def _handle_signal(signum: int, frame: Any) -> None:
        launcher.shutdown()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _handle_signal)

    # 5. Start all services
    try:
        success = launcher.start_all()
        if not success:
            launcher.shutdown()
            return 1

        print()
        log_banner("=" * 66)
        log_banner(" Application ready. ")
        print()
        if not args.no_frontend:
            print(f"   Frontend:          {CLR_BOLD}http://localhost:{args.port_frontend}{CLR_RESET}")
        print(f"   Backend API:       {CLR_BOLD}http://localhost:{args.port_backend}{CLR_RESET}")
        print(f"   API Documentation: {CLR_BOLD}http://localhost:{args.port_backend}/docs{CLR_RESET}")
        if not args.no_mcp:
            print(f"   MCP Server:        {CLR_BOLD}http://localhost:{args.port_mcp}/mcp{CLR_RESET}")
        print()
        print(" Press Ctrl+C to stop all services.")
        log_banner("=" * 66)
        print()

        # Enable streaming of logs
        launcher.enable_all_streaming()

        # Run process monitoring loop
        launcher.run_monitor_loop()
    except Exception as exc:
        log_err(f"Launcher encountered an unexpected error: {exc}")
    finally:
        launcher.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())

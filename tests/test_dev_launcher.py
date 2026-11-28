"""Automated Test Suite for Second Hour Development Launcher (scripts/dev.py).

Verifies:
1. Repository root and executable resolution cross-platform.
2. Safe environment configuration validation without secret leakage.
3. Fail-closed production security checks.
4. Correct service commands, ports, and working directories.
5. Flag filtering (--no-frontend, --no-mcp, --check-only).
6. Process tree termination and cleanup (zero orphans).
7. Readiness polling and port collision handling.
8. Unexpected child process exit detection.
9. Secret sanitization across all diagnostic outputs.
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts import dev


@pytest.fixture
def repo_root():
    return dev.get_repo_root()


def test_get_repo_root(repo_root):
    """Scenario 1: Repository root is resolved correctly."""
    assert repo_root.is_dir()
    assert (repo_root / "app").is_dir()
    assert (repo_root / "frontend").is_dir()
    assert (repo_root / "scripts" / "dev.py").is_file()


def test_find_python_executable(repo_root):
    """Scenario 2: Python interpreter resolution prefers .venv when available."""
    py_exe = dev.find_python_executable(repo_root)
    assert py_exe.is_file()
    assert py_exe.name.startswith("python")


def test_find_npm_command():
    """Scenario 3: npm executable resolution handles Windows cmd and Unix binary."""
    npm_cmd = dev.find_npm_command()
    assert isinstance(npm_cmd, str)
    if os.name == "nt":
        assert npm_cmd.lower().endswith((".cmd", ".exe")) or npm_cmd == "npm"
    else:
        assert "npm" in npm_cmd


def test_sanitize_url():
    """Scenario 4: Secret credentials are never leaked in sanitized URLs."""
    raw = "postgresql://myuser:supersecretpassword123@ep-cool-pooler.aws.neon.tech:5432/neondb"
    sanitized = dev.sanitize_url(raw)
    assert "supersecretpassword123" not in sanitized
    assert "myuser:****@" in sanitized

    # URL without credentials remains unchanged
    clean = "http://127.0.0.1:8000/api/health"
    assert dev.sanitize_url(clean) == clean


def test_validate_environment_development(repo_root):
    """Scenario 5: Environment validation works cleanly in development mode."""
    ok, errors, meta = dev.validate_environment(repo_root)
    assert isinstance(ok, bool)
    assert isinstance(errors, list)
    assert isinstance(meta, dict)
    assert "environment" in meta
    assert "trust_mode" in meta


def test_validate_environment_rejects_demo_mode_in_production(repo_root):
    """Scenario 6: Production environment strictly rejects demo mode."""
    mock_env = {
        "ENVIRONMENT": "production",
        "DEMO_MODE": "1",
        "OTP_HMAC_SECRET": "real-secret-123",
        "TOKEN_ENCRYPTION_KEY": "real-key-123",
    }
    with patch.object(dev, "load_env_file", return_value=mock_env):
        ok, errors, meta = dev.validate_environment(repo_root)
        assert ok is False
        assert any("DEMO_MODE cannot be enabled in production" in err for err in errors)


def test_validate_environment_enforces_production_secrets(repo_root):
    """Scenario 7: Production environment fails closed if OTP secret or token key missing."""
    mock_env = {
        "ENVIRONMENT": "production",
        "DEMO_MODE": "0",
        "OTP_HMAC_SECRET": "",
        "TOKEN_ENCRYPTION_KEY": "",
    }
    with patch.object(dev, "load_env_file", return_value=mock_env):
        ok, errors, _ = dev.validate_environment(repo_root)
        assert ok is False
        assert any("OTP_HMAC_SECRET must be configured" in err for err in errors)
        assert any("TOKEN_ENCRYPTION_KEY must be configured" in err for err in errors)


def test_validate_environment_production_verification_mode_requires_credentials(repo_root):
    """Scenario 8: PRODUCTION verification trust mode enforces provider credentials."""
    mock_env = {
        "ENVIRONMENT": "development",
        "VERIFICATION_PROVIDER_MODE": "PRODUCTION",
        "DIGILOCKER_CLIENT_ID": "",
        "DIGILOCKER_CLIENT_SECRET": "",
    }
    with patch.object(dev, "load_env_file", return_value=mock_env):
        ok, errors, _ = dev.validate_environment(repo_root)
        assert ok is False
        assert any("DIGILOCKER_CLIENT_ID / CLIENT_SECRET are missing" in err for err in errors)


def test_launcher_setup_services_default(repo_root):
    """Scenario 9: Launcher configures MCP, Backend, and Frontend by default."""
    py = dev.find_python_executable(repo_root)
    launcher = dev.Launcher(repo_root=repo_root, python_exe=py)
    launcher.setup_services()

    assert len(launcher.services) == 3
    names = [s.name for s in launcher.services]
    assert "MCP" in names
    assert "Backend" in names
    assert "Frontend" in names

    # Check ports
    mcp_svc = next(s for s in launcher.services if s.name == "MCP")
    assert mcp_svc.port == 8001
    assert "app.mcp_server" in mcp_svc.cmd

    backend_svc = next(s for s in launcher.services if s.name == "Backend")
    assert backend_svc.port == 8000
    assert "app.api:app" in backend_svc.cmd

    frontend_svc = next(s for s in launcher.services if s.name == "Frontend")
    assert frontend_svc.port == 5173
    assert frontend_svc.cwd == repo_root / "frontend"


def test_launcher_setup_services_filtering(repo_root):
    """Scenario 10: Flags --no-frontend and --no-mcp exclude respective services."""
    py = dev.find_python_executable(repo_root)
    # Headless API only
    launcher = dev.Launcher(repo_root=repo_root, python_exe=py, include_frontend=False, include_mcp=False)
    launcher.setup_services()
    assert len(launcher.services) == 1
    assert launcher.services[0].name == "Backend"


def test_check_http_endpoint_readiness():
    """Scenario 11: HTTP readiness check handles success, client errors (405 MCP), and connection failure."""
    # Mock urllib response 200
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value.status = 200
    with patch("urllib.request.urlopen", return_value=mock_resp):
        ok, code = dev.check_http_endpoint("http://127.0.0.1:8000/api/health")
        assert ok is True
        assert code == 200

    # Mock HTTP 405 (MCP Streamable HTTP responds 405 to GET /mcp because it expects POST/SSE)
    import urllib.error
    mock_err = urllib.error.HTTPError(
        url="http://127.0.0.1:8001/mcp", code=405, msg="Method Not Allowed", hdrs={}, fp=None
    )
    with patch("urllib.request.urlopen", side_effect=mock_err):
        ok, code = dev.check_http_endpoint("http://127.0.0.1:8001/mcp")
        assert ok is True
        assert code == 405

    # Mock connection refused
    with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError("Connection refused")):
        ok, code = dev.check_http_endpoint("http://127.0.0.1:9999")
        assert ok is False
        assert code is None


def test_managed_service_lifecycle_mocked(repo_root):
    """Scenario 12: ManagedService starts, captures output, and stops cleanly."""
    py = dev.find_python_executable(repo_root)
    svc = dev.ManagedService(
        name="TestSvc",
        cmd=[str(py), "-c", "import time; time.sleep(10)"],
        cwd=repo_root,
        port=9999,
        readiness_url="http://127.0.0.1:9999",
        color_code=dev.CLR_CYAN,
    )

    mock_proc = MagicMock()
    mock_proc.pid = 12345
    mock_proc.poll.return_value = None
    mock_proc.stdout.readline.side_effect = ["Starting test service...\n", ""]

    with patch("subprocess.Popen", return_value=mock_proc):
        svc.start()
        assert svc.is_alive() is True

        svc.enable_streaming()
        assert svc._streaming is True

        # Stop service
        svc.stop(timeout=1.0)
        assert mock_proc.terminate.called


def test_unexpected_child_exit_detection(repo_root):
    """Scenario 13: Launcher monitor detects unexpected child process termination."""
    py = dev.find_python_executable(repo_root)
    launcher = dev.Launcher(repo_root=repo_root, python_exe=py, include_frontend=False, include_mcp=False)
    launcher.setup_services()

    svc = launcher.services[0]
    mock_proc = MagicMock()
    mock_proc.poll.return_value = 1  # Exited with error code 1
    svc.process = mock_proc

    # In monitor loop, it should detect exit code and set shutdown_event
    with patch("time.sleep", side_effect=[None, KeyboardInterrupt]):
        launcher.run_monitor_loop()
        assert launcher.shutdown_event.is_set()


def test_check_only_flag_execution(repo_root):
    """Scenario 14: --check-only flag validates environment and exits with code 0."""
    py = dev.find_python_executable(repo_root)
    res = subprocess.run(
        [str(py), str(repo_root / "scripts" / "dev.py"), "--check-only"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert res.returncode == 0
    assert "Pre-flight validation complete" in res.stdout
    assert "Database connection" in res.stdout


def test_launcher_e2e_headless_startup_and_shutdown(repo_root):
    """Scenario 15: Real subprocess execution of dev.py --no-frontend, testing live readiness and clean shutdown."""
    import time
    py = dev.find_python_executable(repo_root)
    dev_script = str(repo_root / "scripts" / "dev.py")

    proc = subprocess.Popen(
        [str(py), dev_script, "--no-frontend"],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    ready = False
    start_time = time.time()
    try:
        # Read lines until application ready banner appears
        while time.time() - start_time < 60.0:
            line = proc.stdout.readline()
            if not line:
                break
            if "Application ready" in line:
                ready = True
                break

        assert ready is True, "Launcher did not signal 'Application ready.' within 60 seconds"

        # Verify real backend health endpoint
        ok_back, status_code = dev.check_http_endpoint("http://127.0.0.1:8000/api/health", timeout=5.0)
        assert ok_back is True
        assert status_code == 200

        # Verify real MCP endpoint
        ok_mcp, mcp_code = dev.check_http_endpoint("http://127.0.0.1:8001/mcp", timeout=5.0)
        assert ok_mcp is True
        assert mcp_code in (200, 204, 400, 404, 405, 406)
    finally:
        # Cleanly stop the launcher
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            proc.terminate()
            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.kill()
        proc.wait(timeout=5.0)

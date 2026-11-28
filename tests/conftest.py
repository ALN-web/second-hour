"""Global pytest configuration and fixtures for Second Hour test suites."""
import pytest
from app import config


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    """Configure safe test defaults for unit and integration suites.
    
    Ensures tests run in simulated provider mode by default, preventing unexpected
    outbound network calls to external SMTP servers or SMS gateways while preserving
    strict verification and HMAC security controls.
    
    Tests in test_otp_delivery.py explicitly override these settings to test
    specific provider adapters, error conditions, and missing-credential edge cases.
    """
    if config.ENVIRONMENT not in ("production", "staging", "prod", "stage"):
        monkeypatch.setattr(config, "EMAIL_PROVIDER", "MOCK")
        monkeypatch.setattr(config, "SMS_PROVIDER", "MOCK")
    yield

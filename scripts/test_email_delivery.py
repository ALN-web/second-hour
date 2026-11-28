"""Safe, standalone email OTP delivery test script for Second Hour.

Verifies:
1. Environment and provider configuration (Resend / SMTP).
2. Dispatch of an authentic test OTP via dispatch_email_otp.
3. Provider acceptance and generation of a provider reference / message ID.
4. Safe logging without exposing secret keys, credentials, or full OTP tokens.

Usage:
    python scripts/test_email_delivery.py [--recipient you@example.com] [--code 123456]
"""
import argparse
import sys
from pathlib import Path

# Ensure application root is in python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import config
from app.services.otp_delivery import dispatch_email_otp, mask_identifier


def run_email_delivery_test(recipient: str, code: str = "729401") -> bool:
    print("=" * 65)
    print(" Second Hour — Email OTP Delivery Verification")
    print("=" * 65)

    provider_name = (config.EMAIL_PROVIDER or "SMTP").upper().strip()
    print(f"[*] Configured Email Provider : {provider_name}")
    print(f"[*] Environment               : {config.ENVIRONMENT}")
    print(f"[*] Demo Mode                 : {config.DEMO_MODE}")
    print(f"[*] Recipient (Masked)        : {mask_identifier(recipient)}")

    # Provider-specific diagnostic checks without leaking secrets
    if provider_name == "RESEND":
        has_key = bool(config.RESEND_API_KEY)
        from_email = config.RESEND_FROM_EMAIL or "Not set"
        print(f"[*] RESEND_API_KEY Present    : {has_key}")
        print(f"[*] RESEND_FROM_EMAIL         : {from_email}")
        if not has_key:
            print("\n[ERROR] RESEND_API_KEY is missing from configuration.")
            return False
    elif provider_name == "SMTP":
        has_host = bool(config.SMTP_HOST)
        smtp_user = config.SMTP_USERNAME or "Not set"
        print(f"[*] SMTP_HOST Configured      : {has_host} ({config.SMTP_HOST or 'None'})")
        print(f"[*] SMTP_PORT                 : {config.SMTP_PORT}")
        print(f"[*] SMTP_USER                 : {mask_identifier(smtp_user)}")
        if not has_host:
            print("\n[ERROR] SMTP_HOST is missing from configuration.")
            return False
    elif provider_name == "MOCK":
        print("[!] Provider is set to MOCK.")

    print("\n[*] Dispatching test OTP email...")
    result = dispatch_email_otp(
        to_email=recipient,
        code=code,
        expiry_minutes=10,
        purpose="email_verify",
    )

    print("-" * 65)
    print(f"[*] Success                   : {result.success}")
    print(f"[*] Provider Used             : {result.provider}")
    print(f"[*] Delivery Status           : {result.status.value if hasattr(result.status, 'value') else result.status}")
    print(f"[*] Provider Reference ID     : {result.reference_id or 'None'}")
    print(f"[*] User Message              : {result.user_message}")

    if not result.success:
        print(f"[!] Error Code                : {result.error_code}")
        print(f"[!] Error Message             : {result.error_message}")
        print("\n[FAIL] Email OTP delivery failed.")
        return False

    print("\n[PASS] Email OTP was successfully delivered and accepted by provider.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Second Hour Email OTP Delivery")
    parser.add_argument(
        "--recipient",
        type=str,
        default="deanhackathon123@gmail.com",
        help="Target email address for delivery verification (default: deanhackathon123@gmail.com)",
    )
    parser.add_argument(
        "--code",
        type=str,
        default="729401",
        help="6-digit test code (default: 729401)",
    )
    args = parser.parse_args()

    success = run_email_delivery_test(recipient=args.recipient, code=args.code)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

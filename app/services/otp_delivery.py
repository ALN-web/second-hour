"""Centralized OTP Delivery Engine for Second Hour.

Implements real delivery adapters for email and SMS:
1. Email: Standard SMTP (TLS/SSL) with MIME multipart and Resend REST API fallback.
2. SMS: Twilio and MSG91 (India TRAI DLT Compliant).
3. Indian phone number normalization (+91 / 10-digit validation).
4. Provider delivery status tracking: GENERATED -> REQUESTED -> ACCEPTED | FAILED -> EXPIRED | VERIFIED.
5. Strict secret hygiene: OTP values are NEVER logged, serialized into exceptions, or leaked in error responses.
"""
from __future__ import annotations

import email.utils
import logging
import re
import smtplib
import socket
import ssl
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any
from uuid import uuid4

import httpx

from app import config
from app.services.common import ServiceError

logger = logging.getLogger("secondhour.otp_delivery")


# ==============================================================================
# Delivery Statuses & Dataclasses
# ==============================================================================

class OtpDeliveryStatus:
    GENERATED = "GENERATED"
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    VERIFIED = "VERIFIED"


@dataclass
class DeliveryResult:
    """Result of an OTP delivery attempt via an external provider."""
    success: bool
    provider: str
    status: str  # "ACCEPTED" or "FAILED"
    reference_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None  # Internal detail for logs & audit (never contains OTP)
    user_message: str = "OTP sent successfully."  # Sanitized user-facing message


class DeliveryError(ServiceError):
    """Base exception for OTP delivery errors."""


class DeliveryConfigurationError(DeliveryError):
    """Delivery provider is not configured or has missing credentials."""


class DeliveryProviderError(DeliveryError):
    """External delivery provider rejected or failed to accept message."""


class DeliveryTimeoutError(DeliveryError):
    """External delivery provider request timed out."""


# ==============================================================================
# Identifier Masking & Normalization Helpers
# ==============================================================================

def mask_identifier(val: str | None, visible_start: int = 2, visible_end: int = 4) -> str:
    """Mask sensitive email or phone identifier for logs and audit entries.
    
    Guarantees no full email or phone number is exposed in logs.
    """
    if not val:
        return "Not provided"
    clean = str(val).strip()
    if "@" in clean:
        parts = clean.split("@", 1)
        name, domain = parts[0], parts[1]
        masked_name = name[0] + "***" + (name[-1] if len(name) > 1 else "")
        return f"{masked_name}@{domain}"
    if len(clean) <= 6:
        return f"****{clean[-2:]}"
    return f"{clean[:visible_start]}****{clean[-visible_end:]}"


def normalize_indian_phone(phone: str | None) -> str:
    """Normalize and validate an Indian mobile number into canonical E.164 format (+91XXXXXXXXXX).
    
    Accepted formats:
    - 9876543210 (10 digits starting with 6, 7, 8, or 9)
    - 09876543210 (11 digits with leading 0)
    - 919876543210 (12 digits with country code 91)
    - +919876543210 / +91 98765-43210 (standard formatted)
    
    Also accepts international numbers formatted in standard E.164 (+<country_code><digits>).
    
    Raises:
        ValueError: If the number is malformed or not a valid Indian mobile number.
    """
    if not phone:
        raise ValueError("Mobile number cannot be empty.")
    
    raw = str(phone).strip()
    # Strip whitespace, hyphens, parentheses, dots
    cleaned = re.sub(r"[\s\-\(\)\.]", "", raw)
    
    # Check if starts with +
    if cleaned.startswith("+"):
        if cleaned.startswith("+91"):
            digits = cleaned[3:]
            if re.match(r"^[6-9]\d{9}$", digits):
                return f"+91{digits}"
            raise ValueError(f"Invalid Indian mobile number '{raw}'. Must be 10 digits starting with 6, 7, 8, or 9.")
        # International E.164 number
        if re.match(r"^\+[1-9]\d{6,14}$", cleaned):
            return cleaned
        raise ValueError(f"Invalid international phone number format: '{raw}'.")
    
    # Check leading zero (e.g. 09876543210)
    if cleaned.startswith("0") and len(cleaned) == 11:
        digits = cleaned[1:]
        if re.match(r"^[6-9]\d{9}$", digits):
            return f"+91{digits}"
        raise ValueError(f"Invalid Indian mobile number '{raw}'. Must be 10 digits starting with 6, 7, 8, or 9.")
    
    # Check 12 digits starting with 91 (e.g. 919876543210)
    if cleaned.startswith("91") and len(cleaned) == 12:
        digits = cleaned[2:]
        if re.match(r"^[6-9]\d{9}$", digits):
            return f"+91{digits}"
        raise ValueError(f"Invalid Indian mobile number '{raw}'. Must be 10 digits starting with 6, 7, 8, or 9.")
    
    # Check 10 digits (e.g. 9876543210)
    if re.match(r"^[6-9]\d{9}$", cleaned):
        return f"+91{cleaned}"
    
    raise ValueError(f"Invalid Indian mobile number format: '{raw}'. Expected 10 digits starting with 6-9 (e.g., 9876543210 or +919876543210).")


def get_phone_for_msg91(phone: str) -> str:
    """Format phone number for MSG91 API (requires 91 prefix without leading +)."""
    norm = normalize_indian_phone(phone)
    if norm.startswith("+"):
        return norm[1:]
    return norm


# ==============================================================================
# Email Templates & Adapters
# ==============================================================================

def render_email_template(code: str, expiry_minutes: int, purpose: str) -> tuple[str, str]:
    """Render professional, minimal plain-text and HTML email templates for OTP verification.
    
    Guarantees:
    - Clean branded layout for Second Hour.
    - Monospace 6-digit passcode.
    - Prominent expiration and single-use warning.
    - Explicit security warning never to share code.
    """
    purpose_label = "Email Verification"
    if purpose == "phone_change":
        purpose_label = "Mobile Number Update"
    elif purpose == "email_change":
        purpose_label = "Email Address Update"
    elif purpose == "step_up":
        purpose_label = "High-Security Verification"

    plain_text = (
        f"Second Hour — {purpose_label}\n\n"
        f"Your one-time verification passcode is: {code}\n\n"
        f"This code will expire in {expiry_minutes} minutes and can only be used once.\n\n"
        f"SECURITY NOTICE:\n"
        f"Do not share this code with anyone. Second Hour representatives will never ask for your code.\n"
        f"If you did not request this verification, please disregard this email or review your account security.\n\n"
        f"Second Hour — Emergency Case Coordination & PM-RAHAT Assistance\n"
        f"Not an emergency service: In an emergency, call 112."
    )

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Second Hour Verification Code</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 560px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
    <!-- Header -->
    <tr>
      <td style="background-color: #091528; padding: 24px 32px; text-align: left;">
        <span style="font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px;">Second Hour</span>
        <span style="display: block; font-size: 11px; color: #94a3b8; margin-top: 4px;">PM-RAHAT & Emergency Case Coordination</span>
      </td>
    </tr>
    <!-- Content -->
    <tr>
      <td style="padding: 32px;">
        <h2 style="font-size: 18px; font-weight: 600; color: #0f172a; margin: 0 0 12px 0;">{purpose_label}</h2>
        <p style="font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 24px 0;">
          Use the following 6-digit verification passcode to confirm your identity on Second Hour.
        </p>
        
        <!-- Code Display Box -->
        <div style="background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 12px; padding: 18px; text-align: center; margin: 0 0 24px 0;">
          <span style="font-family: 'Courier New', Courier, monospace; font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #ff7518;">
            {code}
          </span>
          <span style="display: block; font-size: 12px; color: #64748b; margin-top: 8px;">
            Valid for <strong>{expiry_minutes} minutes</strong> · One-time use only
          </span>
        </div>

        <!-- Security Warning -->
        <div style="background-color: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 0 8px 8px 0; margin-bottom: 24px;">
          <p style="font-size: 12px; color: #92400e; margin: 0; line-height: 1.5;">
            <strong>Security Notice:</strong> Never share this code with anyone. Second Hour team members will never ask for your verification code.
          </p>
        </div>

        <p style="font-size: 12px; line-height: 1.5; color: #64748b; margin: 0;">
          If you did not request this verification code, please ignore this email. No changes will be made to your account.
        </p>
      </td>
    </tr>
    <!-- Footer -->
    <tr>
      <td style="background-color: #f8fafc; padding: 20px 32px; border-top: 1px solid #e2e8f0; text-align: center;">
        <p style="font-size: 11px; color: #94a3b8; margin: 0;">
          Second Hour is not an emergency service. In an emergency, call <strong>112</strong>.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""
    return plain_text, html_content


class SmtpEmailAdapter:
    """Standard SMTP email delivery adapter with STARTTLS and timeout handling."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool | None = None,
        use_ssl: bool | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.host = host if host is not None else config.SMTP_HOST
        self.port = port if port is not None else config.SMTP_PORT
        self.username = username if username is not None else config.SMTP_USERNAME
        self.password = password if password is not None else config.SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else config.SMTP_USE_TLS
        self.use_ssl = use_ssl if use_ssl is not None else config.SMTP_USE_SSL
        self.from_email = from_email if from_email is not None else config.SMTP_FROM_EMAIL
        self.from_name = from_name if from_name is not None else config.SMTP_FROM_NAME
        self.timeout = timeout if timeout is not None else config.SMTP_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        """Check if minimum required SMTP settings are present."""
        return bool(self.host and self.from_email)

    def send(self, to_email: str, code: str, expiry_minutes: int = 10, purpose: str = "email_verify") -> DeliveryResult:
        """Send email OTP via SMTP. Never logs the OTP code."""
        if not self.is_configured():
            return DeliveryResult(
                success=False,
                provider="SMTP",
                status=OtpDeliveryStatus.FAILED,
                error_code="CONFIG_MISSING",
                error_message="SMTP_HOST or SMTP_FROM_EMAIL is not configured.",
                user_message="Delivery service is not configured for email.",
            )

        ref_id = f"SMTP-{uuid4().hex[:12]}"
        plain_text, html_content = render_email_template(code, expiry_minutes, purpose)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Second Hour Verification Code"
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to_email
        msg["Message-ID"] = email.utils.make_msgid(domain="secondhour.in")
        msg["Date"] = email.utils.formatdate(localtime=True)

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            logger.info("Attempting SMTP email OTP dispatch to %s (host=%s:%d)", mask_identifier(to_email), self.host, self.port)
            if self.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout, context=context) as server:
                    if self.username and self.password:
                        server.login(self.username, self.password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                    if self.use_tls:
                        server.starttls(context=ssl.create_default_context())
                    if self.username and self.password:
                        server.login(self.username, self.password)
                    server.send_message(msg)

            logger.info("SMTP email OTP successfully accepted for %s (ref=%s)", mask_identifier(to_email), ref_id)
            return DeliveryResult(
                success=True,
                provider="SMTP",
                status=OtpDeliveryStatus.ACCEPTED,
                reference_id=ref_id,
                user_message="OTP sent successfully.",
            )
        except (socket.timeout, TimeoutError) as exc:
            logger.warning("SMTP connection timed out for %s: %s", mask_identifier(to_email), exc)
            return DeliveryResult(
                success=False,
                provider="SMTP",
                status=OtpDeliveryStatus.FAILED,
                error_code="TIMEOUT",
                error_message=f"SMTP server connection timed out after {self.timeout}s",
                user_message="Delivery service temporarily unavailable.",
            )
        except smtplib.SMTPAuthenticationError as exc:
            logger.error("SMTP authentication failed: %s", exc)
            return DeliveryResult(
                success=False,
                provider="SMTP",
                status=OtpDeliveryStatus.FAILED,
                error_code="AUTH_FAILED",
                error_message="SMTP server authentication failed.",
                user_message="Delivery service temporarily unavailable.",
            )
        except smtplib.SMTPException as exc:
            logger.error("SMTP server rejected delivery to %s: %s", mask_identifier(to_email), exc)
            return DeliveryResult(
                success=False,
                provider="SMTP",
                status=OtpDeliveryStatus.FAILED,
                error_code="PROVIDER_REJECTED",
                error_message=f"SMTP server error: {exc}",
                user_message="Unable to send OTP. Please try again.",
            )
        except Exception as exc:
            logger.error("Unexpected error during SMTP delivery to %s: %s", mask_identifier(to_email), exc)
            return DeliveryResult(
                success=False,
                provider="SMTP",
                status=OtpDeliveryStatus.FAILED,
                error_code="UNKNOWN_ERROR",
                error_message=f"Network or system error: {exc}",
                user_message="Unable to send OTP. Please try again.",
            )


class ResendEmailAdapter:
    """Resend REST API email delivery adapter."""

    def __init__(self, api_key: str | None = None, from_email: str | None = None, timeout: float | None = None) -> None:
        self.api_key = api_key if api_key is not None else config.RESEND_API_KEY
        self.from_email = from_email if from_email is not None else config.RESEND_FROM_EMAIL
        self.timeout = timeout if timeout is not None else config.SMTP_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        return bool(self.api_key and self.from_email)

    def send(self, to_email: str, code: str, expiry_minutes: int = 10, purpose: str = "email_verify") -> DeliveryResult:
        if not self.is_configured():
            return DeliveryResult(
                success=False,
                provider="RESEND",
                status=OtpDeliveryStatus.FAILED,
                error_code="CONFIG_MISSING",
                error_message="RESEND_API_KEY is not configured.",
                user_message="Delivery service is not configured for email.",
            )

        plain_text, html_content = render_email_template(code, expiry_minutes, purpose)
        payload = {
            "from": f"Second Hour <{self.from_email}>",
            "to": [to_email],
            "subject": "Second Hour Verification Code",
            "text": plain_text,
            "html": html_content,
        }

        try:
            logger.info("Attempting Resend email OTP dispatch to %s", mask_identifier(to_email))
            resp = httpx.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                ref_id = data.get("id", f"RESEND-{uuid4().hex[:8]}")
                logger.info("Resend email OTP accepted for %s (ref=%s)", mask_identifier(to_email), ref_id)
                return DeliveryResult(
                    success=True,
                    provider="RESEND",
                    status=OtpDeliveryStatus.ACCEPTED,
                    reference_id=ref_id,
                    user_message="OTP sent successfully.",
                )
            error_data = resp.json().catch(lambda: {}) if hasattr(resp, "json") else {}
            logger.warning("Resend rejected delivery to %s (HTTP %d): %s", mask_identifier(to_email), resp.status_code, resp.text)
            return DeliveryResult(
                success=False,
                provider="RESEND",
                status=OtpDeliveryStatus.FAILED,
                error_code="PROVIDER_REJECTED",
                error_message=f"Resend HTTP {resp.status_code}: {resp.text}",
                user_message="Unable to send OTP. Please try again.",
            )
        except httpx.TimeoutException as exc:
            logger.warning("Resend API timed out for %s: %s", mask_identifier(to_email), exc)
            return DeliveryResult(
                success=False,
                provider="RESEND",
                status=OtpDeliveryStatus.FAILED,
                error_code="TIMEOUT",
                error_message="Resend API request timed out.",
                user_message="Delivery service temporarily unavailable.",
            )
        except Exception as exc:
            logger.error("Resend delivery failed for %s: %s", mask_identifier(to_email), exc)
            return DeliveryResult(
                success=False,
                provider="RESEND",
                status=OtpDeliveryStatus.FAILED,
                error_code="NETWORK_ERROR",
                error_message=str(exc),
                user_message="Delivery service temporarily unavailable.",
            )


# ==============================================================================
# SMS Adapters (Twilio & MSG91)
# ==============================================================================

class TwilioSmsAdapter:
    """Twilio SMS delivery adapter using standard REST API."""

    def __init__(
        self,
        account_sid: str | None = None,
        auth_token: str | None = None,
        from_number: str | None = None,
        messaging_service_sid: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.account_sid = account_sid if account_sid is not None else config.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token if auth_token is not None else config.TWILIO_AUTH_TOKEN
        self.from_number = from_number if from_number is not None else config.TWILIO_FROM_NUMBER
        self.messaging_service_sid = messaging_service_sid if messaging_service_sid is not None else config.TWILIO_MESSAGING_SERVICE_SID
        self.timeout = timeout if timeout is not None else config.SMS_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        has_auth = bool(self.account_sid and self.auth_token)
        has_sender = bool(self.from_number or self.messaging_service_sid)
        return has_auth and has_sender

    def send(self, to_phone: str, code: str, expiry_minutes: int = 10, purpose: str = "phone_verify") -> DeliveryResult:
        if not self.is_configured():
            return DeliveryResult(
                success=False,
                provider="TWILIO",
                status=OtpDeliveryStatus.FAILED,
                error_code="CONFIG_MISSING",
                error_message="Twilio credentials (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER) missing.",
                user_message="Delivery service is not configured for phone.",
            )

        try:
            norm_phone = normalize_indian_phone(to_phone)
        except ValueError as val_err:
            return DeliveryResult(
                success=False,
                provider="TWILIO",
                status=OtpDeliveryStatus.FAILED,
                error_code="INVALID_RECIPIENT",
                error_message=str(val_err),
                user_message=str(val_err),
            )

        endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        body_text = f"Your Second Hour verification code is {code}. Valid for {expiry_minutes} minutes. Do not share this code with anyone."

        data: dict[str, str] = {
            "To": norm_phone,
            "Body": body_text,
        }
        if self.messaging_service_sid:
            data["MessagingServiceSid"] = self.messaging_service_sid
        else:
            data["From"] = self.from_number

        try:
            logger.info("Attempting Twilio SMS dispatch to %s", mask_identifier(norm_phone))
            resp = httpx.post(
                endpoint,
                data=data,
                auth=(self.account_sid, self.auth_token),
                timeout=self.timeout,
            )
            if resp.status_code in (200, 201):
                res_json = resp.json()
                sid = res_json.get("sid", f"SM-{uuid4().hex[:12]}")
                logger.info("Twilio SMS accepted for %s (sid=%s)", mask_identifier(norm_phone), sid)
                return DeliveryResult(
                    success=True,
                    provider="TWILIO",
                    status=OtpDeliveryStatus.ACCEPTED,
                    reference_id=sid,
                    user_message="OTP sent successfully.",
                )
            
            # Provider rejected request
            error_data = {}
            try:
                error_data = resp.json()
            except Exception:
                pass
            err_msg = error_data.get("message") or f"HTTP {resp.status_code}"
            err_code = f"TWILIO_{error_data.get('code', resp.status_code)}"
            logger.warning("Twilio rejected delivery to %s (%s): %s", mask_identifier(norm_phone), err_code, err_msg)
            return DeliveryResult(
                success=False,
                provider="TWILIO",
                status=OtpDeliveryStatus.FAILED,
                error_code=err_code,
                error_message=f"Twilio error {err_code}: {err_msg}",
                user_message="Unable to send OTP. Please try again.",
            )
        except httpx.TimeoutException as exc:
            logger.warning("Twilio request timed out for %s: %s", mask_identifier(norm_phone), exc)
            return DeliveryResult(
                success=False,
                provider="TWILIO",
                status=OtpDeliveryStatus.FAILED,
                error_code="TIMEOUT",
                error_message=f"Twilio request timed out after {self.timeout}s",
                user_message="Delivery service temporarily unavailable.",
            )
        except Exception as exc:
            logger.error("Twilio SMS delivery failed for %s: %s", mask_identifier(norm_phone), exc)
            return DeliveryResult(
                success=False,
                provider="TWILIO",
                status=OtpDeliveryStatus.FAILED,
                error_code="NETWORK_ERROR",
                error_message=str(exc),
                user_message="Delivery service temporarily unavailable.",
            )


class Msg91SmsAdapter:
    """MSG91 SMS delivery adapter with India TRAI DLT compliance."""

    def __init__(
        self,
        auth_key: str | None = None,
        template_id: str | None = None,
        sender_id: str | None = None,
        dlt_te_id: str | None = None,
        api_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.auth_key = auth_key if auth_key is not None else config.MSG91_AUTH_KEY
        self.template_id = template_id if template_id is not None else config.MSG91_TEMPLATE_ID
        self.sender_id = sender_id if sender_id is not None else config.MSG91_SENDER_ID
        self.dlt_te_id = dlt_te_id if dlt_te_id is not None else config.MSG91_DLT_TE_ID
        self.api_url = api_url if api_url is not None else config.MSG91_OTP_URL
        self.timeout = timeout if timeout is not None else config.SMS_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        return bool(self.auth_key and self.template_id)

    def send(self, to_phone: str, code: str, expiry_minutes: int = 10, purpose: str = "phone_verify") -> DeliveryResult:
        if not self.is_configured():
            return DeliveryResult(
                success=False,
                provider="MSG91",
                status=OtpDeliveryStatus.FAILED,
                error_code="CONFIG_MISSING",
                error_message="MSG91 credentials (MSG91_AUTH_KEY, MSG91_TEMPLATE_ID) missing.",
                user_message="Delivery service is not configured for phone.",
            )

        try:
            msg91_phone = get_phone_for_msg91(to_phone)
        except ValueError as val_err:
            return DeliveryResult(
                success=False,
                provider="MSG91",
                status=OtpDeliveryStatus.FAILED,
                error_code="INVALID_RECIPIENT",
                error_message=str(val_err),
                user_message=str(val_err),
            )

        headers = {
            "authkey": self.auth_key,
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "template_id": self.template_id,
            "mobile": msg91_phone,
            "otp": code,
            "otp_expiry": expiry_minutes,
        }
        if self.sender_id:
            payload["sender"] = self.sender_id
        if self.dlt_te_id:
            payload["dlt_te_id"] = self.dlt_te_id

        try:
            logger.info("Attempting MSG91 DLT SMS dispatch to %s", mask_identifier(msg91_phone))
            resp = httpx.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            res_json: dict[str, Any] = {}
            try:
                res_json = resp.json()
            except Exception:
                pass

            resp_type = str(res_json.get("type", "")).lower()
            if resp.status_code == 200 and (resp_type == "success" or "request_id" in res_json or "message" in res_json):
                ref_id = str(res_json.get("request_id") or res_json.get("message") or f"MSG91-{uuid4().hex[:8]}")
                logger.info("MSG91 SMS accepted for %s (ref=%s)", mask_identifier(msg91_phone), ref_id)
                return DeliveryResult(
                    success=True,
                    provider="MSG91",
                    status=OtpDeliveryStatus.ACCEPTED,
                    reference_id=ref_id,
                    user_message="OTP sent successfully.",
                )

            err_msg = str(res_json.get("message") or resp.text or f"HTTP {resp.status_code}")
            logger.warning("MSG91 rejected SMS for %s: %s", mask_identifier(msg91_phone), err_msg)
            return DeliveryResult(
                success=False,
                provider="MSG91",
                status=OtpDeliveryStatus.FAILED,
                error_code="MSG91_REJECTED",
                error_message=f"MSG91 error: {err_msg}",
                user_message="Unable to send OTP. Please try again.",
            )
        except httpx.TimeoutException as exc:
            logger.warning("MSG91 request timed out for %s: %s", mask_identifier(msg91_phone), exc)
            return DeliveryResult(
                success=False,
                provider="MSG91",
                status=OtpDeliveryStatus.FAILED,
                error_code="TIMEOUT",
                error_message=f"MSG91 request timed out after {self.timeout}s",
                user_message="Delivery service temporarily unavailable.",
            )
        except Exception as exc:
            logger.error("MSG91 SMS delivery failed for %s: %s", mask_identifier(msg91_phone), exc)
            return DeliveryResult(
                success=False,
                provider="MSG91",
                status=OtpDeliveryStatus.FAILED,
                error_code="NETWORK_ERROR",
                error_message=str(exc),
                user_message="Delivery service temporarily unavailable.",
            )


# ==============================================================================
# Dispatcher Facade
# ==============================================================================

def dispatch_email_otp(to_email: str, code: str, expiry_minutes: int = 10, purpose: str = "email_verify") -> DeliveryResult:
    """Dispatch an email OTP using the configured provider.
    
    Guarantees:
    - Never falls back silently to mock outside explicitly enabled DEMO_MODE.
    - Missing credentials fail safely reporting unconfigured delivery.
    - Provider rejections and timeouts return sanitized user messages.
    """
    provider_name = (config.EMAIL_PROVIDER or "SMTP").upper().strip()

    # Explicit MOCK provider handling
    if provider_name == "MOCK":
        if config.ENVIRONMENT in ("production", "staging", "prod", "stage"):
            raise DeliveryConfigurationError("MOCK email provider is strictly forbidden in production/staging environments!")
        ref_id = f"MOCK-EMAIL-{uuid4().hex[:8]}"
        logger.info("[MOCK] Simulated email OTP accepted for %s (ref=%s)", mask_identifier(to_email), ref_id)
        return DeliveryResult(
            success=True,
            provider="MOCK",
            status=OtpDeliveryStatus.ACCEPTED,
            reference_id=ref_id,
            user_message="OTP sent successfully.",
        )

    # Check for configured adapter
    if provider_name == "RESEND" or (config.RESEND_API_KEY and not config.SMTP_HOST):
        adapter = ResendEmailAdapter()
        if not adapter.is_configured():
            if config.DEMO_MODE:
                ref_id = f"DEV-SIMULATED-EMAIL-{uuid4().hex[:8]}"
                logger.info("[DEMO_MODE] Simulated email delivery for %s (ref=%s)", mask_identifier(to_email), ref_id)
                return DeliveryResult(
                    success=True,
                    provider="DEV_SIMULATED",
                    status=OtpDeliveryStatus.ACCEPTED,
                    reference_id=ref_id,
                    user_message="OTP sent successfully.",
                )
            return DeliveryResult(
                success=False,
                provider="RESEND",
                status=OtpDeliveryStatus.FAILED,
                error_code="CONFIG_MISSING",
                error_message="RESEND_API_KEY is not configured.",
                user_message="Delivery service is not configured for email. Please configure RESEND_API_KEY or SMTP_HOST.",
            )
        return adapter.send(to_email, code, expiry_minutes, purpose)

    # Default to SMTP
    adapter = SmtpEmailAdapter()
    if not adapter.is_configured():
        if config.DEMO_MODE:
            ref_id = f"DEV-SIMULATED-EMAIL-{uuid4().hex[:8]}"
            logger.info("[DEMO_MODE] Simulated email delivery for %s (ref=%s)", mask_identifier(to_email), ref_id)
            return DeliveryResult(
                success=True,
                provider="DEV_SIMULATED",
                status=OtpDeliveryStatus.ACCEPTED,
                reference_id=ref_id,
                user_message="OTP sent successfully.",
            )
        return DeliveryResult(
            success=False,
            provider="SMTP",
            status=OtpDeliveryStatus.FAILED,
            error_code="CONFIG_MISSING",
            error_message="SMTP_HOST or credentials missing.",
            user_message="Delivery service is not configured for email. Please configure SMTP_HOST in .env.",
        )

    return adapter.send(to_email, code, expiry_minutes, purpose)


def dispatch_sms_otp(to_phone: str, code: str, expiry_minutes: int = 10, purpose: str = "phone_verify") -> DeliveryResult:
    """Dispatch an SMS OTP using the configured SMS gateway.
    
    Guarantees:
    - Normalizes Indian mobile numbers (+91 / 10 digits).
    - Never falls back silently to mock outside explicitly enabled DEMO_MODE.
    - Missing credentials fail safely reporting unconfigured delivery.
    - Provider rejections and timeouts return sanitized user messages.
    """
    provider_name = (config.SMS_PROVIDER or "TWILIO").upper().strip()

    # Explicit MOCK provider handling
    if provider_name == "MOCK":
        if config.ENVIRONMENT in ("production", "staging", "prod", "stage"):
            raise DeliveryConfigurationError("MOCK SMS provider is strictly forbidden in production/staging environments!")
        ref_id = f"MOCK-SMS-{uuid4().hex[:8]}"
        logger.info("[MOCK] Simulated SMS OTP accepted for %s (ref=%s)", mask_identifier(to_phone), ref_id)
        return DeliveryResult(
            success=True,
            provider="MOCK",
            status=OtpDeliveryStatus.ACCEPTED,
            reference_id=ref_id,
            user_message="OTP sent successfully.",
        )

    # MSG91 Adapter
    if provider_name == "MSG91":
        adapter = Msg91SmsAdapter()
        if not adapter.is_configured():
            if config.DEMO_MODE:
                ref_id = f"DEV-SIMULATED-SMS-{uuid4().hex[:8]}"
                logger.info("[DEMO_MODE] Simulated SMS delivery for %s (ref=%s)", mask_identifier(to_phone), ref_id)
                return DeliveryResult(
                    success=True,
                    provider="DEV_SIMULATED",
                    status=OtpDeliveryStatus.ACCEPTED,
                    reference_id=ref_id,
                    user_message="OTP sent successfully.",
                )
            return DeliveryResult(
                success=False,
                provider="MSG91",
                status=OtpDeliveryStatus.FAILED,
                error_code="CONFIG_MISSING",
                error_message="MSG91_AUTH_KEY or MSG91_TEMPLATE_ID missing.",
                user_message="Delivery service is not configured for phone. Please configure MSG91 credentials.",
            )
        return adapter.send(to_phone, code, expiry_minutes, purpose)

    # Default to Twilio
    adapter = TwilioSmsAdapter()
    if not adapter.is_configured():
        if config.DEMO_MODE:
            ref_id = f"DEV-SIMULATED-SMS-{uuid4().hex[:8]}"
            logger.info("[DEMO_MODE] Simulated SMS delivery for %s (ref=%s)", mask_identifier(to_phone), ref_id)
            return DeliveryResult(
                success=True,
                provider="DEV_SIMULATED",
                status=OtpDeliveryStatus.ACCEPTED,
                reference_id=ref_id,
                user_message="OTP sent successfully.",
            )
        return DeliveryResult(
            success=False,
            provider="TWILIO",
            status=OtpDeliveryStatus.FAILED,
            error_code="CONFIG_MISSING",
            error_message="TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN missing.",
            user_message="Delivery service is not configured for phone. Please configure Twilio credentials in .env.",
        )

    return adapter.send(to_phone, code, expiry_minutes, purpose)

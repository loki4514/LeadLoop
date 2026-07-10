"""Transactional email via Resend (https://resend.com).

Resend is an HTTP API, so no SMTP wiring is needed. When ``RESEND_API_KEY`` is
not configured, emails are not sent — instead the message (including any reset
link) is logged, which keeps the flow testable in development.
"""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"


async def send_email(to: str, subject: str, html: str) -> None:
    """Send an email, or log it when Resend is not configured.

    Never raises on delivery failure — a failed send is logged and swallowed so
    it can't leak whether an address exists or break the calling request.
    """
    if not settings.RESEND_API_KEY:
        logger.warning(
            "RESEND_API_KEY unset — not sending email. To=%s Subject=%r\n%s",
            to,
            subject,
            html,
        )
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _RESEND_URL,
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={
                    "from": settings.EMAIL_FROM,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
            )
            resp.raise_for_status()
    except Exception:  # noqa: BLE001 — delivery is best-effort
        logger.exception("Failed to send email to %s", to)


def reset_email_html(name: str | None, reset_url: str, ttl_minutes: int) -> str:
    """Build the password-reset email body."""
    greeting = f"Hi {name}," if name else "Hi,"
    return f"""
    <div style="font-family:system-ui,sans-serif;max-width:480px;margin:auto">
      <h2>Reset your LeadLoop password</h2>
      <p>{greeting}</p>
      <p>We received a request to reset your password. Click the button below to
         choose a new one. This link expires in {ttl_minutes} minutes.</p>
      <p style="margin:24px 0">
        <a href="{reset_url}"
           style="background:#4f46e5;color:#fff;padding:10px 18px;border-radius:8px;
                  text-decoration:none;font-weight:600">Reset password</a>
      </p>
      <p style="color:#666;font-size:13px">
        If you didn't request this, you can safely ignore this email.<br>
        Or paste this link into your browser:<br>
        <span style="word-break:break-all">{reset_url}</span>
      </p>
    </div>
    """

"""Pluggable transactional mailer.

Two providers: ``log`` (default — writes the email to the logs, so the reset flow works in
dev/CI with no mail server) and ``smtp`` (real delivery via any SMTP relay: a mailbox provider,
AWS SES SMTP, Mailgun, etc.). The SMTP send is a stdlib ``smtplib`` call run in a thread so it
never blocks the event loop. Callers use :func:`send_password_reset_email`.
"""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

import structlog

from app.config.settings import get_settings

logger = structlog.get_logger(__name__)

_RESET_SUBJECT = "Reset your AutoApply AI password"


def build_reset_link(raw_token: str) -> str:
    """Build the frontend URL the user clicks to complete a password reset."""
    base = get_settings().email.frontend_base_url.rstrip("/")
    return f"{base}/reset-password?token={raw_token}"


def _reset_bodies(reset_link: str) -> tuple[str, str]:
    """Return (text, html) bodies for the reset email."""
    text = (
        "We received a request to reset your AutoApply AI password.\n\n"
        f"Reset it here: {reset_link}\n\n"
        "This link expires shortly and can be used once. "
        "If you didn't request this, ignore this email."
    )
    html = (
        "<p>We received a request to reset your AutoApply AI password.</p>"
        f'<p><a href="{reset_link}">Reset your password</a></p>'
        "<p>This link expires shortly and can be used once. "
        "If you didn't request this, you can safely ignore this email.</p>"
    )
    return text, html


def _send_via_smtp(to: str, subject: str, text_body: str, html_body: str | None) -> None:
    """Synchronous SMTP send (run off the event loop via a worker thread)."""
    cfg = get_settings().email
    msg = EmailMessage()
    msg["From"] = f"{cfg.from_name} <{cfg.from_address}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30) as server:
        if cfg.smtp_starttls:
            server.starttls()
        if cfg.smtp_username:
            server.login(cfg.smtp_username, cfg.smtp_password.get_secret_value())
        server.send_message(msg)


async def send_password_reset_email(to: str, reset_link: str) -> None:
    """Deliver a password-reset email according to the configured provider."""
    cfg = get_settings().email
    text_body, html_body = _reset_bodies(reset_link)
    if cfg.provider == "smtp":
        await asyncio.to_thread(_send_via_smtp, to, _RESET_SUBJECT, text_body, html_body)
        logger.info("password_reset_email_sent", to=to, provider="smtp")
        return
    # ``log`` provider: emit the link so the flow is exercisable without a mail server. In
    # production, use the smtp provider — do not rely on this to actually reach the user.
    logger.info("password_reset_email", to=to, provider="log", reset_link=reset_link)

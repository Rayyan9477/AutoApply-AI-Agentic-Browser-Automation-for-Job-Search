"""Unit tests for the pluggable mailer (log backend + link building)."""

from structlog.testing import capture_logs

from app.services import mailer


def test_build_reset_link_points_at_frontend_with_token():
    link = mailer.build_reset_link("abc123")
    assert "token=abc123" in link
    assert "/reset-password" in link


class TestSendPasswordResetEmail:
    async def test_log_backend_logs_the_link(self, monkeypatch):
        # Force the log provider regardless of ambient env.
        settings = mailer.get_settings()
        monkeypatch.setattr(settings.email, "provider", "log")
        link = "https://app/reset-password?token=xyz"
        with capture_logs() as logs:
            await mailer.send_password_reset_email("who@x.com", link)
        assert any(e.get("reset_link") == link for e in logs)

    async def test_smtp_backend_invokes_transport(self, monkeypatch):
        settings = mailer.get_settings()
        monkeypatch.setattr(settings.email, "provider", "smtp")
        sent: list[tuple[str, str]] = []

        def _fake_smtp_send(to: str, subject: str, text_body: str, html_body: str | None) -> None:
            sent.append((to, subject))

        monkeypatch.setattr(mailer, "_send_via_smtp", _fake_smtp_send)
        await mailer.send_password_reset_email("who@x.com", "https://app/reset-password?token=xyz")
        assert sent and sent[0][0] == "who@x.com"

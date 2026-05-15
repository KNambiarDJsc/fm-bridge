"""
FM Trading Agency — Email Notifier (Resend)
=============================================
Optional email fallback for alerts.
Uses Resend API — https://resend.com

Only fires if RESEND_API_KEY is set in .env.
Uses same message content as Telegram, formatted as plain HTML.
"""
from __future__ import annotations
import logging
import requests

log = logging.getLogger("fm.alerts.email")


def send_email_alert(
    subject:  str,
    body:     str,
    api_key:  str,
    from_addr: str,
    to_addr:  str,
) -> bool:
    """Send via Resend API. Returns True on success."""
    if not api_key or not to_addr:
        log.debug("Email not configured — skipping")
        return False

    # Convert Telegram HTML → clean email HTML
    html_body = (
        body
        .replace("\n", "<br>")
        .replace("<b>", "<strong>")
        .replace("</b>", "</strong>")
        .replace("━━━━━━━━━━━━━━━━━━━━━━━━", "<hr>")
    )

    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "from":    from_addr,
                "to":      [to_addr],
                "subject": subject,
                "html":    f"<html><body style='font-family:monospace;'>{html_body}</body></html>",
            },
            timeout=10,
        )
        if r.status_code in (200, 201):
            log.info("✉  Email sent: %s", subject)
            return True
        else:
            log.error("Email error %d: %s", r.status_code, r.text[:200])
            return False
    except Exception as e:
        log.error("Email send failed: %s", e)
        return False

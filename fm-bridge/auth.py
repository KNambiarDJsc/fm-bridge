"""
FM Trading Agency — Authentication
====================================
Handles Zerodha Kite Connect authentication.

Two modes:
  1. TOTP auto-login  — set ZERODHA_USER_ID + ZERODHA_PASSWORD + ZERODHA_TOTP_KEY in .env
                        Bridge logs in automatically. Zero manual steps.
  2. Manual flow      — original behaviour: opens browser, prompts for request_token.
                        Used as fallback when TOTP is not configured.

The access token is cached to ~/.fm_bridge_token.json and reused
until midnight IST (Zerodha tokens expire at midnight).
"""

from __future__ import annotations

import sys
import time
import webbrowser
from datetime import datetime, timezone
from typing import Optional

import pyotp
import requests
from kiteconnect import KiteConnect

from config import Settings, load_token, save_token, get_settings

import logging
log = logging.getLogger("fm.auth")


def _ist_today() -> str:
    """Return today's date string in IST."""
    import pytz
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).strftime("%Y-%m-%d")


def _token_valid(cfg: dict, api_key: str) -> bool:
    """Check whether the saved token is still valid for today."""
    return (
        cfg.get("access_token")
        and cfg.get("token_date") == _ist_today()
        and cfg.get("api_key") == api_key
    )


def _verify_token(kite: KiteConnect) -> bool:
    """Quick API check — returns True if the token is alive."""
    try:
        kite.profile()
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────
# TOTP AUTO-LOGIN (zero-touch)
# ─────────────────────────────────────────────────────────────────

def _totp_auto_login(kite: KiteConnect, settings: Settings) -> Optional[str]:
    """
    Fully automated Zerodha login via TOTP.
    Requires: ZERODHA_USER_ID, ZERODHA_PASSWORD, ZERODHA_TOTP_KEY in .env

    Returns the access_token string on success, None on failure.
    """
    user_id   = settings.zerodha_user_id
    password  = settings.zerodha_password
    totp_key  = settings.zerodha_totp_key

    if not all([user_id, password, totp_key]):
        log.debug("TOTP credentials not configured — falling back to manual login.")
        return None

    log.info("[AUTH] TOTP auto-login starting for %s ...", user_id)

    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
        })

        # ── Step 1: POST credentials ──────────────────────────────
        r1 = session.post(
            "https://kite.zerodha.com/api/login",
            data={"user_id": user_id, "password": password},
            timeout=10,
        )
        r1.raise_for_status()
        j1 = r1.json()
        if j1.get("status") != "success":
            log.error("Login step 1 failed: %s", j1.get("message", j1))
            return None
        request_id = j1["data"]["request_id"]
        log.debug("Login step 1 OK, request_id: %s", request_id)

        # ── Step 2: POST TOTP ─────────────────────────────────────
        totp_value = pyotp.TOTP(totp_key).now()
        r2 = session.post(
            "https://kite.zerodha.com/api/twofa",
            data={
                "user_id":     user_id,
                "request_id":  request_id,
                "twofa_value": totp_value,
                "skip_session": "",
            },
            timeout=10,
        )
        r2.raise_for_status()
        j2 = r2.json()
        if j2.get("status") != "success":
            log.error("Login step 2 (TOTP) failed: %s", j2.get("message", j2))
            return None
        log.debug("TOTP step OK")

        # ── Step 3: Exchange request_token for access_token ───────
        login_url = kite.login_url()
        r3 = session.get(login_url, allow_redirects=False, timeout=10)
        redirect = r3.headers.get("Location", "")
        if "request_token=" not in redirect:
            # Try following the redirect manually
            r3b = session.get(login_url, timeout=10)
            redirect = r3b.url

        if "request_token=" not in redirect:
            log.error("No request_token in redirect URL: %s", redirect)
            return None

        import urllib.parse as up
        qs = up.parse_qs(up.urlparse(redirect).query)
        request_token = qs.get("request_token", [None])[0]
        if not request_token:
            log.error("Could not extract request_token from %s", redirect)
            return None

        log.debug("request_token extracted: %s...", request_token[:6])

        sess_data  = kite.generate_session(request_token, api_secret=settings.api_secret)
        access_token = sess_data["access_token"]
        log.info("[OK] TOTP auto-login successful for %s", user_id)
        return access_token

    except requests.RequestException as e:
        log.error("TOTP login network error: %s", e)
        return None
    except Exception as e:
        log.exception("TOTP login unexpected error: %s", e)
        return None


# ─────────────────────────────────────────────────────────────────
# MANUAL FALLBACK (original bridge flow)
# ─────────────────────────────────────────────────────────────────

def _manual_login(kite: KiteConnect, settings: Settings) -> Optional[str]:
    """
    Original browser-based login flow (fallback when TOTP not configured).
    Opens browser, waits for user to paste request_token.
    """
    login_url = kite.login_url()
    print("\n" + "═" * 58)
    print("  FM Trading Agency — Zerodha Login")
    print("═" * 58)
    print(f"\n  Opening browser → {login_url}")
    print("\n  After login, copy the request_token from the redirect URL.")
    print("  URL looks like: 127.0.0.1/?request_token=XXXXX&...\n")

    try:
        webbrowser.open(login_url)
    except Exception:
        pass

    request_token = input("  Paste the request_token here: ").strip()
    if not request_token:
        print("[ERR] No request_token. Exiting.")
        sys.exit(1)

    try:
        sess_data    = kite.generate_session(request_token, api_secret=settings.api_secret)
        access_token = sess_data["access_token"]
        return access_token
    except Exception as e:
        print(f"\n[ERR] Session generation failed: {e}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────

def authenticate(settings: Optional[Settings] = None) -> KiteConnect:
    """
    Authenticate with Zerodha and return a ready KiteConnect instance.

    Priority:
      1. Reuse today's cached token (fastest — no network call to Zerodha)
      2. TOTP auto-login (if credentials in .env)
      3. Manual browser flow (fallback)

    Returns a KiteConnect instance with the access token already set.
    """
    if settings is None:
        settings = get_settings()

    api_key = settings.api_key
    if not api_key:
        print("\n[ERR] ZERODHA API_KEY not set in .env -- cannot authenticate.")
        sys.exit(1)

    kite = KiteConnect(api_key=api_key)
    token_cache = load_token()

    # ── 1. Try cached token ───────────────────────────────────────
    if _token_valid(token_cache, api_key):
        log.info("Reusing cached access token from %s", token_cache.get("token_date"))
        kite.set_access_token(token_cache["access_token"])
        if _verify_token(kite):
            profile = kite.profile()
            print(f"\n  [OK] Logged in as: {profile.get('user_name')} (cached token)")
            return kite
        else:
            log.warning("Cached token invalid — re-authenticating.")

    # ── 2. TOTP auto-login ────────────────────────────────────────
    access_token = _totp_auto_login(kite, settings)

    # ── 3. Manual fallback ────────────────────────────────────────
    if access_token is None:
        access_token = _manual_login(kite, settings)

    if not access_token:
        print("[ERR] Authentication failed. Exiting.")
        sys.exit(1)

    kite.set_access_token(access_token)

    # Persist token
    save_token({
        "access_token": access_token,
        "token_date":   _ist_today(),
        "api_key":      api_key,
    })

    profile = kite.profile()
    print(f"\n  [OK] Authenticated as: {profile.get('user_name')} ({profile.get('email')})")
    return kite
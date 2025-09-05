#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ParariusSession — Playwright-based session handler for auto-reacting to Pararius emails.

Owner: Baki Almaci
Date: 04 September 2025

Responsibilities:
- Load cookies from Cookie-Editor `session.json` (or Playwright storage_state).
- Open Pararius "React with one click" tracking URLs.
- Let Playwright execute the hidden <form> POST that registers the reaction.
- Provide a safe, production-ready API (no unhandled crashes).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from playwright.sync_api import sync_playwright, BrowserContext, Page


log = logging.getLogger(__name__)


def _cookie_editor_to_playwright(cookies_raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert Cookie-Editor export format into Playwright cookie objects."""
    out: List[Dict[str, Any]] = []
    for c in cookies_raw:
        name = c.get("name")
        value = c.get("value")
        domain = c.get("domain")
        if not name or value is None:
            continue

        pc: Dict[str, Any] = {
            "name": name,
            "value": value,
            "domain": domain or ".pararius.com",
            "path": c.get("path") or "/",
            "httpOnly": bool(c.get("httpOnly", False)),
            "secure": bool(c.get("secure", True)),
        }

        exp = c.get("expirationDate") or c.get("expiry")
        if isinstance(exp, (int, float)):
            pc["expires"] = int(exp)

        ss = (c.get("sameSite") or "").lower()
        if ss in ("lax", "strict", "none"):
            pc["sameSite"] = ss.capitalize()

        out.append(pc)
    return out


class ParariusSession:
    """Headless-browser session for Pararius reactions using Playwright."""

    def __init__(self, session_file: str = "session.json") -> None:
        self.session_file = session_file

    def _load_cookie_editor_json(self) -> List[Dict[str, Any]]:
        """Load cookies from session.json file (Cookie-Editor export)."""
        try:
            with open(self.session_file, "r") as f:
                data = json.load(f)
            if isinstance(data, dict) and "cookies" in data:
                cookies_raw = data["cookies"]
            else:
                cookies_raw = data
            # log.info("[Session] Loaded %d cookies from %s", len(cookies_raw), self.session_file)
            return cookies_raw
        except Exception as e:
            log.warning("[Session] Could not load cookies: %s", e)
            return []

    def react(self, url: str) -> bool:
        """
        Open the mail tracking URL in a headless Chromium, let the JS auto-submit the form,
        and verify the POST /contact/handle/... happens.

        Returns:
            bool: True if the reaction was (likely) registered, False otherwise.
        """
        if not re.search(r"^https://url\d+\.pararius\.nl/ls/click\?", url):
            log.warning("[Session] URL does not look like a Pararius tracking link: %s", url)

        log.info("🧬 Event:  Starting reaction...")

        cookies_raw = self._load_cookie_editor_json()
        pw_cookies = _cookie_editor_to_playwright(cookies_raw)

        post_seen = {"ok": False}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context: BrowserContext = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800},
                )

                if pw_cookies:
                    try:
                        context.add_cookies(pw_cookies)
                    except Exception as e:
                        log.warning("[Session] Failed to add cookies: %s", e)

                page: Page = context.new_page()

                def on_request_finished(req) -> None:
                    try:
                        if req.method == "POST" and "pararius.com/contact/handle" in req.url:
                            post_seen["ok"] = True
                            # log.info("[Session] Observed POST → %s", req.url)
                    except Exception:
                        pass

                page.on("requestfinished", on_request_finished)

                # Navigate and let JS run
                page.goto(url, wait_until="domcontentloaded", referer="https://www.pararius.com/", timeout=5000)

                # trigger form submit if it exists
                form = page.query_selector("form")
                if form:
                    try:
                        with page.expect_response(
                            lambda r: r.request.method == "POST" and "pararius.com/contact/handle" in r.url,
                            timeout=3_000
                        ):
                            page.evaluate("document.forms[0].submit()")
                    except Exception:
                        log.debug("No explicit POST observed; maybe already auto-submitted.")

                # try:
                #     page.wait_for_load_state("networkidle", timeout=15000)
                # except Exception:
                #     pass

                final_url = page.url
                html = page.content()

                log.info("🔗 URL:  %s", final_url)
                if not post_seen["ok"]:
                    log.debug("[Session] No POST observed, page snippet: %s", html[:300])

                success = False
                if post_seen["ok"]:
                    success = True
                elif "/contact/handle/" in final_url and "one-click-apply" in final_url:
                    success = True
                elif re.search(r"(Thanks for your (reaction|message)|Bedankt|Verzonden)", html, re.I):
                    success = True

                if success:
                    # log.info("[Session] Reaction submitted successfully.")
                    pass
                else:
                    log.warning("[Session] Reaction may not have been registered. Cookies might be stale.")

                browser.close()
                return success

        except Exception as e:
            log.exception("[Session] Playwright error: %s", e)
            return False

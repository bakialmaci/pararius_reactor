#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ParariusBot — orchestrator for the Pararius Auto-Reactor.

Owner: Baki Almaci
Date: 04 September 2025

Responsibilities:
- Fetch unseen emails from a mail client.
- Parse Pararius property details (date, title, price, react link).
- Send "one-click" reactions via a session handler (Playwright-based).
- Track processed UIDs to avoid duplicate processing.
- Run continuously until a stop flag is set.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Callable, Optional, Protocol, Tuple, List
from datetime import datetime

import email
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup  # type: ignore

log = logging.getLogger(__name__)


# ===== Protocols (interfaces) =====
class MailClientProtocol(Protocol):
    def fetch_unseen_from(self, sender: str) -> List[Tuple[bytes, email.message.Message]]:
        ...


class SessionProtocol(Protocol):
    def react(self, url: str) -> bool:
        ...


# ===== Helpers =====
def parse_pararius_mail(msg: email.message.Message) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract (title, price, react_link) from a Pararius HTML email.
    Returns (None, None, None) if parsing fails.
    """
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            try:
                html = part.get_payload(decode=True).decode(errors="ignore")
                soup = BeautifulSoup(html, "html.parser")

                # React link
                react_link = None
                for a in soup.find_all("a", href=True):
                    if re.search(r"React with one click", a.text, re.I):
                        react_link = a["href"]
                        break

                # Title: often in <h2> or strong <a>
                title = None
                title_tag = soup.find(["h1", "h2"])
                if not title_tag:
                    title_tag = soup.find("a", string=re.compile(r"in "))
                if title_tag:
                    title = title_tag.get_text(strip=True)

                # Price: look for € and digits
                price = None
                price_match = soup.find(string=re.compile(r"€\s?\d"))
                if price_match:
                    price = price_match.strip()

                return title, price, react_link
            except Exception as e:
                log.warning("[Parser] Failed to parse HTML: %s", e)
                return None, None, None
    return None, None, None


# ===== Bot implementation =====
class ParariusBot:
    """Main bot that coordinates mail fetching and Pararius reactions."""

    def __init__(self, mail_client: MailClientProtocol, session: SessionProtocol) -> None:
        self.mail_client = mail_client
        self.session = session
        self.processed_uids: set[bytes] = set()

    def run_once(self, sender: str = "noreply@pararius.nl") -> None:
        """Process unseen messages from the given sender once."""
        messages = self.mail_client.fetch_unseen_from(sender)
        for uid, msg in messages:
            if uid in self.processed_uids:
                continue

            # Date
            date_str = msg.get("Date")
            if date_str:
                try:
                    dt = parsedate_to_datetime(date_str)
                    date_str = dt.isoformat()
                except Exception:
                    pass

            # Parse details
            title, price, link = parse_pararius_mail(msg)

            # Pretty log
            log.info("====================================================")
            log.info("🚨 NEW PROPERTY -> %s", datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
            log.info("📅 Date:   %s", date_str or "Unknown")
            log.info("🏠 Title:  %s", title or "Unknown")
            log.info("💶 Price:  %s", price or "Unknown")

            if link:
                try:
                    ok = self.session.react(link)
                    if ok:
                        log.info("✅ Reaction sent! -> %s", datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
                    else:
                        log.warning("⚠️  Reaction may have failed.")
                except Exception as e:
                    log.exception("[Bot] Error during reaction: %s", e)
            else:
                log.warning("⚠️  No react link found.")

            log.info("====================================================\n")

            self.processed_uids.add(uid)

    def run_forever(
        self,
        interval: float = 15,
        stop_flag: Optional[Callable[[], bool]] = None,
        sender: str = "noreply@pararius.nl",
        # sender: str = "example@gmail.com",
    ) -> None:
        """
        Continuous run loop with graceful stop.

        Args:
            interval: How often to poll for new messages (seconds).
            stop_flag: Callable returning True if the bot should stop.
            sender: Mail sender filter (default: Pararius noreply).
        """
        log.info("[Bot] Pararius auto-reactor started (interval=%.2fs).", interval)

        while True:
            if stop_flag and stop_flag():
                log.info("[Bot] Stop flag detected. Exiting run_forever().")
                break

            try:
                self.run_once(sender=sender)
            except Exception as e:
                log.exception("[Bot] Unexpected error in run_once: %s", e)

            # sleep in small steps so signals can break quickly
            slept = 0.0
            while slept < interval:
                if stop_flag and stop_flag():
                    log.info("[Bot] Stop flag detected during sleep. Exiting.")
                    return
                time.sleep(0.2)
                slept += 0.2

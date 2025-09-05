#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pararius Auto-Reactor Bot — production entrypoint

Owner: Baki Almaci
Date: 04 September 2025

Responsibilities:
- Load configuration from environment/.env
- Configure structured logging (console + optional rotating file)
- Start the ParariusBot and keep it alive (self-heal on crashes)
- Handle graceful shutdown (Ctrl+C / SIGTERM)
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import signal
import sys
import time
from typing import Optional

# .env loader (optional – will continue without it if missing)
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore

# Your bot implementation
from .ParariusBot import ParariusBot
from .MailClient import MailClient
from .ParariusSession import ParariusSession
from .NetworkManager import NetworkManager


APP_NAME = "pararius-auto-reactor"
DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DEFAULT_INTERVAL = float(os.getenv("BOT_INTERVAL", "1"))  # seconds
MAX_BACKOFF_SECONDS = 300  # cap exponential backoff at 5 minutes


def setup_logging(level: str = DEFAULT_LOG_LEVEL,
                  log_file: Optional[str] = None) -> None:
    """Configure root logger for console + optional file (rotating)."""
    level_num = getattr(logging, level.upper(), logging.INFO)

    fmt = (
        "%(asctime)s.%(msecs)03dZ "
        f"{APP_NAME} "
        "%(levelname)s "
        "%(name)s "
        "%(message)s"
    )
    datefmt = "%Y-%m-%dT%H:%M:%S"

    handlers: list[logging.Handler] = []

    # Console
    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    handlers.append(console)

    # Optional rotating file
    if log_file:
        try:
            from logging.handlers import RotatingFileHandler
            fileh = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)
            fileh.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
            handlers.append(fileh)
        except Exception as e:  # don’t fail startup just for file logging
            sys.stderr.write(f"[warn] could not init file logger: {e}\n")

    logging.basicConfig(level=level_num, handlers=handlers)


def load_env() -> None:
    """Load .env if python-dotenv is available."""
    if load_dotenv is not None:
        # dotenv only affects missing vars; real env always wins
        load_dotenv()
    else:
        logging.getLogger(__name__).debug("python-dotenv not installed; skipping .env load")


def get_required_env(key: str) -> str:
    """Fetch required env var or raise a clear error."""
    val = os.getenv(key)
    if not val:
        raise RuntimeError(
            f"Missing required environment variable: {key}. "
            "Add it to your environment or .env file."
        )
    return val


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description="Production entrypoint for the Pararius Auto-Reactor bot.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL,
        help=f"Poll interval in seconds (default: {DEFAULT_INTERVAL:.0f})."
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=DEFAULT_LOG_LEVEL,
        help=f"Logging level (default: {DEFAULT_LOG_LEVEL})."
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=os.getenv("LOG_FILE", "").strip() or None,
        help="Optional path to a rotating log file."
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="Disable self-healing restarts (exit on first crash)."
    )
    return parser.parse_args(argv)


class GracefulKiller:
    """Convert SIGINT/SIGTERM into a flag the loop can observe."""
    def __init__(self) -> None:
        self._stop = False
        signal.signal(signal.SIGINT, self._handle)   # Ctrl+C
        signal.signal(signal.SIGTERM, self._handle)  # docker/PM2/systemd stop

    @property
    def stop(self) -> bool:
        return self._stop

    def _handle(self, signum, frame) -> None:
        logging.getLogger(__name__).info("Received signal %s; shutting down…", signum)
        self._stop = True


def main(argv: list[str]) -> int:
    # 1) CLI + env + logging
    args = parse_args(argv)
    setup_logging(level=args.log_level, log_file=args.log_file)
    log = logging.getLogger("main")

    load_env()  # safe if dotenv missing

    try:
        email_account = get_required_env("EMAIL_ACCOUNT")
        email_password = get_required_env("EMAIL_PASSWORD")
    except RuntimeError as e:
        log.error(str(e))
        return 2

    log.info("Starting %s", APP_NAME)
    log.info("Owner: Baki Almaci | Date: 2025-09-04")

    # 2) graceful shutdown handler
    killer = GracefulKiller()

    # 3) self-healing supervisor loop
    attempt = 0
    while not killer.stop:
        try:
            def trigger_restart():
                # Just stop the bot; outer loop restarts it
                killer._stop = True

            nm = NetworkManager(interval=1, on_fail=trigger_restart)
            nm.start()

            mail_client = MailClient(
                server="imap.gmail.com",
                email_account=email_account,
                password=email_password,
                mailbox="INBOX",
            )
            session = ParariusSession("session.json")
            bot = ParariusBot(mail_client=mail_client, session=session)
            log.info("Bot instantiated. Entering run_forever(interval=%.2fs)…", args.interval)
            bot.run_forever(interval=args.interval, stop_flag=lambda: killer.stop)
            # If run_forever ever returns normally, treat as unexpected
            nm.stop()
            log.info("NetworkManager stopped.")
            log.warning("run_forever() returned unexpectedly.")
            if args.no_restart:
                break

        except KeyboardInterrupt:
            log.info("Keyboard interrupt! Exiting.")
            break

        except Exception as e:
            attempt += 1
            log.exception("Unhandled error in bot: %s", e)
            if args.no_restart:
                log.error("--no-restart specified. Exiting on first crash.")
                return 1

            # Exponential backoff with jitter (bounded)
            delay = min(MAX_BACKOFF_SECONDS, (2 ** min(attempt, 8)) + random.uniform(0, 1))
            log.warning("Will attempt restart in %.1fs (attempt #%d)…", delay, attempt)

            # Sleep in small chunks so SIGTERM can stop promptly
            slept = 0.0
            while slept < delay and not killer.stop:
                time.sleep(0.5)
                slept += 0.5

        else:
            # No exception, but if we’re here the loop intends to restart anyway
            attempt += 1
            delay = min(MAX_BACKOFF_SECONDS, 2 ** min(attempt, 8))
            log.warning("Restarting bot in %.1fs (attempt #%d)…", delay, attempt)
            time.sleep(delay)

    log.info("Shutdown complete. Bye.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

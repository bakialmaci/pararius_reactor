#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetworkManager — monitors network connectivity and requests program restart.

Owner: Baki Almaci
Date: 04 September 2025
"""

import logging
import socket
import threading
import time
from typing import Optional, Callable

log = logging.getLogger(__name__)


class NetworkManager:
    """Continuously checks network connectivity."""

    def __init__(
        self,
        interval: float = 1.0,
        target_host: str = "8.8.8.8",
        target_port: int = 53,
        on_fail: Optional[Callable[[], None]] = None,
        fail_threshold: int = 3,
    ) -> None:
        """
        Args:
            interval: seconds between checks
            target_host: host to test connectivity against (default: Google DNS)
            target_port: port to test (default: 53 = DNS)
            on_fail: callback if connectivity is lost repeatedly
            fail_threshold: number of consecutive failures before triggering on_fail
        """
        self.interval = interval
        self.target_host = target_host
        self.target_port = target_port
        self.on_fail = on_fail
        self.fail_threshold = fail_threshold

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._fail_count = 0

    def _check_once(self) -> bool:
        """Try to open a TCP socket. Return True if successful."""
        try:
            with socket.create_connection(
                (self.target_host, self.target_port), timeout=3
            ):
                return True
        except OSError:
            return False

    def _loop(self) -> None:
        while not self._stop.is_set():
            ok = self._check_once()
            if ok:
                if self._fail_count > 0:
                    log.info("[Network] Connectivity restored")
                self._fail_count = 0
            else:
                self._fail_count += 1
                log.warning("[Network] Connectivity check failed (%d/%d)",
                            self._fail_count, self.fail_threshold)
                if self._fail_count >= self.fail_threshold and self.on_fail:
                    log.error("[Network] Threshold reached → requesting restart")
                    try:
                        self.on_fail()
                    except Exception as e:
                        log.exception("[Network] on_fail callback crashed: %s", e)
                    self._fail_count = 0  # reset counter after callback
            time.sleep(self.interval)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("[Network] Manager started (interval=%.1fs)", self.interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        log.info("[Network] Manager stopped")

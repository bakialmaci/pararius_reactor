"""
Pararius Reactor package initializer.

Exposes main classes for easier importing.
"""

from .MailClient import MailClient
from .NetworkManager import NetworkManager
from .ParariusBot import ParariusBot
from .ParariusSession import ParariusSession

__all__ = [
    "MailClient",
    "NetworkManager",
    "ParariusBot",
    "ParariusSession",
]

__version__     = "0.1.0"
__author__      = "Baki Almacı"
__license__     = "GPL-3.0"
__copyright__   = "Copyleft 2025, Baki Almaci"
__email__       = "bakialmaci@gmail.com"
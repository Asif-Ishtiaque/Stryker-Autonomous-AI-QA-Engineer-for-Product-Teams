"""Shared rate limiter. Applied to /auth/login and /auth/register — the two
endpoints reachable with zero prior authentication, and previously the only
ones with no throttling of any kind (no lockout, no minimum password length
either — see RegisterRequest), making credential brute-forcing or mass
registration free for anyone with network access to the API.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

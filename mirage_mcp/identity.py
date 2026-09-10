"""
Turns a raw client IP into an HMAC-SHA256 hash before it ever reaches
capture.py -- same IP_SALT-based anonymization mirage-core already uses for
its published command exports. Lets sessions.jsonl show "same connector
reconnected" vs "a new one showed up" without ever storing the address
itself.

IP_SALT must be set for hashing to produce a stable, non-guessable result;
see .env.example. Never log the raw IP anywhere, including in error paths.
"""

import hashlib
import hmac
import os


def hash_ip(ip: str) -> str | None:
    salt = os.environ.get("IP_SALT")
    if not salt:
        return None
    return hmac.new(salt.encode(), ip.encode(), hashlib.sha256).hexdigest()[:16]

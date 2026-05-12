"""
Rate Limiting Middleware — Pareeksha Gurukul Refund Bot
Prevents spam by throttling rapid successive messages.
"""

import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# user_id → last_message_timestamp
_last_seen: dict[int, float] = defaultdict(float)


def is_rate_limited(user_id: int, limit_seconds: int = 3) -> bool:
    """Return True if user is sending messages too fast."""
    now = time.time()
    last = _last_seen[user_id]
    if now - last < limit_seconds:
        return True
    _last_seen[user_id] = now
    return False

"""Short-term bearer tokens for the Bedrock Mantle (OpenAI-compatible) endpoint.

Mantle (``https://bedrock-mantle.<region>.api.aws/v1``) is Bedrock's OpenAI-compatible data
plane and authenticates with Bedrock API keys sent as ``Authorization: Bearer``. Long-term
keys require IAM self-service permissions the runtime identity may not have, so we derive
short-term tokens (valid 12h) from the ambient AWS credential chain and cache them per
region with a comfortable refresh margin.
"""

from __future__ import annotations

import time

from aws_bedrock_token_generator import provide_token

# Tokens are valid for 12h; refresh an hour early so in-flight requests never race expiry.
_TOKEN_TTL_SECONDS = 11 * 60 * 60

_cache: dict[str, tuple[str, float]] = {}  # region -> (token, expires_at_monotonic)


def get_mantle_token(region: str) -> str:
    """Return a cached short-term bearer token for the Mantle endpoint in ``region``."""
    cached = _cache.get(region)
    now = time.monotonic()
    if cached is not None and cached[1] > now:
        return cached[0]
    token = str(provide_token(region=region))
    _cache[region] = (token, now + _TOKEN_TTL_SECONDS)
    return token

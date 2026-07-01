"""Short-code generation: random base62 strings, not a sequential counter,
so codes are non-enumerable (a caller can't guess link N+1 from link N)."""
from __future__ import annotations

import secrets

from storage import InMemoryStore

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
DEFAULT_CODE_LENGTH = 7

# Bounded retries on collision. At length 7 the keyspace is 62^7 (~3.5e12),
# so collisions are astronomically unlikely; the bound exists purely to turn
# a hypothetical pathological case into a clear error instead of a hang.
MAX_GENERATION_ATTEMPTS = 10


def _random_code(length: int) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def generate_code(store: InMemoryStore, length: int = DEFAULT_CODE_LENGTH) -> str:
    for _ in range(MAX_GENERATION_ATTEMPTS):
        code = _random_code(length)
        if not store.exists(code):
            return code
    raise RuntimeError(
        f"failed to generate a unique code after {MAX_GENERATION_ATTEMPTS} attempts"
    )

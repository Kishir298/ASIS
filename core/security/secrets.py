"""
Secret handling utilities.

Secrets should come from the environment or another secure
credential provider, never from committed source code.
"""

from __future__ import annotations

import os


def get_secret(name: str) -> str | None:
    """
    Retrieve a secret from an environment variable.

    Empty values are treated as missing.
    """
    value = os.getenv(name)

    if value is None:
        return None

    value = value.strip()

    return value or None


def require_secret(name: str) -> str:
    """
    Retrieve a required secret.

    Raises:
        RuntimeError: If the secret is not configured.
    """
    value = get_secret(name)

    if value is None:
        raise RuntimeError(
            f"Required secret '{name}' is not configured."
        )

    return value
"""
Confirmation handling for potentially dangerous Forza operations.
"""

from __future__ import annotations

from .permissions import PermissionLevel, requires_confirmation


def request_confirmation(
    action: str,
    level: PermissionLevel,
) -> bool:
    """
    Ask the user to confirm a potentially dangerous operation.

    Returns True when the action is approved.
    """
    if not requires_confirmation(level):
        return True

    print()
    print("Forza security confirmation required.")
    print(f"Action: {action}")
    print(f"Risk level: {level.name}")
    print("Type 'yes' to continue.")

    response = input("> ").strip().lower()

    return response == "yes"
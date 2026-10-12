"""Desktop notifications — replaces UserNotifications with notify-send.

Notifications are cosmetic: a failure here is swallowed, never surfaced as an
error, and never allowed to interrupt a poll.
"""

from __future__ import annotations

import shutil
import subprocess

APP_NAME = "PokeTokenBar"
ICON = "utilities-system-monitor"


def available() -> bool:
    return shutil.which("notify-send") is not None


def send(title: str, body: str = "", urgency: str = "normal") -> bool:
    """Post one notification. Returns whether it was dispatched."""
    if not available():
        return False
    try:
        subprocess.run(
            [
                "notify-send",
                "--app-name", APP_NAME,
                "--icon", ICON,
                "--urgency", urgency,
                title,
                body,
            ],
            check=False,
            timeout=5,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


class Notifier:
    """Edge-triggered notifications for companion and limit events."""

    def __init__(self, send_fn=send) -> None:
        self._send = send_fn
        # kind -> highest tier already announced (1 = warn, 2 = crit).
        self._limit_tier: dict[str, int] = {}

    def companion(self, events, name: str | None = None) -> None:
        if events is None:
            return
        label = name or "Your companion"
        if events.hatched is not None:
            self._send("An egg hatched!", f"{label} joined you.")
        if events.evolved_to is not None:
            self._send("Evolution!", f"{label} evolved.")
        if events.graduated is not None:
            self._send("Graduated!", f"{label} joined your Pokedex.")

    def limits(self, windows: dict[str, float], warn: float, crit: float) -> None:
        """Announce a window crossing warn or crit, once per crossing.

        Keyed by window kind alone. The Swift app re-notified on every refresh
        when volatile fields such as resets_at entered the key.
        """
        for key, utilization in windows.items():
            # "<account-id>:session" with several accounts; the label depends on
            # the window, the edge state on the whole key.
            kind = key.rsplit(":", 1)[-1]
            tier = 2 if utilization >= crit else (1 if utilization >= warn else 0)
            previous = self._limit_tier.get(key, 0)
            if tier == 0:
                self._limit_tier.pop(key, None)  # rearm
                continue
            if tier <= previous:
                continue
            self._limit_tier[key] = tier
            label = "5-hour" if kind == "session" else "weekly"
            self._send(
                f"{label.capitalize()} limit at {utilization:.0f}%",
                "Usage is close to the cap." if tier == 1 else "Usage is nearly exhausted.",
                urgency="critical" if tier == 2 else "normal",
            )

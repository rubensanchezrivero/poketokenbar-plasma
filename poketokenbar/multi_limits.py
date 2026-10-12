"""Limits for every configured Claude account.

One `LimitsSource` per account, so each keeps its own TTL and its own backoff:
a 429 or an expired login on one account must not stop the others from
reporting. Accounts are re-discovered on every poll, so logging into a new one
shows up without restarting the daemon.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from . import accounts as accounts_mod
from . import limits
from .accounts import Account
from .limits_source import LimitsSource


def _fetch_for(account: Account) -> limits.LimitStatus:
    """Fetch one account's limits using that account's own credentials."""
    credential = limits.read_credentials(account.credentials_path)
    status = limits.parse(limits.fetch(credential))
    status.subscription_type = credential.subscription_type
    status.rate_limit_tier = credential.rate_limit_tier
    status.account = {
        "uuid": account.uuid,
        "email": account.email,
        "display_name": account.display_name,
        "organization": account.organization,
    }
    return status


def _window(w) -> dict | None:
    if w is None:
        return None
    return {
        "utilization": w.utilization,
        "resets_at": w.resets_at,
        "severity": w.severity,
    }


def busiest(rows: list[dict]) -> dict | None:
    """The account closest to a cap — what the panel shows.

    Ranked by the WORST of its two windows, not by session alone. Ranking
    session-first hides the account that matters: one at 35% session but 86%
    weekly is far nearer a wall than one at 66% session and 14% weekly, yet a
    session-first rank would show the latter.

    An account with no data still ranks last rather than being dropped, so the
    panel renders something before the first successful fetch.
    """
    if not rows:
        return None

    def rank(row: dict) -> tuple[int, float]:
        values = [
            float(w.get("utilization") or 0.0)
            for w in (row.get("session"), row.get("weekly"))
            if w is not None
        ]
        if not values:
            return (0, 0.0)
        return (1, max(values))

    return max(rows, key=rank)


class MultiLimitsSource:
    def __init__(
        self,
        discover: Callable[[], list[Account]] | None = None,
        fetch: Callable[[Account], limits.LimitStatus] | None = None,
        clock: Callable[[], float] = time.monotonic,
        ttl: float = 300.0,
    ) -> None:
        self._discover = discover or accounts_mod.discover
        self._fetch = fetch or _fetch_for
        self._clock = clock
        self._ttl = ttl
        self._sources: dict[str, LimitsSource] = {}

    def _source_for(self, account: Account) -> LimitsSource:
        source = self._sources.get(account.id)
        if source is None:
            source = LimitsSource(
                fetch=lambda a=account: self._fetch(a), clock=self._clock, ttl=self._ttl
            )
            self._sources[account.id] = source
        return source

    def invalidate(self) -> None:
        for source in self._sources.values():
            source.invalidate()

    def get(self) -> list[dict]:
        """One row per account, in discovery order."""
        try:
            found = self._discover()
        except Exception:
            found = []

        rows: list[dict] = []
        live: set[str] = set()
        for account in found:
            live.add(account.id)
            source = self._source_for(account)
            status = source.get()
            rows.append(
                {
                    "id": account.id,
                    "short_label": account.short_label,
                    "display_name": account.display_name,
                    "email": account.email,
                    "organization": account.organization,
                    "config_dir": str(account.config_dir),
                    "plan": (status.subscription_type if status else None) or account.plan,
                    "session": _window(status.session if status else None),
                    "weekly": _window(status.weekly if status else None),
                    "error": source.last_error,
                }
            )

        # Drop state for accounts that are gone, so a logged-out account does
        # not keep a stale cache alive forever.
        for account_id in list(self._sources):
            if account_id not in live:
                del self._sources[account_id]

        return rows

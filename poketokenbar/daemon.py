"""poketokend — polls providers, writes state.json, drains commands."""

from __future__ import annotations

import os
import time
from pathlib import Path

from . import commands, config, state
from .companion_store import CompanionStore
from .burn import BurnTracker
from .notify import Notifier
from .status import StatusChecker
from .limits_source import LimitsSource
from .multi_limits import MultiLimitsSource, busiest
from .pokeapi import PokeAPI
from .sprites import SpriteStore
from .cache import ScanCache
from .models import DailyUsage


def _status_from_row(row: dict):
    """Rebuild a LimitStatus from an account row, for the panel and burn."""
    from . import limits as _limits

    status = _limits.LimitStatus()
    for key in ("session", "weekly"):
        window = row.get(key)
        if window is None:
            continue
        setattr(
            status,
            key,
            _limits.LimitWindow(
                float(window.get("utilization") or 0.0),
                window.get("resets_at"),
                window.get("severity"),
            ),
        )
    status.subscription_type = row.get("plan")
    status.account = {
        "uuid": row.get("id", ""),
        "email": row.get("email", ""),
        "display_name": row.get("display_name", ""),
        "organization": row.get("organization", ""),
    }
    return status


def _windows_by_account(rows: list, fallback) -> dict:
    """Utilization per account+window, e.g. {"<id>:session": 71.0}."""
    out: dict = {}
    if rows:
        for row in rows:
            for kind in ("session", "weekly"):
                window = row.get(kind)
                if window is not None:
                    out[f"{row['id']}:{kind}"] = float(window.get("utilization") or 0.0)
        return out
    if fallback is not None:
        if fallback.session is not None:
            out["session"] = fallback.session.utilization
        if fallback.weekly is not None:
            out["weekly"] = fallback.weekly.utilization
    return out


class Daemon:
    def __init__(
        self, state_path: Path, config_path: Path, cache, providers,
        limits_source=None, companion_store=None, notifier=None,
        burn_tracker=None, status_checker=None, accounts_source=None,
    ) -> None:
        self.state_path = state_path
        self.config_path = config_path
        self.cache = cache
        self.providers = providers
        # Injected so tests never reach the network. None disables limits.
        self.limits_source = limits_source
        self.companion_store = companion_store
        self.notifier = notifier
        self.burn = burn_tracker
        # Which account the last limits belonged to. Switching accounts changes
        # what the percentages mean, so cached limits and burn history from the
        # previous account must not carry over.
        self._account_uuid: str | None = None
        # Every configured Claude account, for per-account limits.
        self.accounts_source = accounts_source
        self.status_checker = status_checker
        self.spool: Path | None = None
        self.config_values = config.load(config_path)

    def poll_once(self) -> dict:
        errors: list[str] = []
        for command in commands.drain(spool=self.spool):
            name = command.get("name")
            if name == "refresh":
                # Manual refresh: drop cached limits so the next fetch is live.
                if self.limits_source is not None:
                    self.limits_source.invalidate()
            elif name == "reload_config":
                self.config_values = config.load(self.config_path)
            elif name in ("export", "import") and self.companion_store is not None:
                target = (command.get("args") or {}).get("path", "")
                try:
                    from . import transfer

                    if name == "export":
                        written = transfer.export_to(
                            Path(target), self.companion_store.state
                        )
                        message = f"exported to {written}"
                    else:
                        self.companion_store.state = transfer.import_from(Path(target))
                        message = "save imported"
                    if self.notifier is not None:
                        self.notifier._send("PokeTokenBar", message)
                except Exception as exc:
                    errors.append(f"{name}: {exc}")
            elif name in ("buy", "use") and self.companion_store is not None:
                key = (command.get("args") or {}).get("key", "")
                try:
                    if name == "buy":
                        message = self.companion_store.buy(key)
                    else:
                        message = self.companion_store.use_item(key)
                    if self.notifier is not None:
                        self.notifier._send("PokeTokenBar", message)
                except Exception as exc:
                    errors.append(f"{name}: {exc}")

        daily_by_provider: dict[str, DailyUsage] = {}
        for provider in self.providers:
            try:
                daily = provider.fetch_daily()
            except Exception as exc:  # per-provider isolation
                errors.append(f"{provider.id}: {exc}")
                continue
            if daily is not None:
                daily_by_provider[provider.id] = daily

        periods: dict = {}
        for provider in self.providers:
            fetch_periods = getattr(provider, "fetch_periods", None)
            if fetch_periods is None:
                continue
            try:
                result = fetch_periods()
            except Exception as exc:
                errors.append(f"{provider.id} periods: {exc}")
                continue
            for key in ("week", "month"):
                bucket = periods.setdefault(key, {"tokens": 0, "cost": 0.0})
                bucket["tokens"] += result[key]["tokens"]
                bucket["cost"] += result[key]["cost"]

        account_rows: list = []
        limit_status = None
        if self.accounts_source is not None:
            # Per-account limits. One account's failure or rate limit must not
            # hide the others, so each is fetched and cached independently.
            try:
                account_rows = self.accounts_source.get()
            except Exception as exc:
                errors.append(f"accounts: {exc}")
            for row in account_rows:
                if row.get("error"):
                    errors.append(f"{row['short_label']}: {row['error']}")
            # The panel shows one account: the one nearest a cap.
            lead = busiest(account_rows)
            if lead is not None:
                limit_status = _status_from_row(lead)
        elif self.limits_source is not None:
            # Single-account fallback (tests, or a host with one config dir).
            limit_status = self.limits_source.get()
            if self.limits_source.last_error:
                errors.append(f"limits: {self.limits_source.last_error}")

        companion_payload = None
        if self.companion_store is not None:
            try:
                # One language, not two. The catalogue reads config while the
                # companion reads the save, so they must be kept in step or the
                # popup renders half-translated.
                self.companion_store.state.language = str(
                    self.config_values.get("language", "en")
                )
                self.companion_store.update(
                    {pid: d.total_tokens for pid, d in daily_by_provider.items()}
                )
                today_total = sum(x.total_tokens for x in daily_by_provider.values())
                warn = float(self.config_values.get("warn_threshold", 80))
                limit_warning = False
                if limit_status is not None and limit_status.session is not None:
                    limit_warning = limit_status.session.utilization >= warn
                companion_payload = self.companion_store.payload(
                    today_tokens=today_total, limit_warning=limit_warning
                )
                # Candy and notifications ride on fresh limits, keyed per
                # account. Keying by window alone would let the panel's "busiest"
                # account change and re-grant for a window already paid out.
                windows = _windows_by_account(account_rows, limit_status)
                if windows:
                    if self.burn is not None:
                        for key, utilization in windows.items():
                            self.burn.record(key, utilization)
                    self.companion_store.grant_candy(windows)
                    if self.notifier is not None and self.config_values.get(
                        "limit_notifications", True
                    ):
                        self.notifier.limits(
                            windows,
                            float(self.config_values.get("warn_threshold", 80)),
                            float(self.config_values.get("crit_threshold", 95)),
                        )
                if self.notifier is not None and self.config_values.get(
                    "companion_notifications", True
                ):
                    self.notifier.companion(
                        self.companion_store.last_events,
                        companion_payload.get("name"),
                    )
                    self.companion_store.last_events = None
            except Exception as exc:
                # The companion is cosmetic; never let it break the numbers.
                errors.append(f"companion: {exc}")

        status_payload = None
        if self.status_checker is not None and self.config_values.get(
            "status_checks_enabled", True
        ):
            try:
                status_payload = self.status_checker.get()
            except Exception as exc:
                errors.append(f"status: {exc}")

        payload = state.build(
            daily_by_provider,
            self.config_values,
            errors,
            limit_status=limit_status,
            companion_payload=companion_payload,
            shop_payload=self.companion_store.shop_payload() if self.companion_store else None,
            bag_payload=self.companion_store.bag_payload() if self.companion_store else None,
            dex_payload=self.companion_store.dex_payload() if self.companion_store else None,
            catch_log=self.companion_store.catch_log_payload() if self.companion_store else None,
            rarity_counts=self.companion_store.rarity_counts() if self.companion_store else None,
            catch_counts=self.companion_store.catch_rarity_counts() if self.companion_store else None,
            periods=periods,
            burn=self.burn.payload() if self.burn is not None else None,
            provider_status=status_payload,
            accounts=account_rows,
            celebration=self.companion_store.celebration if self.companion_store else None,
        )
        state.write(self.state_path, payload)
        # Cleared after publishing so the banner shows once rather than
        # persisting until the next hatch.
        if self.companion_store is not None:
            self.companion_store.celebration = None
        return payload

    def run(self) -> None:
        while True:
            self.poll_once()
            interval = int(self.config_values.get("refresh_interval", 120))
            # Sleep in short slices so a queued command is picked up promptly
            # without re-scanning the logs every second.
            waited = 0
            while waited < interval:
                time.sleep(min(2, interval - waited))
                waited += 2
                if self._has_commands():
                    break

    def _has_commands(self) -> bool:
        spool = self.spool or commands.spool_dir()
        return spool.is_dir() and any(spool.glob("*.json"))


def main() -> int:
    from .providers.claude import ClaudeProvider
    from .providers.codex import CodexProvider

    cache_base = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    cache = ScanCache(Path(cache_base) / "poketokenbar" / "scan.db")
    daemon = Daemon(
        state_path=state.default_path(),
        config_path=config.default_path(),
        cache=cache,
        providers=[ClaudeProvider(cache=cache), CodexProvider(cache=cache)],
        limits_source=None,
        accounts_source=MultiLimitsSource(),
        companion_store=CompanionStore(
            api=PokeAPI(), sprite_store=SpriteStore()
        ),
        notifier=Notifier(),
        burn_tracker=BurnTracker(),
        status_checker=StatusChecker(),
    )
    try:
        daemon.run()
    except KeyboardInterrupt:
        return 0
    finally:
        cache.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

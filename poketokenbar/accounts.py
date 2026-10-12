"""Discovery of every Claude account configured on this machine.

Claude Code keeps one config directory per account, selected with
`CLAUDE_CONFIG_DIR` — typically `~/.claude` plus siblings like `~/.claude-work`.
Each holds its own `.credentials.json`, so each has its own 5-hour and weekly
limits.

Usage logs are a different matter. Secondary dirs commonly symlink `projects/`
back to the default one, and log lines carry no account marker, so token totals
cannot be attributed per account — they are inherently combined. Only the limits
are per-account, which is exactly what this module exists to enumerate.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DIR_NAME = ".claude"
PREFIX = ".claude"


@dataclass(slots=True)
class Account:
    config_dir: Path
    credentials_path: Path
    uuid: str
    email: str
    organization: str
    plan: str
    short_label: str = ""

    @property
    def display_name(self) -> str:
        """Longest useful name: organisation, else email, else the directory."""
        return self.organization or self.email or self.config_dir.name

    @property
    def id(self) -> str:
        """Stable key for per-account caches and notification state.

        The uuid when known, else the directory — never the email, which can be
        absent on a config that has credentials but no profile yet.
        """
        return self.uuid or str(self.config_dir)


def _read_json(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _identity_for(config_dir: Path) -> dict:
    """oauthAccount for a config dir.

    The default `~/.claude` stores it in the sibling `~/.claude.json`; secondary
    dirs keep their own copy inside the directory. Check inside first so a
    secondary dir never falls back to the default account's identity.
    """
    inside = _read_json(config_dir / ".claude.json").get("oauthAccount")
    if isinstance(inside, dict):
        return inside
    sibling = _read_json(config_dir.with_name(config_dir.name + ".json")).get("oauthAccount")
    return sibling if isinstance(sibling, dict) else {}


def _candidate_dirs(home: Path, env: Mapping[str, str]) -> list[Path]:
    out: list[Path] = []
    try:
        entries = sorted(home.iterdir())
    except OSError:
        entries = []
    for entry in entries:
        if not entry.is_dir():
            continue
        name = entry.name
        # `.claude` itself, or `.claude-<something>`. A bare prefix match would
        # also catch unrelated names like `.claudette`.
        if name == DEFAULT_DIR_NAME or name.startswith(PREFIX + "-"):
            out.append(entry)

    configured = env.get("CLAUDE_CONFIG_DIR")
    if configured:
        out.append(Path(configured).expanduser())
    return out


def _short_label(account: Account, taken: set[str]) -> str:
    """Two-ish character tag for the panel.

    Derived from the directory suffix (`.claude-ingenius` -> IN,
    `.claude-p2` -> P2) because that is what the person named it. The default
    dir has no suffix, so it falls back to the organisation or email.
    """
    name = account.config_dir.name
    if name.startswith(PREFIX + "-"):
        source = name[len(PREFIX) + 1 :]
    else:
        source = account.organization or account.email or name.lstrip(".")

    cleaned = "".join(ch for ch in source if ch.isalnum())
    base = (cleaned[:2] or "CL").upper()

    label = base
    suffix = 2
    while label in taken:
        # Two different dirs can shorten to the same two letters; widening keeps
        # the panel unambiguous rather than showing the same tag twice.
        label = (base[:1] + str(suffix)).upper()
        suffix += 1
    taken.add(label)
    return label


def discover(home: Path | None = None, env: Mapping[str, str] | None = None) -> list[Account]:
    """Every account with usable credentials, default dir first.

    Deduplicated on account uuid: two directories pointing at one account would
    otherwise double that account's limits in the UI.
    """
    home = home or Path.home()
    env = os.environ if env is None else env

    found: list[Account] = []
    seen_ids: set[str] = set()
    seen_dirs: set[Path] = set()

    for config_dir in _candidate_dirs(home, env):
        try:
            resolved = config_dir.resolve()
        except OSError:
            continue
        if resolved in seen_dirs:
            continue

        credentials_path = config_dir / ".credentials.json"
        oauth = _read_json(credentials_path).get("claudeAiOauth")
        if not isinstance(oauth, dict) or not oauth.get("accessToken"):
            # No account OAuth (missing file, or only MCP server state): there
            # are no limits to fetch, so it is not an account.
            continue
        seen_dirs.add(resolved)

        identity = _identity_for(config_dir)
        account = Account(
            config_dir=config_dir,
            credentials_path=credentials_path,
            uuid=str(identity.get("accountUuid") or ""),
            email=str(identity.get("emailAddress") or ""),
            organization=str(identity.get("organizationName") or ""),
            plan=str(oauth.get("subscriptionType") or ""),
        )
        if account.id in seen_ids:
            continue
        seen_ids.add(account.id)
        found.append(account)

    # Default dir first, then alphabetical, so panel labels keep a stable order
    # between polls rather than reshuffling.
    found.sort(key=lambda a: (a.config_dir.name != DEFAULT_DIR_NAME, a.config_dir.name))

    taken: set[str] = set()
    for account in found:
        account.short_label = _short_label(account, taken)
    return found

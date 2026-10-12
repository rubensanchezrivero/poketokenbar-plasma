"""Shop, bag, and rare-candy grants — ports the economy half of CompanionStore.

Tokens serve two roles at once: an unspendable growth meter
(used_since_install) and a spendable wallet (minus spent_tokens). Buying never
rewinds growth; it only debits the wallet.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import balance, companion
from .balance import Rarity
from .companion import CompanionState


class ShopError(Exception):
    """A purchase that cannot proceed (unknown item, funds, or state)."""


@dataclass(slots=True)
class ShopEntry:
    key: str
    kind: str  # "item" | "egg"
    price: int
    label: str
    owned: bool = False


def entries(state: CompanionState) -> list[ShopEntry]:
    """Everything on sale, cheapest first."""
    out = [
        ShopEntry("rareCandy", "item", balance.RARE_CANDY_PRICE, "Rare Candy"),
        ShopEntry("mint", "item", balance.MINT_PRICE, "Mint"),
        ShopEntry(
            "shinyCharm",
            "item",
            balance.SHINY_CHARM_PRICE,
            "Shiny Charm",
            # Passive and permanent: held, never consumed, bought once.
            owned=state.inventory.get("shinyCharm", 0) > 0,
        ),
    ]
    for tier in balance.EGG_SHOP_TIERS:
        key = f"egg:{tier}" if tier else "egg"
        label = {
            None: "Pokemon Egg",
            Rarity.UNCOMMON: "Uncommon Egg",
            Rarity.RARE: "Rare Egg",
        }[tier]
        out.append(ShopEntry(key, "egg", balance.egg_price(tier), label))
    return sorted(out, key=lambda e: e.price)


def _debit(state: CompanionState, price: int) -> None:
    if state.spendable_tokens < price:
        raise ShopError(
            f"not enough tokens: need {price:,}, have {state.spendable_tokens:,}"
        )
    state.spent_tokens += price


def buy(state: CompanionState, key: str) -> str:
    """Purchase one shop entry. Returns a short description of what happened."""
    entry = next((e for e in entries(state) if e.key == key), None)
    if entry is None:
        raise ShopError(f"unknown shop item: {key}")

    if entry.kind == "item":
        if entry.key == "shinyCharm" and entry.owned:
            raise ShopError("shiny charm is already held")
        _debit(state, entry.price)
        state.inventory[entry.key] = state.inventory.get(entry.key, 0) + 1
        return f"bought {entry.label}"

    # Eggs replace the current companion outright.
    tier = {"egg": None, f"egg:{Rarity.UNCOMMON}": Rarity.UNCOMMON,
            f"egg:{Rarity.RARE}": Rarity.RARE}[entry.key]
    _debit(state, entry.price)
    # The discarded companion is NOT graduated: it never entered the dex and
    # must not affect collected_finals either — as if it had never hatched.
    state.active = None
    state.egg_usage = 0
    state.egg_tier = tier
    state.pending_hatch_id = None
    return f"bought {entry.label}"


def use_item(state: CompanionState, key: str, rng=None) -> str:
    """Consume one held item."""
    held = state.inventory.get(key, 0)
    if held <= 0:
        raise ShopError(f"no {key} in bag")

    if key == "rareCandy":
        if state.active is None:
            raise ShopError("candy needs a hatched companion")
        state.inventory[key] = held - 1
        # Routed through apply_usage so carry-over, evolution, and graduation
        # all behave exactly as they do for real usage.
        companion.apply_usage(state, balance.RARE_CANDY_XP, rng=rng)
        return "used Rare Candy"

    if key == "mint":
        if state.active is None:
            raise ShopError("mint needs a hatched companion")
        import random

        rng = rng or random.Random()
        state.inventory[key] = held - 1
        state.active.nature = companion.roll_nature(rng)
        return f"nature is now {state.active.nature}"

    raise ShopError(f"{key} cannot be used")


# --- rare candy grants -----------------------------------------------------


def window_key(kind: str) -> str:
    """Stable identifier for a limit window.

    Must never include volatile fields such as resets_at. Including them made
    the Swift app re-notify on every refresh, because a rolling weekly window
    reports a new resets_at each time.
    """
    return f"limit:{kind}"


def grant_candy(state: CompanionState, windows: dict[str, float]) -> int:
    """Award candy for maxed limit windows. Edge-triggered.

    `windows` maps kind ("session"/"weekly") to utilization percent.
    Returns how many candies were granted.
    """
    granted = 0
    for key, utilization in windows.items():
        # Keys may be "<account-id>:session" when several accounts are
        # configured. The payout depends on the window, the edge state on the
        # whole key, so each account earns its own candy once.
        kind = key.rsplit(":", 1)[-1]
        key = window_key(key)
        tier = 2 if utilization >= 100 else (1 if utilization >= 80 else 0)
        previous = state.candy_grant_tier.get(key, 0)

        if tier == 0:
            # Dropped back below the warning line — rearm for next time.
            state.candy_grant_tier.pop(key, None)
            continue
        if tier <= previous:
            continue
        state.candy_grant_tier[key] = tier
        if tier < 2:
            continue  # only a full window pays out

        if not state.candy_feature_seeded:
            # First run must not pay out for a window that was already full
            # before the feature existed.
            continue
        amount = (
            balance.RARE_CANDY_WEEKLY_GRANT
            if kind == "weekly"
            else balance.RARE_CANDY_SESSION_GRANT
        )
        state.inventory["rareCandy"] = state.inventory.get("rareCandy", 0) + amount
        granted += amount

    state.candy_feature_seeded = True
    return granted

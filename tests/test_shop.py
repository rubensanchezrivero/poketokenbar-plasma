import random

import pytest

from poketokenbar import balance, shop
from poketokenbar.balance import Rarity
from poketokenbar.companion import CompanionState, EvoLine, apply_usage


def _with_mon(tokens=0):
    s = CompanionState()
    line = EvoLine(base_id=1, path_ids=[1, 2, 3], rarity=Rarity.COMMON)
    apply_usage(s, balance.EGG_HATCH_THRESHOLD, line_for_egg=line, rng=random.Random(1))
    s.used_since_install = tokens
    s.spent_tokens = 0
    return s


# --- shop listing ----------------------------------------------------------


def test_entries_are_sorted_by_price():
    prices = [e.price for e in shop.entries(CompanionState())]
    assert prices == sorted(prices)


def test_shiny_charm_shows_as_owned_once_held():
    s = CompanionState()
    s.inventory["shinyCharm"] = 1
    charm = next(e for e in shop.entries(s) if e.key == "shinyCharm")
    assert charm.owned is True


def test_three_egg_tiers_are_offered():
    keys = {e.key for e in shop.entries(CompanionState())}
    assert "egg" in keys and f"egg:{Rarity.UNCOMMON}" in keys and f"egg:{Rarity.RARE}" in keys


# --- buying ----------------------------------------------------------------


def test_buying_debits_the_wallet_but_not_growth():
    s = _with_mon(tokens=balance.RARE_CANDY_PRICE)
    shop.buy(s, "rareCandy")
    assert s.inventory["rareCandy"] == 1
    assert s.spent_tokens == balance.RARE_CANDY_PRICE
    assert s.used_since_install == balance.RARE_CANDY_PRICE  # growth never rewinds
    assert s.spendable_tokens == 0


def test_cannot_buy_without_funds():
    s = CompanionState()
    with pytest.raises(shop.ShopError):
        shop.buy(s, "rareCandy")


def test_unknown_item_is_rejected():
    with pytest.raises(shop.ShopError):
        shop.buy(CompanionState(), "masterball")


def test_shiny_charm_cannot_be_bought_twice():
    s = _with_mon(tokens=balance.SHINY_CHARM_PRICE * 2)
    shop.buy(s, "shinyCharm")
    with pytest.raises(shop.ShopError):
        shop.buy(s, "shinyCharm")


def test_buying_an_egg_discards_the_companion_without_dex_credit():
    # A discarded companion must vanish as if never hatched — no dex entry and
    # no collected_finals mark, or it would skew future branch diversity.
    s = _with_mon(tokens=balance.FRESH_EGG_PRICE)
    shop.buy(s, "egg")
    assert s.active is None
    assert s.dex == []
    assert s.collected_finals == set()
    assert s.egg_usage == 0


def test_premium_egg_records_its_guarantee():
    s = _with_mon(tokens=balance.egg_price(Rarity.RARE))
    shop.buy(s, f"egg:{Rarity.RARE}")
    assert s.egg_tier == Rarity.RARE


# --- using items -----------------------------------------------------------


def test_candy_grows_the_companion():
    s = _with_mon()
    s.inventory["rareCandy"] = 1
    before = s.active.used_at_stage
    shop.use_item(s, "rareCandy")
    assert s.active.used_at_stage == before + balance.RARE_CANDY_XP
    assert s.inventory["rareCandy"] == 0


def test_candy_cannot_be_used_on_an_egg():
    s = CompanionState()
    s.inventory["rareCandy"] = 1
    with pytest.raises(shop.ShopError):
        shop.use_item(s, "rareCandy")


def test_using_an_item_you_lack_is_rejected():
    with pytest.raises(shop.ShopError):
        shop.use_item(_with_mon(), "rareCandy")


def test_mint_rerolls_the_nature():
    s = _with_mon()
    s.inventory["mint"] = 1
    s.active.nature = "hardy"
    shop.use_item(s, "mint", rng=random.Random(5))
    assert s.active.nature in balance.NATURES
    assert s.inventory["mint"] == 0


# --- candy grants ----------------------------------------------------------


def test_first_run_does_not_pay_out_for_an_already_full_window():
    # Installing while a window sits at 100% must not backfill candy.
    s = CompanionState()
    assert shop.grant_candy(s, {"session": 100.0}) == 0
    assert s.inventory.get("rareCandy", 0) == 0


def test_full_session_window_grants_one_candy():
    s = CompanionState()
    shop.grant_candy(s, {"session": 10.0})  # seeds the feature
    assert shop.grant_candy(s, {"session": 100.0}) == balance.RARE_CANDY_SESSION_GRANT


def test_full_weekly_window_grants_five():
    s = CompanionState()
    shop.grant_candy(s, {"weekly": 10.0})
    assert shop.grant_candy(s, {"weekly": 100.0}) == balance.RARE_CANDY_WEEKLY_GRANT


def test_grant_is_edge_triggered_not_repeated_every_poll():
    s = CompanionState()
    shop.grant_candy(s, {"session": 10.0})
    first = shop.grant_candy(s, {"session": 100.0})
    second = shop.grant_candy(s, {"session": 100.0})
    third = shop.grant_candy(s, {"session": 100.0})
    assert first > 0
    assert second == 0 and third == 0


def test_window_rearms_after_dropping_below_the_warning_line():
    s = CompanionState()
    shop.grant_candy(s, {"session": 10.0})
    shop.grant_candy(s, {"session": 100.0})
    shop.grant_candy(s, {"session": 5.0})  # window reset
    assert shop.grant_candy(s, {"session": 100.0}) > 0


def test_window_key_excludes_volatile_fields():
    # A rolling weekly window reports a new resets_at on every fetch. Keying on
    # it re-fired the notification each refresh in the Swift app.
    assert shop.window_key("weekly") == "limit:weekly"
    assert "resets" not in shop.window_key("weekly")


# --- multi-account window keys ---------------------------------------------


def test_weekly_grant_survives_an_account_prefixed_key():
    # Keys became "<account-id>:weekly" for multi-account support. A plain
    # `kind == "weekly"` check silently downgrades the payout to the session
    # amount, which no existing test caught.
    s = CompanionState()
    shop.grant_candy(s, {"acct-1:weekly": 10.0})
    assert shop.grant_candy(s, {"acct-1:weekly": 100.0}) == balance.RARE_CANDY_WEEKLY_GRANT


def test_session_grant_survives_an_account_prefixed_key():
    s = CompanionState()
    shop.grant_candy(s, {"acct-1:session": 10.0})
    assert shop.grant_candy(s, {"acct-1:session": 100.0}) == balance.RARE_CANDY_SESSION_GRANT


def test_two_accounts_filling_the_same_window_both_pay_out():
    s = CompanionState()
    shop.grant_candy(s, {"a:session": 10.0, "b:session": 10.0})
    granted = shop.grant_candy(s, {"a:session": 100.0, "b:session": 100.0})
    assert granted == balance.RARE_CANDY_SESSION_GRANT * 2


def test_one_account_filling_twice_still_pays_out_once():
    s = CompanionState()
    shop.grant_candy(s, {"a:session": 10.0})
    first = shop.grant_candy(s, {"a:session": 100.0})
    second = shop.grant_candy(s, {"a:session": 100.0})
    assert first > 0 and second == 0

from pathlib import Path

from poketokenbar import limits
from poketokenbar.accounts import Account
from poketokenbar.multi_limits import MultiLimitsSource, busiest


def _account(label, uuid=None):
    return Account(
        config_dir=Path(f"/home/u/.claude-{label.lower()}"),
        credentials_path=Path(f"/home/u/.claude-{label.lower()}/.credentials.json"),
        uuid=uuid or label,
        email=f"{label.lower()}@x.com",
        organization="",
        plan="pro",
        short_label=label,
    )


def _status(session=None, weekly=None):
    entries = []
    if session is not None:
        entries.append({"kind": "session", "percent": session})
    if weekly is not None:
        entries.append({"kind": "weekly_all", "percent": weekly})
    return limits.parse({"limits": entries})


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, s):
        self.now += s


# --- busiest account -------------------------------------------------------


def test_busiest_uses_the_worst_window_not_session_alone():
    # Observed live: RU at 35% session / 86% weekly is nearer a wall than P2 at
    # 66% session / 14% weekly. Ranking by session alone showed the wrong one.
    rows = [
        {"short_label": "RU", "session": {"utilization": 35.0}, "weekly": {"utilization": 86.0}},
        {"short_label": "P2", "session": {"utilization": 66.0}, "weekly": {"utilization": 14.0}},
    ]
    assert busiest(rows)["short_label"] == "RU"


def test_busiest_picks_the_highest_session_utilization():
    rows = [
        {"short_label": "RU", "session": {"utilization": 12.0}, "weekly": None},
        {"short_label": "IN", "session": {"utilization": 71.0}, "weekly": None},
        {"short_label": "P2", "session": {"utilization": 29.0}, "weekly": None},
    ]
    assert busiest(rows)["short_label"] == "IN"


def test_busiest_falls_back_to_weekly_when_no_session():
    rows = [
        {"short_label": "RU", "session": None, "weekly": {"utilization": 40.0}},
        {"short_label": "IN", "session": None, "weekly": {"utilization": 5.0}},
    ]
    assert busiest(rows)["short_label"] == "RU"


def test_busiest_prefers_an_account_with_data_over_one_without():
    rows = [
        {"short_label": "RU", "session": None, "weekly": None},
        {"short_label": "IN", "session": {"utilization": 3.0}},
    ]
    assert busiest(rows)["short_label"] == "IN"


def test_busiest_of_nothing_is_none():
    assert busiest([]) is None


def test_busiest_with_no_data_anywhere_still_returns_a_row():
    # Something must render in the panel even before the first successful fetch.
    rows = [{"short_label": "RU", "session": None, "weekly": None}]
    assert busiest(rows)["short_label"] == "RU"


# --- per-account isolation -------------------------------------------------


def test_each_account_is_fetched_separately():
    calls = []

    def fetch_for(account):
        calls.append(account.short_label)
        return _status(session=10.0)

    src = MultiLimitsSource(
        discover=lambda: [_account("RU"), _account("IN")],
        fetch=fetch_for,
        clock=Clock(),
    )
    src.get()
    assert sorted(calls) == ["IN", "RU"]


def test_one_account_failing_does_not_hide_the_others():
    def fetch_for(account):
        if account.short_label == "RU":
            raise limits.LimitsError("boom")
        return _status(session=42.0)

    src = MultiLimitsSource(
        discover=lambda: [_account("RU"), _account("IN")],
        fetch=fetch_for,
        clock=Clock(),
    )
    rows = src.get()
    by_label = {r["short_label"]: r for r in rows}
    assert by_label["IN"]["session"]["utilization"] == 42.0
    assert "boom" in by_label["RU"]["error"]
    assert by_label["RU"]["session"] is None


def test_a_rate_limited_account_does_not_block_the_rest():
    def fetch_for(account):
        if account.short_label == "RU":
            raise limits.RateLimitedError(retry_after=300)
        return _status(session=5.0)

    clock = Clock()
    src = MultiLimitsSource(
        discover=lambda: [_account("RU"), _account("IN")],
        fetch=fetch_for,
        clock=clock,
    )
    src.get()
    rows = src.get()
    assert {r["short_label"] for r in rows} == {"RU", "IN"}
    assert next(r for r in rows if r["short_label"] == "IN")["session"] is not None


def test_each_account_caches_on_its_own_ttl():
    calls = []

    def fetch_for(account):
        calls.append(account.short_label)
        return _status(session=10.0)

    clock = Clock()
    src = MultiLimitsSource(
        discover=lambda: [_account("RU")], fetch=fetch_for, clock=clock, ttl=60
    )
    src.get()
    clock.advance(30)
    src.get()
    assert len(calls) == 1
    clock.advance(31)
    src.get()
    assert len(calls) == 2


def test_a_newly_added_account_is_picked_up():
    # Someone logs into a second account while the daemon runs.
    present = [_account("RU")]
    src = MultiLimitsSource(
        discover=lambda: list(present),
        fetch=lambda a: _status(session=1.0),
        clock=Clock(),
    )
    assert len(src.get()) == 1
    present.append(_account("IN"))
    assert len(src.get()) == 2


def test_a_removed_account_disappears():
    present = [_account("RU"), _account("IN")]
    src = MultiLimitsSource(
        discover=lambda: list(present),
        fetch=lambda a: _status(session=1.0),
        clock=Clock(),
    )
    assert len(src.get()) == 2
    present.pop()
    assert [r["short_label"] for r in src.get()] == ["RU"]


def test_rows_carry_identity_for_the_popup():
    src = MultiLimitsSource(
        discover=lambda: [_account("IN")],
        fetch=lambda a: _status(session=7.0, weekly=3.0),
        clock=Clock(),
    )
    row = src.get()[0]
    assert row["short_label"] == "IN"
    assert row["email"] == "in@x.com"
    assert row["plan"] == "pro"
    assert row["weekly"]["utilization"] == 3.0


def test_invalidate_forces_a_refetch_for_every_account():
    calls = []

    def fetch_for(account):
        calls.append(account.short_label)
        return _status(session=1.0)

    src = MultiLimitsSource(
        discover=lambda: [_account("RU"), _account("IN")],
        fetch=fetch_for,
        clock=Clock(),
        ttl=600,
    )
    src.get()
    src.invalidate()
    src.get()
    assert len(calls) == 4

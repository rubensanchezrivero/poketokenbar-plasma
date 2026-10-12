from poketokenbar.companion import DexEntry, GrowthEvents
from poketokenbar.notify import Notifier


class Spy:
    def __init__(self):
        self.sent = []

    def __call__(self, title, body="", urgency="normal"):
        self.sent.append((title, urgency))
        return True


def test_hatch_notifies():
    spy = Spy()
    Notifier(spy).companion(GrowthEvents(hatched=25))
    assert "hatched" in spy.sent[0][0].lower()


def test_evolution_and_graduation_notify():
    spy = Spy()
    Notifier(spy).companion(
        GrowthEvents(evolved_to=26, graduated=DexEntry(1, 3, [1, 2, 3], "common"))
    )
    assert len(spy.sent) == 2


def test_no_events_sends_nothing():
    spy = Spy()
    Notifier(spy).companion(GrowthEvents())
    Notifier(spy).companion(None)
    assert spy.sent == []


def test_limit_warning_fires_once_per_crossing():
    spy = Spy()
    n = Notifier(spy)
    n.limits({"session": 85.0}, warn=80, crit=95)
    n.limits({"session": 86.0}, warn=80, crit=95)
    n.limits({"session": 90.0}, warn=80, crit=95)
    assert len(spy.sent) == 1


def test_escalating_to_critical_fires_again():
    spy = Spy()
    n = Notifier(spy)
    n.limits({"session": 85.0}, warn=80, crit=95)
    n.limits({"session": 96.0}, warn=80, crit=95)
    assert len(spy.sent) == 2
    assert spy.sent[1][1] == "critical"


def test_dropping_below_warn_rearms():
    spy = Spy()
    n = Notifier(spy)
    n.limits({"session": 85.0}, warn=80, crit=95)
    n.limits({"session": 5.0}, warn=80, crit=95)  # window reset
    n.limits({"session": 85.0}, warn=80, crit=95)
    assert len(spy.sent) == 2


def test_below_warn_never_notifies():
    spy = Spy()
    Notifier(spy).limits({"session": 20.0, "weekly": 5.0}, warn=80, crit=95)
    assert spy.sent == []


def test_windows_are_tracked_independently():
    spy = Spy()
    n = Notifier(spy)
    n.limits({"session": 85.0, "weekly": 10.0}, warn=80, crit=95)
    n.limits({"session": 85.0, "weekly": 85.0}, warn=80, crit=95)
    assert len(spy.sent) == 2


def test_label_survives_an_account_prefixed_key():
    # Keys are "<account-id>:session" with several accounts; a plain equality
    # check against "session" labelled every alert "weekly".
    spy = Spy()
    Notifier(spy).limits({"acct-1:session": 85.0}, warn=80, crit=95)
    assert "5-hour" in spy.sent[0][0].lower()


def test_accounts_are_tracked_independently():
    spy = Spy()
    n = Notifier(spy)
    n.limits({"a:session": 85.0, "b:session": 10.0}, warn=80, crit=95)
    n.limits({"a:session": 85.0, "b:session": 85.0}, warn=80, crit=95)
    assert len(spy.sent) == 2

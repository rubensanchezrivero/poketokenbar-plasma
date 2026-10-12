import json

from poketokenbar import accounts


def _make(tmp_path, name, *, token, email, org=None, plan="pro", uuid=None, identity="inside"):
    """Create a Claude config dir.

    identity="inside"  -> <dir>/.claude.json   (how secondary dirs store it)
    identity="sibling" -> <dir>.json           (how the default ~/.claude does)
    """
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / ".credentials.json").write_text(
        json.dumps(
            {
                "claudeAiOauth": {
                    "accessToken": token,
                    "subscriptionType": plan,
                    "rateLimitTier": "default_claude_ai",
                }
            }
        ),
        encoding="utf-8",
    )
    body = json.dumps(
        {
            "oauthAccount": {
                "accountUuid": uuid or token,
                "emailAddress": email,
                "organizationName": org,
            }
        }
    )
    if identity == "inside":
        (d / ".claude.json").write_text(body, encoding="utf-8")
    else:
        (tmp_path / f"{name}.json").write_text(body, encoding="utf-8")
    return d


# --- discovery -------------------------------------------------------------


def test_finds_every_config_dir_with_credentials(tmp_path):
    _make(tmp_path, ".claude", token="a", email="a@x.com", identity="sibling")
    _make(tmp_path, ".claude-p2", token="b", email="b@x.com")
    _make(tmp_path, ".claude-ingenius", token="c", email="c@y.com", org="Ingenius")
    found = accounts.discover(home=tmp_path)
    assert {a.email for a in found} == {"a@x.com", "b@x.com", "c@y.com"}


def test_a_dir_without_credentials_is_ignored(tmp_path):
    _make(tmp_path, ".claude", token="a", email="a@x.com", identity="sibling")
    (tmp_path / ".claude-empty").mkdir()
    assert len(accounts.discover(home=tmp_path)) == 1


def test_unrelated_directories_are_ignored(tmp_path):
    _make(tmp_path, ".claude", token="a", email="a@x.com", identity="sibling")
    (tmp_path / ".config").mkdir()
    (tmp_path / ".claudette").mkdir()  # prefix match but no credentials
    assert len(accounts.discover(home=tmp_path)) == 1


def test_default_dir_reads_its_sibling_identity_file(tmp_path):
    # ~/.claude keeps oauthAccount in ~/.claude.json, outside the directory.
    _make(tmp_path, ".claude", token="a", email="main@x.com", identity="sibling")
    found = accounts.discover(home=tmp_path)
    assert found[0].email == "main@x.com"


def test_claude_config_dir_env_is_included(tmp_path):
    _make(tmp_path, ".claude", token="a", email="a@x.com", identity="sibling")
    extra = _make(tmp_path, "elsewhere", token="z", email="z@x.com")
    found = accounts.discover(home=tmp_path, env={"CLAUDE_CONFIG_DIR": str(extra)})
    assert "z@x.com" in {a.email for a in found}


def test_same_account_in_two_dirs_appears_once(tmp_path):
    # Deduplicated on account uuid, not path: two dirs pointing at one account
    # would otherwise double its limits in the UI.
    _make(tmp_path, ".claude", token="a", email="a@x.com", uuid="same", identity="sibling")
    _make(tmp_path, ".claude-copy", token="b", email="a@x.com", uuid="same")
    assert len(accounts.discover(home=tmp_path)) == 1


def test_discovery_is_stable_and_sorted(tmp_path):
    _make(tmp_path, ".claude-zz", token="z", email="z@x.com")
    _make(tmp_path, ".claude", token="a", email="a@x.com", identity="sibling")
    _make(tmp_path, ".claude-mm", token="m", email="m@x.com")
    # The default dir leads; the rest are alphabetical so the panel's label
    # order does not reshuffle between polls.
    assert [a.config_dir.name for a in accounts.discover(home=tmp_path)] == [
        ".claude",
        ".claude-mm",
        ".claude-zz",
    ]


def test_missing_identity_still_yields_an_account(tmp_path):
    # Credentials are what make limits fetchable; a missing .claude.json should
    # degrade the label, not drop the account.
    d = tmp_path / ".claude-bare"
    d.mkdir()
    (d / ".credentials.json").write_text(
        json.dumps({"claudeAiOauth": {"accessToken": "t"}}), encoding="utf-8"
    )
    found = accounts.discover(home=tmp_path)
    assert len(found) == 1
    assert found[0].email == ""
    assert found[0].short_label


def test_dir_without_account_oauth_is_skipped(tmp_path):
    # Only MCP OAuth state: no account to fetch limits for.
    d = tmp_path / ".claude-mcp"
    d.mkdir()
    (d / ".credentials.json").write_text(
        json.dumps({"mcpOAuth": {"server": {}}}), encoding="utf-8"
    )
    assert accounts.discover(home=tmp_path) == []


# --- labels ----------------------------------------------------------------


def test_short_label_comes_from_the_dir_suffix(tmp_path):
    _make(tmp_path, ".claude-ingenius", token="c", email="c@y.com", org="Ingenius")
    assert accounts.discover(home=tmp_path)[0].short_label == "IN"


def test_short_label_keeps_digits(tmp_path):
    _make(tmp_path, ".claude-p2", token="b", email="b@x.com")
    assert accounts.discover(home=tmp_path)[0].short_label == "P2"


def test_default_dir_labels_from_org_or_email(tmp_path):
    _make(tmp_path, ".claude", token="a", email="ruben@x.com", org="Ruben", identity="sibling")
    assert accounts.discover(home=tmp_path)[0].short_label == "RU"


def test_short_labels_are_unique(tmp_path):
    # Two dirs that would both shorten to "PE" must not render identically.
    _make(tmp_path, ".claude-personal", token="a", email="a@x.com")
    _make(tmp_path, ".claude-pets", token="b", email="b@x.com")
    labels = [a.short_label for a in accounts.discover(home=tmp_path)]
    assert len(set(labels)) == len(labels)


def test_display_name_prefers_org_then_email(tmp_path):
    _make(tmp_path, ".claude-ingenius", token="c", email="c@y.com", org="Ingenius")
    _make(tmp_path, ".claude-p2", token="b", email="b@x.com")
    by_dir = {a.config_dir.name: a for a in accounts.discover(home=tmp_path)}
    assert by_dir[".claude-ingenius"].display_name == "Ingenius"
    assert by_dir[".claude-p2"].display_name == "b@x.com"

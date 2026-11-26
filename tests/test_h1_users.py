from datetime import timedelta

from nflb.config import get_settings
from nflb.core import users
from nflb.db.models import User, utcnow
from nflb.db.session import session_scope


def test_settings_parse_allowed_ids():
    assert get_settings().allowed_user_ids == [111, 222]


def test_hash_is_stable_salted_and_not_plain():
    h = users.hash_user_id(111)
    assert h == users.hash_user_id(111)
    assert h != users.hash_user_id(222)
    assert "111" not in h and len(h) == 64


def test_consent_flow():
    uid = users.hash_user_id(111)
    assert not users.has_consent(uid)
    users.give_consent(uid, chat_id=999)
    assert users.has_consent(uid)


def test_history_keeps_only_last_turns():
    uid = users.hash_user_id(111)
    users.give_consent(uid, None)
    keep = get_settings().history_turns * 2
    for i in range(keep + 7):
        users.add_turn(uid, "user", f"m{i}")
    hist = users.get_history(uid)
    assert len(hist) == keep
    assert hist[-1]["content"] == f"m{keep + 6}"


def test_delete_removes_rows_and_files():
    uid = users.hash_user_id(111)
    users.give_consent(uid, 5)
    users.add_turn(uid, "user", "hola")
    folder = users.user_files_dir(uid)
    folder.mkdir(parents=True)
    (folder / "resumen.pdf").write_bytes(b"x")

    assert users.delete_user(uid)
    assert not users.has_consent(uid)
    assert users.get_history(uid) == []
    assert not folder.exists()


def test_purge_inactive():
    old, new = users.hash_user_id(111), users.hash_user_id(222)
    users.give_consent(old, None)
    users.give_consent(new, None)
    with session_scope() as s:
        s.get(User, old).last_seen_at = utcnow() - timedelta(days=31)
    assert users.purge_inactive(30) == 1
    assert not users.has_consent(old)
    assert users.has_consent(new)

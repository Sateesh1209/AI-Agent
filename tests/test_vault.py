"""Tests for the encrypted credential vault.

Run:  python tests/test_vault.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jarvis.vault import Vault  # noqa: E402


def _tmp_vault_path():
    return os.path.join(tempfile.mkdtemp(), "vault.enc")


def test_set_get_roundtrip():
    p = _tmp_vault_path()
    v = Vault("master-pass-123", path=p)
    v.set_credential("UDR.com", "sateesh@example.com", "s3cret!")
    got = v.get_credential("udr.com")
    assert got == {"username": "sateesh@example.com", "password": "s3cret!"}


def test_persists_and_reopens_with_same_password():
    p = _tmp_vault_path()
    Vault("pw", path=p).set_credential("workday", "user1", "pw1")
    reopened = Vault("pw", path=p)
    assert reopened.get_credential("workday")["password"] == "pw1"


def test_wrong_password_is_rejected():
    p = _tmp_vault_path()
    Vault("correct", path=p).set_credential("site", "u", "p")
    try:
        Vault("WRONG", path=p)
        assert False, "wrong password should have raised"
    except ValueError:
        pass


def test_find_for_url_and_list_and_delete():
    p = _tmp_vault_path()
    v = Vault("pw", path=p)
    v.set_credential("ultipro", "u", "p")
    match = v.find_for("https://recruiting2.ultipro.com/uni1027udrt/JobBoard")
    assert match and match["site"] == "ultipro"
    assert v.list_sites() == ["ultipro"]
    assert v.delete("ultipro") is True
    assert v.list_sites() == []


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in funcs:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\nAll {len(funcs)} tests passed.")

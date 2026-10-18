import builtins
import hashlib

import exitkit.audit as audit_module
from exitkit.audit import KNOWN_64, PUBLIC, is_fake, main as audit_main


def mixed_body():
    alphabet = "0123456789abcdef"
    body = "".join(alphabet[(i * 5 + 3) % 16] for i in range(40))
    assert not is_fake(body)
    assert body not in PUBLIC
    return body


def test_glued_hex_is_review(tmp_path, capsys):
    body = mixed_body()
    (tmp_path / "before.txt").write_text("cafe0x" + body + "\n", encoding="utf-8")
    (tmp_path / "after.txt").write_text(body + "ab\n", encoding="utf-8")
    assert audit_main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "RESULT: FAIL" in out
    assert "glued" in out
    assert out.count("REVIEW") >= 2


def test_public_permit2_multicall_and_fake_are_not_review(tmp_path, capsys):
    text = "\n".join([
        "multicall 0xcA11bde05977b3631167028862bE2a173976CA11 end",
        "permit2 0x000000000022D473030F116dDEE9F6B43aC78BA3 end",
        "fake 0x" + ("1" * 40) + " end",
        "native 0x" + ("e" * 40) + " end",
    ]) + "\n"
    (tmp_path / "pub.txt").write_text(text, encoding="utf-8")
    assert audit_main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "RESULT: PASS" in out
    assert "REVIEW" not in out


def test_known_topic_passes_and_a_split_address_does_not(tmp_path, capsys):
    topic = next(iter(KNOWN_64))
    (tmp_path / "topic.txt").write_text("0x" + topic + "\n", encoding="utf-8")
    assert audit_main([str(tmp_path)]) == 0
    capsys.readouterr()

    body = mixed_body()
    (tmp_path / "split.txt").write_text("0x" + body[:20] + "\n" + body[20:] + "\n", encoding="utf-8")
    assert audit_main([str(tmp_path)]) == 1
    assert "split across lines" in capsys.readouterr().out


def test_venv_is_skipped_and_the_same_address_outside_is_not(tmp_path, capsys):
    body = mixed_body()
    hidden = tmp_path / ".venv" / "lib.txt"
    hidden.parent.mkdir()
    hidden.write_text("0x" + body + "\n", encoding="utf-8")
    (tmp_path / "readme.txt").write_text("nothing to see\n", encoding="utf-8")
    assert audit_main([str(tmp_path)]) == 0
    capsys.readouterr()

    (tmp_path / "note.txt").write_text("0x" + body + "\n", encoding="utf-8")
    assert audit_main([str(tmp_path)]) == 1


def test_forbid_substring(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("alpha SECRET-MARKER omega\n", encoding="utf-8")
    assert audit_main([str(tmp_path), "--forbid", "SECRET-MARKER"]) == 1
    assert "FORBIDDEN" in capsys.readouterr().out


def test_missing_folder_is_error(tmp_path, capsys):
    missing = tmp_path / "missing"

    assert audit_main([str(missing)]) != 0
    out = capsys.readouterr().out
    assert "ERROR" in out
    assert "RESULT: PASS" not in out


def test_unreadable_file_is_error(tmp_path, capsys, monkeypatch):
    unreadable = tmp_path / "unreadable.txt"
    unreadable.write_text("nothing to see\n", encoding="utf-8")
    real_open = builtins.open

    def fail_unreadable(path, *args, **kwargs):
        if str(path) == str(unreadable):
            raise PermissionError("permission denied")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(audit_module, "open", fail_unreadable, raising=False)
    assert audit_main([str(tmp_path)]) != 0
    out = capsys.readouterr().out
    assert "ERROR" in out
    assert "unreadable.txt" in out
    assert "RESULT: PASS" not in out


def test_unreadable_folder_is_error(tmp_path, capsys, monkeypatch):
    unreadable = tmp_path / "unreadable"
    unreadable.mkdir()
    real_scandir = audit_module.os.scandir

    def fail_unreadable(path):
        if str(path) == str(unreadable):
            raise PermissionError(13, "Permission denied", str(unreadable))
        return real_scandir(path)

    monkeypatch.setattr(audit_module.os, "scandir", fail_unreadable)
    assert audit_main([str(tmp_path)]) != 0
    out = capsys.readouterr().out
    assert "ERROR" in out
    assert "unreadable" in out
    assert "RESULT: PASS" not in out


def test_unknown_64_hex_is_redacted(tmp_path, capsys):
    secret = hashlib.sha256(b"synthetic audit redaction regression").hexdigest()
    assert secret not in KNOWN_64
    assert not is_fake(secret)
    (tmp_path / "secret.txt").write_text(secret + "\n0x" + secret + "\n", encoding="utf-8")

    assert audit_main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert secret not in out
    redacted = secret[:4] + "…" + secret[-4:]
    assert f" {redacted}  [" in out
    assert f" 0x{redacted}  [" in out
    assert "secret.txt:1" in out
    assert "secret.txt:2" in out

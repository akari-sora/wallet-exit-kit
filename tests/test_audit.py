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

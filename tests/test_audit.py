import builtins
import hashlib

import pytest

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


@pytest.mark.parametrize("suffix", ["x", "X"])
def test_split_address_allows_nonhex_x_boundary(tmp_path, capsys, suffix):
    body = mixed_body()
    (tmp_path / "split.txt").write_text(body[:20] + "\n" + body[20:] + suffix + "\n")
    assert audit_main([str(tmp_path)]) == 1
    assert "address split across lines" in capsys.readouterr().out


@pytest.mark.parametrize("prefix", ["0x", "0X"])
def test_split_scan_does_not_join_a_prefix_from_the_next_line(tmp_path, capsys, prefix):
    secret = hashlib.sha256(b"synthetic split prefix regression").hexdigest()
    (tmp_path / "secret.txt").write_text(mixed_body()[:39] + "\n" + prefix + secret + "\n")
    assert audit_main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "address split across lines" not in out
    assert secret not in out


@pytest.mark.parametrize("length", [64, 65, 128])
@pytest.mark.parametrize("option", ["", "--unknown="])
def test_parser_errors_redact_long_hex(tmp_path, capsys, length, option):
    secret = (hashlib.sha256(b"synthetic parser redaction regression").hexdigest() * 2)[:length]
    with pytest.raises(SystemExit) as exc:
        audit_main([str(tmp_path), option + secret])
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unrecognized arguments" in captured.err
    assert secret not in captured.err
    assert secret[:4] + "…" + secret[-4:] + f" ({length} hex)" in captured.err


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

    assert audit_main([str(missing)]) == 2
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
    assert secret[24:-4] not in out
    assert "address split across lines" not in out
    redacted = secret[:4] + "…" + secret[-4:] + " (64 hex)"
    assert f" {redacted}  [" in out
    assert f" 0x{redacted}  [" in out
    assert "secret.txt:1" in out
    assert "secret.txt:2" in out


@pytest.mark.parametrize("form", ["bare", "glued", "padded", "long", "signature", "seed"])
@pytest.mark.parametrize("forbid", [False, True])
def test_64_hex_redaction_covers_alternate_output_paths(tmp_path, capsys, form, forbid):
    secret = hashlib.sha256(b"synthetic alternate redaction regression").hexdigest()
    if form == "padded":
        secret = "0" * 24 + mixed_body()
    run = {"long": secret + "a", "signature": secret * 2 + "ab",
           "seed": secret * 2}.get(form, secret)
    prefix = {"glued": "cafe0x", "padded": "0x", "signature": "0x"}.get(form, "")
    token = prefix + run
    (tmp_path / "secret.txt").write_text(token + "\n", encoding="utf-8")
    args = [str(tmp_path)]
    if forbid:
        args.extend(["--forbid", token])

    assert audit_main(args) == 1
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err
    assert "REVIEW" in captured.out
    assert "secret.txt:1" in captured.out
    assert "…" in captured.out
    redacted = prefix + run[:4] + "…" + run[-4:] + f" ({len(run)} hex)"
    assert redacted in captured.out
    if forbid:
        assert "FORBIDDEN substring" in captured.out
        assert f"FORBIDDEN substring {redacted!r}" in captured.out
        assert "forbidden_hits=1" in captured.out


@pytest.mark.parametrize("run", [next(iter(KNOWN_64)), "a" * 64, "ab" * 64])
def test_public_and_fake_long_hex_use_the_same_redaction(tmp_path, capsys, run):
    (tmp_path / "public.txt").write_text("0x" + run + "\n", encoding="utf-8")
    assert audit_main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "0x" + run[:4] + "…" + run[-4:] + f" ({len(run)} hex)" in out
    assert run[:5] not in out


@pytest.mark.parametrize("name", ["linked", ".venv"])
def test_symlinked_directory_is_an_error(tmp_path, capsys, name):
    folder = tmp_path / "scan"
    folder.mkdir()
    target = tmp_path / "outside"
    target.mkdir()
    (target / "private.txt").write_text("private content\n", encoding="utf-8")
    (folder / name).symlink_to(target, target_is_directory=True)

    assert audit_main([str(folder)]) == 1
    out = capsys.readouterr().out
    assert "ERROR" in out
    assert name in out
    assert "symlink" in out
    assert "read_errors=1" in out
    assert "RESULT: PASS" not in out


@pytest.mark.parametrize("exists", [False, True])
def test_long_hex_in_output_paths_is_redacted(tmp_path, capsys, exists):
    secret = hashlib.sha256(b"synthetic path redaction regression").hexdigest()
    folder = tmp_path / secret
    if exists:
        folder.mkdir()
        (folder / secret).write_text("0x" + mixed_body(), encoding="utf-8")
    assert audit_main([str(folder)]) != 0
    out = capsys.readouterr().out
    assert secret not in out
    assert secret[:4] + "…" + secret[-4:] + " (64 hex)" in out


AT = "@"  # split so this file does not match its own handle check


def test_python_decorators_are_not_social_handles(tmp_path, capsys):
    (tmp_path / "test_x.py").write_text(
        f"{AT}pytest.mark.parametrize('a', [1])\n    {AT}property\n{AT}staticmethod\ndef f(): pass\n")
    assert audit_main([str(tmp_path)]) == 0
    assert "social handle" not in capsys.readouterr().out


def test_handles_in_python_comments_and_docs_are_still_review(tmp_path, capsys):
    (tmp_path / "x.py").write_text(f"# ask {AT}alice_dev about this\n")
    (tmp_path / "notes.md").write_text(f"{AT}pytest\n")
    assert audit_main([str(tmp_path)]) != 0
    out = capsys.readouterr().out
    assert AT + "alice_dev" in out
    assert "notes.md" in out


def test_multiline_decorator_is_skipped_but_docstring_handle_is_review(tmp_path, capsys):
    (tmp_path / "test_y.py").write_text(
        f"{AT}pytest.mark.parametrize(\n    'a',\n    [1],\n)\ndef g(a): pass\n")
    assert audit_main([str(tmp_path)]) == 0
    capsys.readouterr()
    (tmp_path / "doc.py").write_text(f'"""Contact:\n{AT}alice_dev\n"""\nx = 1\n')
    assert audit_main([str(tmp_path)]) != 0
    assert AT + "alice_dev" in capsys.readouterr().out


def test_docstring_handle_before_a_class_like_line_is_review(tmp_path, capsys):
    (tmp_path / "doc2.py").write_text(f'"""Contact:\n{AT}alice_dev\nclass of 2026\n"""\n')
    assert audit_main([str(tmp_path)]) != 0
    assert AT + "alice_dev" in capsys.readouterr().out


def test_unparsable_python_keeps_handles_as_review(tmp_path, capsys):
    (tmp_path / "broken.py").write_text(f"{AT}alice_dev\ndef f(:\n")
    assert audit_main([str(tmp_path)]) != 0
    assert AT + "alice_dev" in capsys.readouterr().out


def test_vertical_tab_cannot_shift_decorator_line_numbers(tmp_path, capsys):
    (tmp_path / "vt.py").write_text(f'"""Contact:\v\v{AT}alice_dev\n"""\n{AT}d\ndef f(): pass\n')
    assert audit_main([str(tmp_path)]) != 0
    assert AT + "alice_dev" in capsys.readouterr().out


def test_profile_urls_and_long_handles_are_review(tmp_path, capsys):
    (tmp_path / "links.md").write_text(
        f"https://www.threads.net/{AT}alice_dev\nsee {AT}alice_developer_team\n")
    assert audit_main([str(tmp_path)]) != 0
    out = capsys.readouterr().out
    assert "profile URL" in out
    assert AT + "alice_developer_team" in out


def test_public_feed_url_on_other_hosts_is_not_a_profile_url(tmp_path, capsys):
    (tmp_path / "feeds.md").write_text(f"https://api.paragraph.com/blogs/rss/{AT}base\n")
    audit_main([str(tmp_path)])
    assert "profile URL" not in capsys.readouterr().out


def test_known_public_text_and_platform_path_pass(tmp_path, capsys):
    (tmp_path / "notify.md").write_text(
        f"Open {AT}BotFather, then check {AT}username and {AT}handle / {AT}handles.\n"
        "A label like name.eth is blocked.\n"
        "RULES = \"/ho" "me/box/agent-data/workflows/wallet-guardian-rules/SKILL.md\"\n")
    assert audit_main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "REVIEW" not in out
    assert "Telegram's official bot-creation account" in out
    assert "Grok Bot platform skill folder" in out


@pytest.mark.parametrize("text", [
    f"{AT}BotFather2",
    f"{AT}Username",
    f"{AT}alice_dev",
    "alice" ".eth",
    "/ho" "me/bob/notes",
    "/ho" "me/box/other/",
    "see /ho" "me/box/agent-data-copy/",
    "example.name" ".eth",
    "alice-name" ".eth",
    "/ho" "me/box/agent-data/../../example/private.txt",
    "/ho" "me/box/agent-data/./x/../../y",
    "name" ".eth.example",
    f"{AT}BotFather.foo",
    '"/ho' 'me/box/agent-data/a,b/../../private"',
    '"/ho' 'me/box/agent-data/.."',
    "/ho" "me/box/agent-data/x/..",
    "/ho" "me/box/agent-data/.",
])
def test_near_misses_of_public_text_stay_review(tmp_path, capsys, text):
    (tmp_path / "x.md").write_text(text + "\n")
    assert audit_main([str(tmp_path)]) != 0
    assert "REVIEW" in capsys.readouterr().out


def _sums_case(tmp_path, body=b"skill text\n"):
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "a.md").write_bytes(body)
    return hashlib.sha256(body).hexdigest()


def test_sha256sums_with_matching_file_hash_passes(tmp_path, capsys):
    digest = _sums_case(tmp_path)
    (tmp_path / "SHA256SUMS").write_text(f"{digest}  skills/a.md\n")
    assert audit_main([str(tmp_path)]) == 0
    assert "verified file hash" in capsys.readouterr().out


@pytest.mark.parametrize("make", ["wrong_hash", "escape", "other_file", "symlink", "missing"])
def test_sha256sums_hash_that_cannot_be_verified_stays_review(tmp_path, capsys, make):
    digest = _sums_case(tmp_path)
    if make == "wrong_hash":
        (tmp_path / "SHA256SUMS").write_text(f"{hashlib.sha256(b'x').hexdigest()}  skills/a.md\n")
    elif make == "escape":
        inner = tmp_path / "inner"
        inner.mkdir()
        (inner / "SHA256SUMS").write_text(f"{digest}  ../skills/a.md\n")
    elif make == "other_file":
        (tmp_path / "notes.md").write_text(f"{digest}  skills/a.md\n")
    elif make == "symlink":
        (tmp_path / "link.md").symlink_to(tmp_path / "skills" / "a.md")
        (tmp_path / "SHA256SUMS").write_text(f"{digest}  link.md\n")
    else:
        (tmp_path / "SHA256SUMS").write_text(f"{digest}  skills/gone.md\n")
    assert audit_main([str(tmp_path)]) != 0
    assert "REVIEW" in capsys.readouterr().out


def test_known_text_with_trailing_punctuation_still_passes(tmp_path, capsys):
    (tmp_path / "p.md").write_text(
        f"Ask {AT}BotFather. Then {AT}username, and name" ".eth.\n"
        '"/ho' 'me/box/agent-data/workflows/x/SKILL.md", done.\n')
    assert audit_main([str(tmp_path)]) == 0
    assert "REVIEW" not in capsys.readouterr().out

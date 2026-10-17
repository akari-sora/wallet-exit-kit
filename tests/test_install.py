import json
import os
from pathlib import Path

from exitkit.install import destination, main as install_main

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills" / "onchain-exit-assist").resolve()

TARGETS = {
    "claude": (".claude", "skills", "onchain-exit-assist"),
    "codex": (".codex", "skills", "onchain-exit-assist"),
    "cursor": (".cursor", "skills", "onchain-exit-assist"),
    "agents": (".agents", "skills", "onchain-exit-assist"),
    "hermes": (".hermes", "skills", "onchain-exit-assist"),
}


def test_destination_paths(tmp_path):
    for target, parts in TARGETS.items():
        assert destination(tmp_path, target, "onchain-exit-assist") == tmp_path.joinpath(*parts)


def test_dry_run_writes_nothing(tmp_path, capsys):
    code = install_main(["--home", str(tmp_path), "--skill", "onchain-exit-assist"])
    assert code == 0
    assert list(tmp_path.iterdir()) == []
    report = json.loads(capsys.readouterr().out)
    assert report["dry_run"] is True
    assert report["wrote"] is False
    assert report["ok"] is True
    assert {row["target"] for row in report["actions"]} == set(TARGETS)
    assert all(row["action"].startswith("would-") for row in report["actions"])


def test_apply_creates_symlinks(tmp_path, capsys):
    for target, parts in TARGETS.items():
        home = tmp_path / target
        home.mkdir()
        code = install_main([
            "--home", str(home), "--apply", "--target", target, "--skill", "onchain-exit-assist",
        ])
        assert code == 0, capsys.readouterr().out
        dest = home.joinpath(*parts)
        assert dest.is_symlink()
        assert os.readlink(dest) == str(SKILL)
        assert (dest / "SKILL.md").is_file()


def test_apply_does_not_overwrite_an_existing_directory(tmp_path, capsys):
    dest = tmp_path / ".claude" / "skills" / "onchain-exit-assist"
    dest.mkdir(parents=True)
    (dest / "keep.txt").write_text("keep", encoding="utf-8")
    code = install_main([
        "--home", str(tmp_path), "--apply", "--target", "claude", "--skill", "onchain-exit-assist",
    ])
    assert code == 2
    assert (dest / "keep.txt").read_text(encoding="utf-8") == "keep"
    assert not dest.is_symlink()
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is False
    assert report["wrote"] is False


def test_force_backs_up_then_links(tmp_path, capsys):
    dest = tmp_path / ".cursor" / "skills" / "onchain-exit-assist"
    dest.mkdir(parents=True)
    (dest / "keep.txt").write_text("keep", encoding="utf-8")
    code = install_main([
        "--home", str(tmp_path), "--apply", "--force", "--target", "cursor",
        "--skill", "onchain-exit-assist",
    ])
    assert code == 0
    capsys.readouterr()
    assert dest.is_symlink()
    backups = list((tmp_path / ".cursor" / "skills").glob("onchain-exit-assist.exitkit-bak-*"))
    assert len(backups) == 1
    assert (backups[0] / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_copy_writes_files_not_a_symlink(tmp_path, capsys):
    code = install_main([
        "--home", str(tmp_path), "--apply", "--copy", "--target", "agents",
        "--skill", "onchain-exit-assist",
    ])
    assert code == 0
    capsys.readouterr()
    dest = tmp_path / ".agents" / "skills" / "onchain-exit-assist"
    assert dest.is_dir()
    assert not dest.is_symlink()
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == (SKILL / "SKILL.md").read_text(encoding="utf-8")


def test_symlink_parent_outside_home_is_refused(tmp_path, capsys):
    outside = tmp_path / "outside"
    outside.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    (home / ".codex").symlink_to(outside, target_is_directory=True)
    code = install_main([
        "--home", str(home), "--apply", "--target", "codex", "--skill", "onchain-exit-assist",
    ])
    assert code == 2
    assert list(outside.iterdir()) == []
    err = json.loads(capsys.readouterr().out)
    assert err["ok"] is False


def test_unknown_skill_writes_nothing(tmp_path, capsys):
    code = install_main(["--home", str(tmp_path), "--skill", "not-a-skill"])
    assert code == 2
    assert list(tmp_path.iterdir()) == []
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_grok_dry_run_does_not_write(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "missing-home"))
    out = tmp_path / "grok.md"
    code = install_main([
        "--target", "grok", "--skill", "onchain-exit-assist", "--output", str(out),
    ])
    assert code == 0
    assert not out.exists()
    report = json.loads(capsys.readouterr().out)
    assert report["wrote"] is False
    assert report["dry_run"] is True
    embed = report["actions"][0]["embed"]
    assert "references/07-constants.md" in embed
    assert "references/01-asset-scan.md" in embed


def test_grok_apply_inlines_references(tmp_path, capsys):
    out = tmp_path / "grok.md"
    code = install_main([
        "--target", "grok", "--apply", "--skill", "onchain-exit-assist", "--output", str(out),
    ])
    assert code == 0
    capsys.readouterr()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "name: onchain-exit-assist" in text
    assert "# Embedded reference: references/07-constants.md" in text
    assert "EIP-1967 implementation slot" in text
    assert "# Embedded reference: references/06-hard-limits.md" in text


def test_grok_apply_stdout(capsys):
    code = install_main(["--target", "grok", "--apply", "--skill", "onchain-exit-assist"])
    assert code == 0
    text = capsys.readouterr().out
    assert "name: onchain-exit-assist" in text
    assert "# Embedded reference: references/01-asset-scan.md" in text

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


def _snapshot(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
        dirnames.sort()
        for name in sorted(filenames):
            item = Path(dirpath) / name
            rel = item.relative_to(path).as_posix()
            if item.is_symlink():
                rows.append((rel, "link:" + os.readlink(item)))
            else:
                rows.append((rel, item.read_bytes().hex()))
    return rows


def test_force_over_existing_symlink_keeps_the_source(tmp_path, capsys):
    home = tmp_path / "home"
    home.mkdir()
    before = _snapshot(SKILL)
    assert not any(name.startswith("onchain-exit-assist.exitkit-bak-") for name in os.listdir(SKILL.parent))
    code = install_main([
        "--home", str(home), "--apply", "--target", "claude", "--skill", "onchain-exit-assist",
    ])
    first = capsys.readouterr().out
    assert code == 0, first
    dest = home / ".claude" / "skills" / "onchain-exit-assist"
    assert dest.is_symlink()
    assert os.readlink(dest) == str(SKILL)
    assert SKILL.resolve() != home.resolve()
    code = install_main([
        "--home", str(home), "--target", "claude", "--skill", "onchain-exit-assist",
    ])
    dry = capsys.readouterr().out
    assert code == 0, dry
    report = json.loads(dry)
    assert report["ok"] is True
    assert report["dry_run"] is True
    assert "escapes" not in dry
    code = install_main([
        "--home", str(home), "--apply", "--force", "--target", "claude", "--skill", "onchain-exit-assist",
    ])
    forced = capsys.readouterr().out
    assert code == 0, forced
    assert _snapshot(SKILL) == before
    assert SKILL.is_dir() and not SKILL.is_symlink()
    assert list(SKILL.parent.glob("onchain-exit-assist.exitkit-bak-*")) == []
    assert dest.is_symlink()
    assert os.readlink(dest) == str(SKILL)
    backups = list((home / ".claude" / "skills").glob("onchain-exit-assist.exitkit-bak-*"))
    assert len(backups) == 1
    assert backups[0].is_symlink()
    assert os.readlink(backups[0]) == str(SKILL)


def test_force_does_not_rename_a_user_symlink_target(tmp_path, capsys):
    home = tmp_path / "home"
    dotfiles = home / "dotfiles" / "onchain-exit-assist"
    dotfiles.mkdir(parents=True)
    (dotfiles / "marker.txt").write_text("user", encoding="utf-8")
    inode = dotfiles.stat().st_ino
    dest_parent = home / ".claude" / "skills"
    dest_parent.mkdir(parents=True)
    dest = dest_parent / "onchain-exit-assist"
    dest.symlink_to(dotfiles, target_is_directory=True)
    code = install_main([
        "--home", str(home), "--apply", "--force", "--target", "claude", "--skill", "onchain-exit-assist",
    ])
    assert code == 0, capsys.readouterr().out
    assert dotfiles.stat().st_ino == inode
    assert (dotfiles / "marker.txt").read_text(encoding="utf-8") == "user"
    assert dest.is_symlink()
    assert os.readlink(dest) == str(SKILL)
    backups = list(dest_parent.glob("onchain-exit-assist.exitkit-bak-*"))
    assert len(backups) == 1
    assert backups[0].is_symlink()
    assert os.readlink(backups[0]) == str(dotfiles)


def test_symlinked_agent_dir_outside_the_skills_dir_is_refused(tmp_path, capsys):
    home = tmp_path / "home"
    other = home / "other-dir"
    other.mkdir(parents=True)
    (other / "marker.txt").write_text("keep", encoding="utf-8")
    (home / ".claude").symlink_to(other, target_is_directory=True)
    code = install_main([
        "--home", str(home), "--apply", "--target", "claude", "--skill", "onchain-exit-assist",
    ])
    assert code == 2
    err = json.loads(capsys.readouterr().out)
    assert err["ok"] is False
    assert "escapes HOME" in err["error"]
    assert (other / "marker.txt").read_text(encoding="utf-8") == "keep"
    assert not (other / "skills").exists()


def test_install_ignores_an_unrelated_current_directory(tmp_path, monkeypatch, capsys):
    stranger = tmp_path / "stranger"
    skill = stranger / "skills" / "not-ours"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: not-ours\n---\n", encoding="utf-8")
    (stranger / "pyproject.toml").write_text('[project]\nname = "wallet-exit-kit"\n', encoding="utf-8")
    monkeypatch.chdir(stranger)
    home = tmp_path / "home"
    home.mkdir()
    code = install_main(["--home", str(home), "--skill", "not-ours"])
    assert code == 2
    err = json.loads(capsys.readouterr().out)
    assert err["ok"] is False
    assert "not-ours" in err["error"]
    assert list(home.iterdir()) == []


def test_repo_must_be_an_absolute_checkout(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(ROOT)
    code = install_main(["--repo", ".", "--home", str(tmp_path), "--skill", "onchain-exit-assist"])
    assert code == 2
    assert "absolute" in json.loads(capsys.readouterr().out)["error"]
    code = install_main(["--repo", str(tmp_path), "--home", str(tmp_path), "--skill", "onchain-exit-assist"])
    assert code == 2
    assert "checkout" in json.loads(capsys.readouterr().out)["error"]


def test_copy_refuses_a_symlink_inside_the_skill(tmp_path, capsys):
    repo = tmp_path / "repo"
    skill = repo / "skills" / "demo-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo-skill\n---\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text('[project]\nname = "wallet-exit-kit"\n', encoding="utf-8")
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    (skill / "link.txt").symlink_to(secret)
    home = tmp_path / "home"
    home.mkdir()
    code = install_main([
        "--repo", str(repo), "--home", str(home), "--apply", "--copy",
        "--target", "claude", "--skill", "demo-skill",
    ])
    assert code == 2
    err = json.loads(capsys.readouterr().out)
    assert err["ok"] is False
    assert "symlink" in err["error"]
    assert secret.read_text(encoding="utf-8") == "secret"
    assert not (home / ".claude" / "skills" / "demo-skill").exists()


def test_grok_apply_refuses_to_overwrite_without_force(tmp_path, capsys):
    out = tmp_path / "grok.md"
    out.write_text("keep", encoding="utf-8")
    code = install_main([
        "--target", "grok", "--apply", "--skill", "onchain-exit-assist", "--output", str(out),
    ])
    assert code == 2
    assert out.read_text(encoding="utf-8") == "keep"
    err = json.loads(capsys.readouterr().out)
    assert err["ok"] is False
    assert "force" in err["error"]


def test_grok_apply_force_backs_up_the_existing_file(tmp_path, capsys):
    out = tmp_path / "grok.md"
    out.write_text("keep", encoding="utf-8")
    code = install_main([
        "--target", "grok", "--apply", "--force", "--skill", "onchain-exit-assist", "--output", str(out),
    ])
    assert code == 0, capsys.readouterr().out
    assert "name: onchain-exit-assist" in out.read_text(encoding="utf-8")
    backups = list(tmp_path.glob("grok.md.exitkit-bak-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "keep"


def test_grok_apply_refuses_a_symlink(tmp_path, capsys):
    target = tmp_path / "real.md"
    target.write_text("keep", encoding="utf-8")
    out = tmp_path / "link.md"
    out.symlink_to(target)
    code = install_main([
        "--target", "grok", "--apply", "--force", "--skill", "onchain-exit-assist", "--output", str(out),
    ])
    assert code == 2
    err = json.loads(capsys.readouterr().out)
    assert err["ok"] is False
    assert "symlink" in err["error"]
    assert target.read_text(encoding="utf-8") == "keep"
    assert out.is_symlink()
    assert os.readlink(out) == str(target)


def test_grok_apply_does_not_create_parent_directories(tmp_path, capsys):
    out = tmp_path / "missing" / "grok.md"
    code = install_main([
        "--target", "grok", "--apply", "--skill", "onchain-exit-assist", "--output", str(out),
    ])
    assert code == 2
    assert not (tmp_path / "missing").exists()
    err = json.loads(capsys.readouterr().out)
    assert "parent" in err["error"]

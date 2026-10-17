"""Install skills from a wallet-exit-kit checkout into agent skill directories.

The default is a dry-run that only prints a plan. ``--apply`` writes.
The default write is a symlink to the skill directory in the checkout.
``--copy`` copies the tree. An existing destination is left alone unless
``--force``, which renames it aside first.

``--target grok`` builds one markdown file with each skill's references
inlined after SKILL.md, for pasting into a Grok bot.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path

FS_TARGETS = ("claude", "codex", "cursor", "agents", "hermes")
_SKILL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}")
_REL = {
    "claude": (".claude", "skills"),
    "codex": (".codex", "skills"),
    "cursor": (".cursor", "skills"),
    "agents": (".agents", "skills"),
    "hermes": (".hermes", "skills"),
}


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def repo_root() -> Path:
    start = Path(__file__).resolve()
    seen: set[Path] = set()
    candidates = [start.parent, *start.parents, Path.cwd().resolve()]
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        if (cand / "pyproject.toml").is_file() and (cand / "skills").is_dir():
            return cand
    raise ValueError("cannot find the wallet-exit-kit checkout (pyproject.toml and skills/)")


def resolve_home(explicit: str | None) -> Path:
    raw = explicit if explicit is not None else os.environ.get("HOME")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("HOME is not set")
    if raw == "~" or raw.startswith("~/") or raw.startswith("~\\"):
        raise ValueError("pass an absolute HOME")
    home = Path(raw)
    if not home.is_absolute():
        raise ValueError("pass an absolute HOME")
    home = home.resolve()
    if not home.is_dir():
        raise ValueError("HOME is not a directory")
    return home


def _under_home(home: Path, path: Path) -> Path:
    """Resolve ``path`` and refuse a destination that leaves ``home``."""
    home_r = home.resolve()
    cursor = path
    suffix: list[str] = []
    while not cursor.exists():
        suffix.append(cursor.name)
        parent = cursor.parent
        if parent == cursor:
            raise ValueError("destination escapes HOME")
        cursor = parent
    resolved = cursor.resolve()
    for name in reversed(suffix):
        resolved = resolved / name
    try:
        resolved.relative_to(home_r)
    except ValueError as exc:
        raise ValueError("destination escapes HOME") from exc
    return resolved


def destination(home: Path, target: str, skill: str) -> Path:
    if target not in _REL:
        raise ValueError("unknown target")
    if _SKILL_NAME.fullmatch(skill) is None:
        raise ValueError("unsafe skill name")
    return _under_home(home, home.joinpath(*_REL[target], skill))


def discover_skills(root: Path, names: list[str] | None) -> list[Path]:
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        raise ValueError("skills/ is missing")
    found: list[Path] = []
    root_r = root.resolve()
    for child in sorted(skills_dir.iterdir(), key=lambda p: p.name):
        if child.name.startswith(".") or not child.is_dir():
            continue
        if not (child / "SKILL.md").is_file():
            continue
        if _SKILL_NAME.fullmatch(child.name) is None:
            raise ValueError("unsafe skill name")
        resolved = child.resolve()
        try:
            resolved.relative_to(root_r)
        except ValueError as exc:
            raise ValueError("skill path escapes the repo") from exc
        found.append(resolved)
    if names:
        want = list(names)
        by_name = {path.name: path for path in found}
        missing = [name for name in want if name not in by_name]
        if missing:
            raise ValueError("unknown skill: " + ", ".join(missing))
        found = [by_name[name] for name in want]
    if not found:
        raise ValueError("no skills to install")
    return found


def _ref_files(skill: Path) -> list[Path]:
    refs = skill / "references"
    if not refs.is_dir():
        return []
    root = skill.resolve()
    out: list[Path] = []
    for path in sorted(refs.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            path.resolve().relative_to(root)
        except ValueError:
            continue
        rel = path.relative_to(skill).as_posix()
        if rel.startswith("references/"):
            out.append(path)
    return out


def render_grok(skills: list[Path]) -> str:
    """One markdown document: each SKILL.md followed by its references."""
    chunks: list[str] = []
    for index, skill in enumerate(skills):
        if index:
            chunks.append(f"\n\n# skill: {skill.name}\n\n")
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        chunks.append(text.rstrip() + "\n")
        for path in _ref_files(skill):
            rel = path.relative_to(skill).as_posix()
            body = path.read_text(encoding="utf-8")
            chunks.append(f"\n---\n\n# Embedded reference: {rel}\n\n")
            chunks.append(body.rstrip() + "\n")
    return "".join(chunks)


def _backup(dest: Path) -> Path:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = dest.with_name(dest.name + ".exitkit-bak-" + stamp)
    n = 0
    while os.path.lexists(bak):
        n += 1
        bak = dest.with_name(dest.name + f".exitkit-bak-{stamp}-{n}")
    os.rename(dest, bak)
    return bak


def _action(apply: bool, force: bool, exists: bool, copy: bool) -> str:
    if exists and not force:
        return "skip-exists"
    verb = "backup-and-copy" if exists and copy else "backup-and-link" if exists else "copy" if copy else "link"
    if not apply:
        return "would-" + verb
    return verb


def _install_one(home: Path, skill: Path, target: str, apply: bool, copy: bool, force: bool) -> dict:
    dest = destination(home, target, skill.name)
    exists = os.path.lexists(dest)
    action = _action(apply, force, exists, copy)
    row = {
        "action": action,
        "destination": dest.as_posix(),
        "exists": exists,
        "mode": "copy" if copy else "symlink",
        "skill": skill.name,
        "source": str(skill.resolve()),
        "target": target,
    }
    if not apply or (exists and not force):
        return row
    if exists:
        row["backup"] = _backup(dest).as_posix()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(dest):
        raise ValueError("refusing to overwrite")
    if copy:
        shutil.copytree(
            skill,
            dest,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
    else:
        os.symlink(str(skill.resolve()), dest, target_is_directory=True)
    return row


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="exitkit install",
        description="Install skills from this checkout. Default is a dry-run.",
    )
    parser.add_argument("--home", default=None, help="install under this HOME (default: $HOME)")
    parser.add_argument("--apply", action="store_true", help="write; without this flag only print the plan")
    parser.add_argument("--copy", action="store_true", help="copy files instead of symlinking")
    parser.add_argument("--force", action="store_true", help="back up an existing skill directory, then replace it")
    parser.add_argument("--target", action="append", choices=(*FS_TARGETS, "grok"), default=None)
    parser.add_argument("--skill", action="append", default=None, help="skill directory name; default is every skill")
    parser.add_argument("--output", default=None, help="with --target grok --apply, write the single file here")
    return parser.parse_args(argv)


def _run(args: argparse.Namespace) -> int:
    root = repo_root()
    skills = discover_skills(root, args.skill)
    targets = list(args.target) if args.target else list(FS_TARGETS)
    if len(targets) != len(set(targets)):
        raise ValueError("repeated --target")
    if args.output and "grok" not in targets:
        raise ValueError("--output is only for --target grok")
    if "grok" in targets and args.apply and not args.output and targets != ["grok"]:
        raise ValueError("pass --output when combining grok with other targets")
    fs_targets = [target for target in targets if target != "grok"]
    home = resolve_home(args.home) if fs_targets else None

    actions: list[dict] = []
    wrote = False
    if "grok" in targets:
        embed: list[str] = []
        for skill in skills:
            embed.extend(path.relative_to(skill).as_posix() for path in _ref_files(skill))
        actions.append({
            "action": "emit" if args.apply else "would-emit",
            "embed": embed,
            "mode": "grok",
            "output": args.output or "stdout",
            "skills": [skill.name for skill in skills],
        })
        if args.apply:
            text = render_grok(skills)
            if args.output:
                dest = Path(args.output)
                if not dest.is_absolute():
                    raise ValueError("pass an absolute --output path")
                if dest.exists() and dest.is_dir():
                    raise ValueError("--output is a directory")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(text, encoding="utf-8")
                wrote = True
            elif targets == ["grok"]:
                sys.stdout.write(text)
                if not text.endswith("\n"):
                    sys.stdout.write("\n")
                return 0

    if home is not None:
        for skill in skills:
            for target in fs_targets:
                row = _install_one(home, skill, target, bool(args.apply), bool(args.copy), bool(args.force))
                actions.append(row)
                if row["action"] in {"link", "copy", "backup-and-link", "backup-and-copy"}:
                    wrote = True

    conflicts = [row for row in actions if row["action"] == "skip-exists"]
    report = {
        "actions": actions,
        "apply": bool(args.apply),
        "copy": bool(args.copy),
        "dry_run": not args.apply,
        "force": bool(args.force),
        "ok": not (args.apply and conflicts),
        "wrote": wrote,
    }
    if home is not None:
        report["home"] = home.as_posix()
    _emit(report)
    if args.apply and conflicts:
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    try:
        return _run(args)
    except ValueError as exc:
        _emit({"error": str(exc), "ok": False})
        return 2
    except OSError as exc:
        _emit({"error": str(exc), "ok": False})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

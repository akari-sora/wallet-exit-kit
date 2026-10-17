"""Every skill's frontmatter must be valid YAML for strict loaders (Grok Bot skill library)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _frontmatter(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").split("\n")
    assert lines[0] == "---", f"{path}: frontmatter must start on line 1"
    end = lines.index("---", 1)
    return lines[1:end]


def test_frontmatter_values_are_safe_yaml_scalars():
    skills = sorted(ROOT.glob("skills/*/SKILL.md"))
    assert skills
    for path in skills:
        keys = {}
        for line in _frontmatter(path):
            key, sep, value = line.partition(": ")
            assert sep, f"{path}: bad frontmatter line {line!r}"
            value = value.strip()
            if value.startswith('"'):
                value = json.loads(value)
            else:
                # A plain YAML scalar may not contain ": " or start with a reserved character.
                assert ": " not in value and not value.startswith(("'", "[", "{", "&", "*", "!", "|", ">", "%", "@", "`")), (
                    f"{path}: quote the value of {key!r}"
                )
            keys[key] = value
        assert keys.get("name") == path.parent.name
        assert keys.get("description")

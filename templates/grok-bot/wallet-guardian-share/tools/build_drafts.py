#!/usr/bin/env python3
# Dev-only build step (not used by a bot). Repo layout: templates/grok-bot/wallet-guardian-share/{tools,skills}; any cwd.
#  1. TEMPLATE_SHA in tools/wg_skillcheck.py := sha256 of tools/instructions-template.v1.3.txt (the instructions template:
#     placeholders <COMMIT40>, <COMMIT8>, <SHA64-*>; never pasted into a bot; MR B renders it with render_release.py);
#  2. the ```python wg_skillcheck fence in skills/wallet-guardian-welcome/SKILL.md := tools/wg_skillcheck.py, byte for byte.
# Generated in one direction only, so the two copies cannot drift. --check: change nothing, exit 1 if anything is stale.
import hashlib, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTR = os.path.join(ROOT, "tools", "instructions-template.v1.3.txt")
WELCOME = os.path.join(ROOT, "skills", "wallet-guardian-welcome", "SKILL.md")
HELPER = os.path.join(ROOT, "tools", "wg_skillcheck.py")
FENCE = re.compile(r"(\n```python wg_skillcheck\n)(.*?\n)(```\n)", re.S)

def template(text):
    # A review draft (first line DRAFT-MARKER, removed here) or the template file itself. Either way it must still hold
    # the <COMMIT40> placeholder, so a rendered release text can never be taken as the template.
    lines = text.split("\n")
    if lines[0].startswith("DRAFT-MARKER:"): lines = lines[1:]
    t = "\n".join(lines).rstrip("\n") + "\n"
    if "<COMMIT40>" not in t or re.search(r"(?m)^DRAFT-MARKER", t): raise SystemExit("not the instructions template or its draft")
    return t

def main(check):
    tsha = hashlib.sha256(template(open(INSTR).read()).encode()).hexdigest()
    h = open(HELPER).read()
    h2 = re.sub(r'^TEMPLATE_SHA = "[^"]*"', 'TEMPLATE_SHA = "%s"' % tsha, h, count=1, flags=re.M)
    w = open(WELCOME).read()
    if len(FENCE.findall(w)) != 1 or "```" in h2: raise SystemExit("welcome needs exactly one helper fence; helper must not contain ```")
    w2 = FENCE.sub(lambda m: m.group(1) + h2 + m.group(3), w)
    stale = (h2 != h) or (w2 != w)
    if check: print("stale" if stale else "up to date", tsha); return 1 if stale else 0
    open(HELPER, "w").write(h2); open(WELCOME, "w").write(w2); print("built", tsha); return 0

if __name__ == "__main__": sys.exit(main("--check" in sys.argv))

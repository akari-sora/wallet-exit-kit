#!/usr/bin/env python3
# Dev-only release helper for the two-MR flow (not used by a bot). No network, no git.
#   strip FILE                   print FILE without its DRAFT-MARKER lines (MR A: rules and welcome as committed)
#   notify DRAFT NOTIFY_COMMIT40 WG_NOTIFY_FILE
#       print the notify SKILL.md for MR A commit 2+: DRAFT-MARKER line removed, <NOTIFY_COMMIT40> := MR A commit 1 (the
#       commit that adds only wg_notify.py), <WG_NOTIFY_SHA256> := sha256 of WG_NOTIFY_FILE (that file fetched at commit 1).
#   instructions TEMPLATE COMMIT40 DIR   (TEMPLATE = tools/instructions-template.v1.3.txt)
#       DIR = the six wallet-guardian-*/SKILL.md fetched from the raw URLs at COMMIT40 (MR A's merge commit), plus
#       wallet-guardian-notify/wg_notify.py fetched at COMMIT40; its sha256 must equal the pin in the notify SKILL.md.
#       Computes the six sha256 itself, checks the six files (no DRAFT-MARKER line; rules has its version, revision, and
#       end lines; welcome's helper fence equals tools/wg_skillcheck.py and its TEMPLATE_SHA equals this template),
#       fills <COMMIT40>, <COMMIT8>, <SHA64-*>, runs guard, prints the release text (MR B).
#   guard FILE                   full-content check of a release text: it must equal the canonical template after undoing
#                                only the commit and the six hashes (same check as the helper's check-instructions).
#   paste-test TEMPLATE          print the length-only paste-test copy: all-zero commit and hashes and a TEST end line,
#                                so guard, check-instructions, and the download all fail. Never installable.
import hashlib, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wg_skillcheck as W
from build_drafts import template, FENCE

def rdb(p):
    with open(p, "rb") as f: return f.read()

def strip(text): return "".join(l for l in text.splitlines(True) if not l.startswith("DRAFT-MARKER"))

NOTIFY_PH = ("<NOTIFY_COMMIT40>", "<WG_NOTIFY_SHA256>")
NOTIFY_PIN = re.compile(r"(?m)^- Commit: ([0-9a-f]{40})\n- sha256: ([0-9a-f]{64})\n- URL: https://gitlab\.com/aa22396584/wallet-exit-kit/-/raw/\1/"
                        r"templates/grok-bot/wallet-guardian-share/skills/wallet-guardian-notify/wg_notify\.py\n")

def helper_ok(b):
    # wg_notify.py as extracted from the v1.2 notify SKILL.md: UTF-8, LF only, shebang first, one final newline, no fence.
    try: s = b.decode("utf-8")
    except UnicodeDecodeError: return False
    return s.startswith("#!/usr/bin/env python3\n") and s.endswith("\n") and not s.endswith("\n\n") and "\r" not in s and "```" not in s

def notify(draft, commit, helper_file):
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or commit == "0" * 40: raise W.Fail("NOTIFY_COMMIT40 must be a real 40-hex commit")
    b = rdb(helper_file)
    if not helper_ok(b): raise W.Fail("wg_notify.py is not in the expected form")
    t = strip(rdb(draft).decode())
    if t.count(NOTIFY_PH[0]) != 3 or t.count(NOTIFY_PH[1]) != 3: raise W.Fail("notify draft must carry each placeholder exactly 3 times")
    if "```python" in t: raise W.Fail("notify draft still embeds a helper")
    out = t.replace(NOTIFY_PH[0], commit).replace(NOTIFY_PH[1], hashlib.sha256(b).hexdigest())
    if W.strict_parse(out.encode(), "wallet-guardian-notify") is None: raise W.Fail("notify is not in the expected form")
    if notify_pin(out.encode()) != (commit, hashlib.sha256(b).hexdigest()): raise W.Fail("notify pin lines not as expected")
    return out

def notify_pin(raw):
    s = raw.decode("utf-8", "replace")
    if any(p in s for p in NOTIFY_PH) or "```python" in s: return None
    m = NOTIFY_PIN.findall(s)
    if len(m) != 1 or s.count("skills/wallet-guardian-notify/wg_notify.py") != 2 or s.count(m[0][1]) != 3: return None
    return m[0]

def guard(text):
    if re.search(r"(?m)^(DRAFT-MARKER|END WG-INSTRUCTIONS TEST)", text): raise W.Fail("draft or test marker present")
    if re.search(r"<(COMMIT40|COMMIT8|SHA64-[a-z-]+)>", text): raise W.Fail("placeholder left")
    t, c = W.template_of(text)
    if hashlib.sha256(t.encode()).hexdigest() != W.TEMPLATE_SHA: raise W.Fail("text differs from the canonical v1.3 template")
    if text.rstrip("\n").split("\n")[-1] != "END WG-INSTRUCTIONS v1.3 " + c[:8]: raise W.Fail("last line is not the END line")
    return c

def fill(tpl, commit, pins):
    t = tpl.replace("<COMMIT40>", commit).replace("<COMMIT8>", commit[:8])
    for n, h in pins.items(): t = t.replace("<SHA64-%s>" % n[len("wallet-guardian-"):], h)
    return t

def instructions(draft, commit, d):
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or commit == "0" * 40: raise W.Fail("COMMIT40 must be a real 40-hex commit")
    raws = {n: rdb(os.path.join(d, n, "SKILL.md")) for n in W.NAMES}
    for n, b in raws.items():
        if re.search(rb"(?m)^DRAFT-MARKER", b): raise W.Fail("%s still has a DRAFT-MARKER line" % n)
        if W.strict_parse(b, n) is None: raise W.Fail("%s is not in the expected form" % n)
    pin = notify_pin(raws["wallet-guardian-notify"])
    if pin is None: raise W.Fail("notify has placeholders, an embedded helper, or no single pin")
    hb = rdb(os.path.join(d, "wallet-guardian-notify", "wg_notify.py"))
    if not helper_ok(hb) or hashlib.sha256(hb).hexdigest() != pin[1]: raise W.Fail("wg_notify.py at COMMIT40 differs from the notify pin")
    body = W.strict_parse(raws["wallet-guardian-rules"], "wallet-guardian-rules")[2].split("\n")
    if W.RULES_LINE not in body or W.REVISION not in body or body[-1] != W.END_LINE: raise W.Fail("rules lack version, revision, or end line")
    m = FENCE.findall(raws["wallet-guardian-welcome"].decode())
    helper = rdb(os.path.join(os.path.dirname(os.path.abspath(__file__)), "wg_skillcheck.py")).decode()
    if len(m) != 1 or m[0][1] != helper: raise W.Fail("welcome helper differs from tools/wg_skillcheck.py")
    tpl = template(rdb(draft).decode())
    if hashlib.sha256(tpl.encode()).hexdigest() != W.TEMPLATE_SHA: raise W.Fail("draft template differs from the helper's TEMPLATE_SHA")
    out = fill(tpl, commit, {n: hashlib.sha256(b).hexdigest() for n, b in raws.items()})
    guard(out); return out

def paste_test(draft):
    t = fill(template(rdb(draft).decode()), "0" * 40, {n: "0" * 64 for n in W.NAMES})
    return t.replace("END WG-INSTRUCTIONS v1.3 00000000", "END WG-INSTRUCTIONS TEST 00000000")

def main(a):
    try:
        if a[:1] == ["strip"] and len(a) == 2: sys.stdout.write(strip(rdb(a[1]).decode())); return 0
        if a[:1] == ["notify"] and len(a) == 4: sys.stdout.write(notify(*a[1:])); return 0
        if a[:1] == ["instructions"] and len(a) == 4: sys.stdout.write(instructions(*a[1:])); return 0
        if a[:1] == ["guard"] and len(a) == 2: print("guard ok", guard(rdb(a[1]).decode())[:8]); return 0
        if a[:1] == ["paste-test"] and len(a) == 2: sys.stdout.write(paste_test(a[1])); return 0
    except W.Fail as e: print("FAIL", e, file=sys.stderr); return 2
    print(__doc__ or "usage: strip|notify|instructions|guard|paste-test", file=sys.stderr); return 64

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))

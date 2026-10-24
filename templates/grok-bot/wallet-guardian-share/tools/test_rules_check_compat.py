# Runs the real rules-check of wg_notify.py (the committed file, asserted byte-identical to the block in
# wallet-guardian-notify@8dbda8e1's SKILL.md; only WORKFLOWS is
# repointed to fixture folders, in a scratch copy under tools/.scratch, never /tmp) against v1.2 and the v1.3 rules.
# No network: rules-check makes no calls.
import os, re, shutil, subprocess, sys
from testlib import REPO, V13, RULES_D, HELPER, mkscratch
md = REPO["wallet-guardian-notify"].decode()
assert re.search(r"```python\n(#!/usr/bin/env python3\n# Wallet Guardian push helper.*?)```", md, re.S).group(1).encode() == HELPER
helper = HELPER.decode()
assert helper.count('WORKFLOWS = "/home/box/agent-data/workflows"') == 1
v12 = REPO["wallet-guardian-rules"].decode()
v13 = V13["wallet-guardian-rules"].decode()  # as committed
def folded(t):  # installer-style >- description
    return t.replace('description: "Use this always: the canonical Wallet Guardian rules; read it first in every conversation and every routine run before any other skill or action."',
                     "description: >-\n  Use this always: the canonical Wallet Guardian rules; read it first in every\n  conversation and every routine run before any other skill or action.")
bumped = v13.replace("Rules version: v1.2 (2026-10-18).", "Rules version: v1.3 (2026-10-20).")
cases = [("v1.2 only", [v12], 0), ("v1.3 with a DRAFT-MARKER line (synthetic)", [RULES_D], 0), ("v1.3 final (markers removed, end line)", [v13], 0),
         ("v1.3 final, folded description", [folded(v13)], 0), ("v1.3 with version line bumped (option B, helper unchanged)", [bumped], 3),
         ("v1.2 + v1.3 both installed", [v12, v13], 3), ("v1.3 final, CRLF line ends", [v13.replace("\n", "\r\n")], 3), ("no rules installed", [], 3)]
fails = 0; base = mkscratch()
try:
    for k, (label, files, want) in enumerate(cases):
        d = os.path.join(base, str(k)); wf = os.path.join(d, "wf"); os.makedirs(wf); os.makedirs(os.path.join(d, "wg"))
        for i, t in enumerate(files):
            p = os.path.join(wf, "wallet-guardian-rules" + ("-%d" % (i + 1) if i else "")); os.makedirs(p)
            with open(os.path.join(p, "SKILL.md"), "w", encoding="utf-8", newline="") as f: f.write(t)
        with open(os.path.join(d, "wg_notify.py"), "w") as f: f.write(helper.replace('"/home/box/agent-data/workflows"', repr(wf), 1))
        r = subprocess.run([sys.executable, "-B", os.path.join(d, "wg_notify.py"), "rules-check"], capture_output=True, text=True,
                           env={"WG_DIR": os.path.join(d, "wg"), "PATH": os.environ.get("PATH", "")})
        out = (r.stdout + r.stderr).strip().replace(wf, "<fixture>")
        ok = r.returncode == want; fails += not ok
        print("%s | %s | exit %d (want %d) | %s" % ("PASS" if ok else "FAIL", label, r.returncode, want, out))
finally: shutil.rmtree(base, ignore_errors=True)
print("%d/%d passed" % (len(cases) - fails, len(cases))); sys.exit(1 if fails else 0)

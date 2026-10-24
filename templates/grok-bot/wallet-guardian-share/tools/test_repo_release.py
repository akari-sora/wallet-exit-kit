# Release gates on the git history of this checkout (MR A, before the push): commit N (the notify pin) adds only
# wg_notify.py and is an ancestor of HEAD; the files at N and at HEAD match the pins; MR B files are untouched.
# Needs git and commit 8dbda8e1. No network: the raw-URL fetch at N and at HEAD is a separate step after the push.
import hashlib, os, subprocess, unittest
from testlib import *

HP = SHARE_PATH + "/skills/wallet-guardian-notify/wg_notify.py"
def ok(*a): return subprocess.run(["git"] + list(a), cwd=SHARE, capture_output=True).returncode == 0

class History(unittest.TestCase):
    def test_n_is_an_ancestor_and_adds_only_wg_notify(self):
        self.assertTrue(ok("merge-base", "--is-ancestor", NFAKE, "HEAD"))
        self.assertTrue(ok("merge-base", "--is-ancestor", C12, NFAKE))
        self.assertEqual(git("diff-tree", "--no-commit-id", "--name-status", "-r", NFAKE).decode(), "A\t%s\n" % HP)
    def test_wg_notify_at_n_and_head_matches_the_pin(self):
        for c in (NFAKE, "HEAD"):
            b = git("show", "%s:%s" % (c, HP)); self.assertEqual(b, HELPER, c); self.assertEqual(hashlib.sha256(b).hexdigest(), PIN[1], c)
        self.assertEqual(hashlib.sha256(HELPER).hexdigest(), "2c2b87bb267435d3c3c4e3ca9a1dff06aae6f38bd3285f62214d86096567ad78")
    def test_committed_skills_are_the_checkout_and_the_render(self):
        for n in W.NAMES: self.assertEqual(at("HEAD", "skills/%s/SKILL.md" % n), V13[n], n)
        self.assertEqual(R.notify(NOTIFY_DRAFT, NFAKE, HELPER_PATH).encode(), V13["wallet-guardian-notify"])
        for n in ("wallet-guardian-rules", "wallet-guardian-welcome"): self.assertEqual(R.strip(globals()[n.split("-")[-1].upper() + "_D"]).encode(), V13[n])
    def test_only_three_skills_change_and_mr_b_files_untouched(self):
        changed = [n for n in W.NAMES if V13[n] != REPO[n]]
        self.assertEqual(sorted(changed), ["wallet-guardian-notify", "wallet-guardian-rules", "wallet-guardian-welcome"])
        for f in ("BOT-DESCRIPTION.txt", "README.md", "STOREFRONT.txt", "REDTEAM-SUMMARY.md"): self.assertEqual(at("HEAD", f), at(C12, f), f)
    def test_sha256sums_lists_the_committed_files(self):
        lines = at("HEAD", "SHA256SUMS").decode().splitlines(); self.assertEqual(lines[0].split("  ")[1], "BOT-DESCRIPTION.txt")
        self.assertEqual(lines[0], at(C12, "SHA256SUMS").decode().splitlines()[0])  # the BOT-DESCRIPTION.txt line is MR B's
        self.assertEqual(sorted(l.split("  ")[1] for l in lines[1:]), sorted("skills/%s/SKILL.md" % n for n in W.NAMES))
        for l in lines:
            h, p = l.split("  "); self.assertEqual(hashlib.sha256(at("HEAD", p)).hexdigest(), h, p)

if __name__ == "__main__": unittest.main(verbosity=2)

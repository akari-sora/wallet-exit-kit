# Offline checks on the instruction text, the release tool, and cross-file consistency. Tests the written text, not a bot.
import os, shutil, subprocess, sys, unittest
from testlib import *
PASTE = R.paste_test(TEMPLATE_PATH)  # the paste-test file itself is not in the repo
V12 = V12_INSTR
REL = render(V13)

def guard_ok(t):
    try: R.guard(t); return True
    except W.Fail: return False

class Guard(unittest.TestCase):
    def test_draft_not_shippable(self): self.assertFalse(guard_ok(DRAFT)); self.assertFalse(guard_ok(R.strip(DRAFT)))
    def test_release_passes_and_ends_with_end_line(self):
        self.assertTrue(guard_ok(REL)); self.assertEqual(REL.rstrip("\n").split("\n")[-1], "END WG-INSTRUCTIONS v1.3 " + FAKE[:8])
        self.assertEqual(REL.count("END WG-INSTRUCTIONS"), 1, "the end line is never quoted earlier")
    def test_every_prefix_fails(self):
        b = REL.encode(); bad = [n for n in range(len(b)) if b[:n].rstrip(b"\n") != b.rstrip(b"\n") and guard_ok(b[:n].decode("utf-8", "ignore"))]
        self.assertEqual(bad, [])
    def test_every_line_deleted_or_doubled_fails(self):
        L = REL.split("\n")
        self.assertEqual([i for i in range(len(L) - 1) if L[i] and guard_ok("\n".join(L[:i] + L[i + 1:]))], [])
        self.assertEqual([i for i in range(len(L) - 1) if L[i] and guard_ok("\n".join(L[:i + 1] + L[i:]))], [])
    def test_suffix_and_middle_cuts_fail(self):
        for a, b in ((0, 100), (2000, 2100), (len(REL) // 2, len(REL) // 2 + 1)): self.assertFalse(guard_ok(REL[:a] + REL[b:]))
    def test_steps_in_order_before_hash_lines(self):
        pos = [REL.index(s) for s in ("- Fail closed:", "- Never overwrite:", "- Step 1, consent:", "- Step 2, download", "- Step 3, verify:",
                                       "- Step 4, check", "- Step 5, install:", "- Hash lines")]
        self.assertEqual(pos, sorted(pos))
        first = min(REL.index(l) for l in REL.split("\n") if W.PIN_RE.match(l)); self.assertLess(pos[-1], first)
        print("\n  release: %d bytes, %d chars; first hash line at byte %d" % (len(REL.encode()), len(REL), len(REL[:first].encode())), file=sys.stderr)
    def test_curl_line(self):
        s2 = [l for l in REL.split("\n") if "curl -q" in l]; self.assertEqual(len(s2), 1); c = s2[0]
        self.assertIn("curl -q --proto =https -sS ", c); self.assertIn("-w '%{http_code}'", c); self.assertIn('[ "$s" = 200 ] || exit 1', c)
        for bad in (" -L", "--location", " -f", "-k ", "--insecure"): self.assertNotIn(bad, c)
        self.assertIn('mkdir -m 700 "$D"', c); self.assertNotIn("mkdir -p", c); self.assertTrue(c.startswith("set -eu; "))
        guard = '[ "$(realpath -e -- "$F")" = "$F" ] || exit 1; case "$F/" in /home/box/agent-data/workflows/*|/tmp/*|/var/tmp/*|/dev/shm/*) exit 1;; esac; '
        self.assertIn(guard, c); self.assertLess(c.index(guard), c.index("mkdir"))
        self.assertEqual(tuple(W.SHARED_TMP), ("/tmp", "/var/tmp", "/dev/shm")); self.assertEqual(W.WORKFLOWS, "/home/box/agent-data/workflows")
    def test_step4_examples_are_real_helper_output(self):
        line = [l for l in REL.split("\n") if l.startswith("First check-instructions")][0]
        self.assertIn('the last line starts with "result: install only: "', line)
        t = mkscratch()
        try:
            lib = os.path.join(t, "lib"); os.mkdir(lib); F = os.path.join(t, "a"); os.mkdir(F); D = make_D(F, V13)
            for n in W.NAMES[2:]: wr(os.path.join(lib, n, "SKILL.md"), installer_form(V13[n], n))
            ex1 = run("compare", D, root=lib); self.assertEqual(ex1[0], 0)
            for n in W.NAMES[:2]: wr(os.path.join(lib, n, "SKILL.md"), installer_form(V13[n], n))
            ex2 = run("compare", D, root=lib); self.assertEqual(ex2[0], 0)
        finally: shutil.rmtree(t)
        self.assertIn('e.g. "%s" or "%s")' % (ex1[2], ex2[2]), line)
    def test_v12_text_kept(self):
        for para in V12.split("\n\n")[:2]: self.assertIn(para.split(" In a first conversation")[0][:200], REL)

class PasteTest(unittest.TestCase):
    def test_paste_copy_is_uninstallable(self):
        self.assertFalse(guard_ok(PASTE)); self.assertIn("/-/raw/" + "0" * 40 + "/", PASTE)
        self.assertEqual(PASTE.rstrip("\n").split("\n")[-1], "END WG-INSTRUCTIONS TEST 00000000")
    def test_same_length_as_any_release(self):
        self.assertEqual(len(PASTE.encode()), len(REL.encode())); self.assertEqual(len(PASTE), len(REL))
    def test_render_refuses_zero_commit(self):
        with self.assertRaises(W.Fail): R.instructions(TEMPLATE_PATH, "0" * 40, os.path.join(SHARE, "skills"))

class Release(unittest.TestCase):
    def setUp(self): self.t = mkscratch()
    def tearDown(self): shutil.rmtree(self.t, ignore_errors=True)
    def rel(self, files):
        d = os.path.join(self.t, "x"); shutil.rmtree(d, ignore_errors=True); write_set(d, files, HELPER)
        return R.instructions(TEMPLATE_PATH, FAKE, d)
    def test_render_from_fetched_files(self): self.assertEqual(self.rel(V13), REL)
    def test_render_refuses_bad_mr_a(self):
        for n, f in (("wallet-guardian-rules", lambda b: RULES_D.encode()), ("wallet-guardian-welcome", lambda b: WELCOME_D.encode()),
                     ("wallet-guardian-rules", lambda b: b.replace(b"\nEnd of wallet-guardian-rules v1.3\n", b"\n")),
                     ("wallet-guardian-rules", lambda b: b.replace(b"Rules revision: v1.3\n", b"")),
                     ("wallet-guardian-welcome", lambda b: b.replace(b"MAX, HEAD", b"MAX,HEAD")),
                     ("wallet-guardian-welcome", lambda b: REPO["wallet-guardian-welcome"])):
            with self.assertRaises(W.Fail): self.rel(dict(V13, **{n: f(V13[n])}))
    def test_build_up_to_date(self):
        r = subprocess.run([sys.executable, os.path.join(HERE, "build_drafts.py"), "--check"], cwd=SHARE, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

class Consistency(unittest.TestCase):
    RULES, WEL = R.strip(RULES_D), R.strip(WELCOME_D)
    def test_same_six_names(self): self.assertEqual(set(re.findall(r"(wallet-guardian-[a-z-]+)/SKILL\.md", REL)), set(W.NAMES))
    def test_revision_and_end_lines(self):
        L = self.RULES.rstrip("\n").split("\n")
        self.assertIn(W.REVISION, L); self.assertIn(W.RULES_LINE, L); self.assertEqual(L[-1], W.END_LINE); self.assertEqual(self.RULES.count(W.END_LINE), 1)
        for t in (REL, RULES_D, WELCOME_D): self.assertIn('"Rules revision: v1.3"', t)
        self.assertIn('"End of wallet-guardian-rules v1.3"', REL)
    def test_markers(self):
        # Committed files: no DRAFT-MARKER line and no draft wording; the synthetic draft forms carry exactly one marker.
        for t in [b.decode() for b in V13.values()] + [DRAFT, REL]: self.assertEqual(re.findall(r"(?m)^DRAFT-MARKER", t), [])
        for t in (RULES_D, WELCOME_D, NOTIFY_D): self.assertEqual(len(re.findall(r"(?m)^DRAFT-MARKER", t)), 1)
        for t in (self.RULES, self.WEL, REL, DRAFT, V13["wallet-guardian-notify"].decode()): self.assertNotIn("draft r", t)
        self.assertEqual((self.RULES, self.WEL), (V13["wallet-guardian-rules"].decode(), V13["wallet-guardian-welcome"].decode()))
    def test_replace_or_delete_rule_everywhere(self):
        for t in (REL, self.RULES, self.WEL):
            for w in ("names", "show-diff or failed check", "replace or delete", "1:1"): self.assertIn(w, t, w)
    def test_consent_limits(self):
        for w in ('"a message naming the action is the yes"', "24-hour", "routine runs", "sub-agents"): self.assertIn(w, self.RULES)
        for w in ("R-3 shortcuts", "routines", "sub-agents", "one attempt"): self.assertIn(w, REL)
        self.assertIn("- No consent lifts R-1, R-2, R-12, R-16, or the limits in R-19.", self.RULES)
    def test_r1_to_r18_unchanged_except_listed(self):
        v12 = REPO["wallet-guardian-rules"].decode().split("\n"); v13 = self.RULES.split("\n")
        self.assertEqual(sorted(l for l in v12 if l not in v13), sorted(["- No consent lifts R-1, R-2, R-12, or R-16.",
            "R-7 Files. Write only inside the folder the user approved, never a shared temp directory. List paths written at the end of the reply.",
            "- wallet-guardian-welcome: the first message."]))
    def test_folder_rules(self):
        for t in (REL, self.RULES): self.assertIn("/home/box/agent-data/workflows", t); self.assertIn("wg-install-", t); self.assertIn("A-Z a-z 0-9 . _ / -", t)
    def test_welcome_opens_with_name_is_not_verification(self):
        body = self.WEL.split("---\n", 2)[2]
        self.assertLess(body.index("A skill name in your list is not verification"), body.index("## Skill check"))
        msg = body.split("## The message")[1].split("\n")[1]; self.assertTrue(msg.startswith("Note: matching skill names are not a verification."))
        self.assertIn("check Wallet Guardian skills", msg)
        self.assertIn("A skill name in the list is not verification.", REL)
    def test_newer_revision_report_only(self):
        for t in (REL, self.RULES, self.WEL): self.assertRegex(t, r"(?i)newer rules revision")
    def test_one_cleanup_command_everywhere(self):
        cmd = 'rm -rf -- "$F/wg-install-<COMMIT8>"'  # the review-package docs are not in the repo, so only the four texts
        texts = {"instructions": DRAFT, "rules": RULES_D, "welcome": WELCOME_D, "notify": NOTIFY_D}
        for k, t in texts.items():
            for m in re.finditer(r"rm -rf", t): self.assertEqual(t[m.start():m.start() + len(cmd)], cmd, k)
        for k in ("instructions", "rules", "welcome"): self.assertIn(cmd, texts[k], k)
        self.assertIn('rm -rf -- "$F/wg-install-' + FAKE[:8] + '"', REL); self.assertNotIn("delete the download folder", WELCOME_D)
        for t in (REL, self.RULES): self.assertIn("only when compare stops on differs, unknown, or duplicate, keep that folder for show-diff", t)
    def test_loader_is_the_only_way(self):
        self.assertEqual(REL.count("python3 -I -B -c"), 1); self.assertNotIn("awk", REL + self.WEL + self.RULES)
        self.assertIn("never written to a file", self.RULES); self.assertIn("Never extract it to a file", self.WEL)

class Privacy(unittest.TestCase):
    def test_share_folder_clean(self):
        bad = ["/work" + "space", "/Us" + "ers", "Asia/" + "Taipei", "wallet-guardian-" + "ops", "\u9f8d", "Sa" + "m ", "ImL" + "1s"]
        for root, _, fs in os.walk(SHARE):
            rel = os.path.relpath(root, SHARE)
            if ".scratch" in rel.split(os.sep) or "__pycache__" in rel: continue
            for f in fs:
                t = rd(os.path.join(root, f)).decode("utf-8", "replace")
                for w in bad: self.assertFalse(w in t, "%r in %s/%s" % (w, rel, f))
                self.assertIsNone(re.search(r"0x[0-9a-fA-F]{40}", t), f)

if __name__ == "__main__": unittest.main(verbosity=2)

# Offline tests for the v1.3 notify helper split (r5): wg_notify.py extracted from the v1.2 notify SKILL.md, the pinned
# download command and the verified-run wrapper in the committed notify §4 (run through bash with a fake curl first on PATH),
# and the release tool's notify checks. No network, no /tmp. Not tested here: a real bot, the real GitLab, a real phone.
import hashlib, os, re, shutil, subprocess, sys, unittest
from testlib import *

V12N = REPO["wallet-guardian-notify"]; NOTE = V13["wallet-guardian-notify"].decode(); HSHA = hashlib.sha256(HELPER).hexdigest()
URL = ("https://gitlab.com/aa22396584/wallet-exit-kit/-/raw/%s/templates/grok-bot/wallet-guardian-share/skills/"
       "wallet-guardian-notify/wg_notify.py" % NFAKE)
def block(raw): return re.findall(rb"\n```python\n(.*?\n)```\n", raw, re.S)
def code_after(text, head):
    L = text.split("\n"); i = L.index(next(l for l in L if l.startswith(head))); assert L[i + 1] == "```"; return L[i + 2]
DL = code_after(NOTE, "Folder: WG_DIR is the approved folder"); RUNF = code_after(NOTE, "Run (every helper call")

FAKE_CURL = r'''#!/usr/bin/env python3
import os, sys
a = sys.argv[1:]; open(os.environ["CURL_LOG"], "a").write(" ".join(a) + "\n")
o = a[a.index("-o") + 1]; mode = os.environ.get("CURL_MODE", "ok")
if mode == "neterr": sys.exit(6)
body = open(os.environ["CURL_SRC"], "rb").read()
if mode == "tamper": body = body.replace(b"TTL = 900", b"TTL = 901")
if mode == "short": body = body[:-1]
if mode in ("404", "302"): body = b"<html>no</html>"
open(o, "wb").write(body); sys.stdout.write(mode if mode in ("404", "302") else "200")
'''

class Extraction(unittest.TestCase):
    def test_byte_identical_to_v12_block(self):
        m = block(V12N); self.assertEqual(len(m), 1); self.assertEqual(m[0], HELPER)
        v12sums = [l.split("  ")[0] for l in at(C12, "SHA256SUMS").decode().splitlines() if l.endswith("  skills/wallet-guardian-notify/SKILL.md")]
        self.assertEqual([hashlib.sha256(V12N).hexdigest()], v12sums)  # the v1.2 file as listed in SHA256SUMS at 8dbda8e1
        self.assertEqual((len(HELPER), HSHA), (18107, "2c2b87bb267435d3c3c4e3ca9a1dff06aae6f38bd3285f62214d86096567ad78"))
        i = V12N.index(b"\n```python\n") + len(b"\n```python\n")
        self.assertEqual(V12N[i:i + len(HELPER)], HELPER); self.assertEqual(V12N[i + len(HELPER):i + len(HELPER) + 4], b"```\n")
        self.assertEqual(len(b"```python\n" + HELPER + b"```"), 18120)  # the ~18,120 in the brief counts the two fence lines
    def test_installed_v12_form_has_the_same_block(self):
        self.assertEqual(block(REAL_INSTALLED["wallet-guardian-notify"]), [HELPER])
    def test_form(self):
        self.assertTrue(R.helper_ok(HELPER)); self.assertTrue(HELPER.endswith(b"\n") and not HELPER.endswith(b"\n\n"))
        self.assertEqual(HELPER.count(b"\n"), 274); self.assertNotIn(b"\r", HELPER)

class DraftText(unittest.TestCase):
    def test_only_listed_lines_changed_outside_s4(self):
        def no4(t):
            a = t.index("## 4. Helper script"); return (t[:a] + t[t.index("## 5. "):]).split("\n")
        old, new = no4(V12N.decode()), no4(NOTE)
        self.assertEqual(len(old), len(new))
        diff = [(o, n) for o, n in zip(old, new) if o != n]
        self.assertEqual([o[:40] for o, _ in diff], ["Run the helper's gate and decide only by", "- Time: always `YYYY-MM-DD HH:MM` plus a",
                                                     "- `not sent` or `blocked by filter` (mis"])
        self.assertIn("wg_notify_run rules-check 2>&1 | wg_mask", diff[0][1]); self.assertIn("taken only from `wg_notify_run time`", diff[1][1])
        self.assertIn("helper not verified", diff[2][1])
    def test_no_embedded_helper_one_pin_one_source(self):
        self.assertNotIn("```python", NOTE); self.assertNotIn("def ", NOTE)
        self.assertEqual(R.notify_pin(NOTE.encode()), (NFAKE, HSHA))
        self.assertEqual(NOTE.count(URL), 2); self.assertEqual(NOTE.count("gitlab.com"), 2); self.assertEqual(NOTE.count(HSHA), 3)
        self.assertEqual(NOTE.count("https://"), V12N.count(b"https://") - HELPER.count(b"https://") + 2)
        for w in ("written from memory", "no other commit, branch, tag, URL, mirror, or host", "no code pasted", "Never edit a copy"):
            self.assertIn(w, NOTE)
    def test_download_command(self):
        for w in ("curl -q --proto =https -sS -o ", "-w '%{http_code}'", '[ "$s" = 200 ];', "sha256sum -c --strict", "mv -fT -- ", "(set -eu; "):
            self.assertIn(w, DL)
        c = DL[DL.index("s=$(curl"):DL.index('"); [ "$s" = 200 ]')]; self.assertEqual(DL.count("curl "), 1)
        for bad in (" -L", "--location", " -f", "--fail", " -k", "--insecure", "--retry"): self.assertNotIn(bad, c)
        self.assertNotIn("mkdir", DL)
        guard = 'case "$WG_DIR/" in /home/box/agent-data/workflows/*|/tmp/*|/var/tmp/*|/dev/shm/*) exit 1;; esac;'
        self.assertLess(DL.index(guard), DL.index("curl")); self.assertLess(DL.index("realpath -e"), DL.index("curl"))
        self.assertLess(DL.index("sha256sum"), DL.index("mv -fT"))
    def test_every_helper_call_goes_through_the_wrapper(self):
        self.assertNotIn('python3 "$WG_DIR/wg_notify.py"', NOTE); self.assertEqual(NOTE.count("python3 "), 1)
        self.assertTrue(RUNF.startswith("wg_notify_run() { python3 -I -B -c '"))
    def test_time_rule_fail_closed(self):
        t = [l for l in NOTE.split("\n") if l.startswith("- Time:")][0]
        for w in ("there is no time source", "(a) included", "never take the time from `date`", "R-15"): self.assertIn(w, t)
    def test_marker_and_render_strip(self):
        self.assertEqual(R.notify(NOTIFY_DRAFT, NFAKE, HELPER_PATH), NOTE)  # render_release rebuilds the committed file
        D = rd(NOTIFY_DRAFT, "r"); self.assertEqual(len(re.findall(r"(?m)^DRAFT-MARKER", D)), 1); self.assertNotIn("DRAFT-MARKER", NOTE)
        self.assertNotIn("draft r", NOTE); self.assertNotIn("<NOTIFY_COMMIT40>", NOTE); self.assertNotIn("<WG_NOTIFY_SHA256>", NOTE)
        self.assertIsNotNone(W.strict_parse(NOTE.encode(), "wallet-guardian-notify"))
    def test_rules_r19_says_install_never_downloads_it(self):
        r = R.strip(RULES_D); self.assertIn("The install never downloads it; wallet-guardian-notify §4 downloads and checks it", r)
        self.assertNotIn("wg_notify", render(V13))

class ReleaseTool(unittest.TestCase):
    def setUp(self): self.t = mkscratch()
    def tearDown(self): shutil.rmtree(self.t, ignore_errors=True)
    def hf(self, b): p = os.path.join(self.t, "h.py"); wr(p, b); return p
    def test_notify_refuses(self):
        for c in ("0" * 40, "abc", NFAKE.upper()):
            with self.assertRaises(W.Fail): R.notify(NOTIFY_DRAFT, c, HELPER_PATH)
        for b in (HELPER.replace(b"\n", b"\r\n"), HELPER + b"\n", HELPER[1:], HELPER + b"```\n", b"\xff" + HELPER):
            with self.assertRaises(W.Fail): R.notify(NOTIFY_DRAFT, NFAKE, self.hf(b))
        bad = os.path.join(self.t, "d.md"); wr(bad, rd(NOTIFY_DRAFT).replace(b"## 5. ", b"```python\nx\n```\n## 5. "))
        with self.assertRaises(W.Fail): R.notify(bad, NFAKE, HELPER_PATH)
    def rel(self, files, helper):
        d = os.path.join(self.t, "x"); shutil.rmtree(d, ignore_errors=True); write_set(d, files, helper)
        return R.instructions(TEMPLATE_PATH, FAKE, d)
    def test_instructions_cross_checks_the_helper(self):
        self.assertEqual(self.rel(V13, HELPER), render(V13))
        for files, helper in ((V13, None), (V13, HELPER + b"#\n"), (dict(V13, **{"wallet-guardian-notify": V12N}), HELPER),
                              (dict(V13, **{"wallet-guardian-notify": R.strip(rd(NOTIFY_DRAFT, "r")).encode()}), HELPER),
                              (dict(V13, **{"wallet-guardian-notify": V13["wallet-guardian-notify"].replace(HSHA.encode(), b"0" * 64, 1)}), HELPER)):
            with self.assertRaises((W.Fail, OSError)): self.rel(files, helper)

class Shell(unittest.TestCase):
    def setUp(self):
        self.t = mkscratch(); self.W = os.path.join(self.t, "approved"); os.mkdir(self.W)
        b = os.path.join(self.t, "bin"); os.mkdir(b); wr(os.path.join(b, "curl"), FAKE_CURL); os.chmod(os.path.join(b, "curl"), 0o755)
        self.src = os.path.join(self.t, "served.py"); wr(self.src, HELPER); self.log = os.path.join(self.t, "curl.log")
        self.env = {"PATH": b + ":/usr/bin:/bin", "CURL_LOG": self.log, "CURL_SRC": self.src, "HOME": self.t}
        self.f = os.path.join(self.W, "wg_notify.py")
    def tearDown(self): shutil.rmtree(self.t, ignore_errors=True)
    def sh(self, script, wg=None, **env):
        e = dict(self.env, **env); e["WG_DIR"] = self.W if wg is None else wg
        return subprocess.run(["bash", "-c", script], env=e, cwd=self.t, capture_output=True, text=True)
    def calls(self): return rd(self.log, "r").splitlines() if os.path.exists(self.log) else []
    def run_(self, *args, **env): return self.sh(RUNF + "; wg_notify_run " + " ".join(args), **env)
    def test_download_ok(self):
        r = self.sh(DL); self.assertEqual((r.returncode, r.stdout.strip().split("\n")[-1]), (0, "helper: verified"), r.stderr)
        self.assertEqual(rd(self.f), HELPER); self.assertEqual(sorted(os.listdir(self.W)), ["wg_notify.py"])
        c = self.calls(); self.assertEqual(len(c), 1); self.assertTrue(c[0].startswith("-q --proto =https -sS -o wg_notify.py.part -w "))
        self.assertTrue(c[0].endswith(" " + URL)); self.assertNotIn("-L", c[0].split())
    def test_download_failures_leave_nothing(self):
        for mode in ("404", "302", "neterr", "tamper", "short"):
            r = self.sh(DL, CURL_MODE=mode); self.assertNotEqual(r.returncode, 0, mode); self.assertNotIn("helper: verified", r.stdout)
            self.assertEqual(os.listdir(self.W), [], mode)
    def test_failed_download_keeps_existing_file(self):
        for existing in (HELPER, HELPER + b"# changed\n"):
            wr(self.f, existing); r = self.sh(DL, CURL_MODE="tamper"); self.assertNotEqual(r.returncode, 0)
            self.assertEqual(rd(self.f), existing); self.assertEqual(os.listdir(self.W), ["wg_notify.py"])
    def test_bad_folder_refused_before_curl(self):
        os.symlink(self.W, os.path.join(self.t, "link")); os.mkdir(os.path.join(self.t, "a b"))
        for wg in ("approved", self.W + "/", self.W + "/../approved", os.path.join(self.t, "link"), os.path.join(self.t, "a b"),
                   os.path.join(self.t, "missing"), "/home/box/agent-data/workflows", "/tmp", "/var/tmp", "/dev/shm", ""):
            r = self.sh(DL, wg=wg); self.assertNotEqual(r.returncode, 0, wg)
        self.assertEqual(self.calls(), []); self.assertEqual(os.listdir(self.W), [])
    def test_wrapper_runs_only_the_pinned_bytes(self):
        wr(self.f, HELPER); r = self.run_("time", TZ="Etc/GMT-8"); self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout.strip(), r"^\d{4}-\d\d-\d\d \d\d:\d\d \+08:00$")
        r = self.run_("time 0", TZ="UTC0"); self.assertEqual(r.stdout.strip(), "1970-01-01 00:00 +00:00")
        direct = subprocess.run([sys.executable, "-B", self.f, "filter"], input="new approval | Ledger <0x1234…abcd> | Ethereum",
                                capture_output=True, text=True, env={"WG_DIR": self.W, "PATH": "/usr/bin:/bin"})
        r = self.sh(RUNF + "; printf '%s' 'new approval | Ledger <0x1234…abcd> | Ethereum' | wg_notify_run filter")
        self.assertEqual((r.returncode, r.stdout), (direct.returncode, direct.stdout))
    def test_wrapper_refuses_changed_or_missing_file(self):
        ran = os.path.join(self.W, "ran")
        for b in (None, HELPER + b"open(D + '/ran', 'w')\n", HELPER.replace(b"TTL = 900", b"TTL = 901"), b""):
            if os.path.lexists(self.f): os.remove(self.f)
            if b is not None: wr(self.f, b)
            for cmd in ("time", "rules-check", "tg-send"):
                r = self.run_(cmd); self.assertNotEqual(r.returncode, 0); self.assertEqual(r.stdout, "")
                self.assertIn("refused: wg_notify.py is missing or not the pinned file; nothing ran", r.stderr)
            self.assertFalse(os.path.exists(ran))
        os.remove(self.f); os.mkdir(self.f); self.assertNotEqual(self.run_("time").returncode, 0)
    def test_v12_upgrade_copy_passes_without_download(self):
        wr(self.f, block(REAL_INSTALLED["wallet-guardian-notify"])[0]); r = self.run_("time", TZ="UTC0")
        self.assertEqual(r.returncode, 0, r.stderr); self.assertEqual(self.calls(), [])

class InstallIndependent(unittest.TestCase):
    def test_six_install_and_check_without_any_helper(self):
        t = mkscratch()
        try:
            lib = os.path.join(t, "lib"); os.mkdir(lib); F = os.path.join(t, "a"); os.mkdir(F); D = make_D(F, V13)
            for n in W.NAMES: wr(os.path.join(lib, n, "SKILL.md"), installer_form(V13[n], n))
            rc, out, last = run("check-installed", D, root=lib); self.assertEqual((rc, last), (0, "result: all six installed and same"), out)
            for root, _, fs in os.walk(t): self.assertNotIn("wg_notify.py", fs)
        finally: shutil.rmtree(t, ignore_errors=True)

if __name__ == "__main__": unittest.main(verbosity=2)

# Runs the exact command text of the instructions' Steps 2, 3, and 4 (taken from an in-memory release render for a
# fixture commit) through bash, with a fake curl first on PATH that serves fixture files. No network, no /tmp.
# Not tested here: a real bot, the platform's install tool, the real GitLab (the raw-URL download at the pinned commits is an owner step after the push).
import hashlib, os, shutil, stat, subprocess, sys, unittest
from testlib import *

FAKE_CURL = r'''#!/usr/bin/env python3
import os, sys
a = sys.argv[1:]; open(os.environ["CURL_LOG"], "a").write(" ".join(a) + "\n")
o = a[a.index("-o") + 1]; url = a[-1]; mode = os.environ.get("CURL_MODE", "ok")
name = url.split("/skills/")[1].split("/")[0] if "/skills/" in url else ""
if mode == "neterr": sys.exit(6)
code = {"302": "302", "404": "404"}.get(mode, "200") if (mode == "ok" or name.endswith(os.environ.get("CURL_ON", ""))) else "200"
src = os.path.join(os.environ["CURL_SRC"], name, "SKILL.md")
os.makedirs(os.path.dirname(o), exist_ok=True)
open(o, "wb").write(open(src, "rb").read() if code == "200" else b"<html>moved</html>")
sys.stdout.write(code)
'''

def lines_after(text, head):
    L = text.split("\n"); return L[L.index(next(l for l in L if l.startswith(head))) + 1]

class BotPath(unittest.TestCase):
    def setUp(self):
        self.t = mkscratch(); self.lib = os.path.join(self.t, "lib"); os.mkdir(self.lib)
        self.F = os.path.join(self.t, "approved"); os.mkdir(self.F)
        # Fixture MR A: the helper copy inside this test's welcome scans the fixture library instead of the real one.
        self.files = dict(V13); w = self.files["wallet-guardian-welcome"].decode()
        assert w.count('WORKFLOWS = "/home/box/agent-data/workflows"') == 1
        self.files["wallet-guardian-welcome"] = w.replace('WORKFLOWS = "/home/box/agent-data/workflows"', "WORKFLOWS = %r" % self.lib).encode()
        self.src = os.path.join(self.t, "repo"); write_set(self.src, self.files, HELPER)  # helper present upstream, never fetched
        self.rel = render(self.files); self.pins = pins_for(self.files)
        self.step2 = lines_after(self.rel, "- Step 2, download")
        self.loader = lines_after(self.rel, "- Step 4, check")
        bindir = os.path.join(self.t, "bin"); os.mkdir(bindir); wr(os.path.join(bindir, "curl"), FAKE_CURL); os.chmod(os.path.join(bindir, "curl"), 0o755)
        self.env = {"PATH": bindir + ":/usr/bin:/bin", "CURL_LOG": os.path.join(self.t, "curl.log"), "CURL_SRC": self.src, "HOME": self.t}
        self.D = os.path.join(self.F, "wg-install-" + FAKE[:8])
    def tearDown(self): shutil.rmtree(self.t, ignore_errors=True)
    def sh(self, script, F=None, cwd=None, **env):
        e = dict(self.env, **env); e["F"] = self.F if F is None else F
        return subprocess.run(["bash", "-c", script], env=e, cwd=cwd or self.t, capture_output=True, text=True)
    def step2_run(self, **k): return self.sh(self.step2, **k)
    def step3_run(self, pins=None):
        r = self.sh('cd "$F/wg-install-%s" && cat > wg-pinned.sha256 <<\'P\'\n%sP\nsha256sum -c --strict wg-pinned.sha256' % (FAKE[:8], pins or self.pins))
        return r, r.returncode == 0 and r.stdout.count(": OK\n") == 6
    def helper(self, cmd, name="", stdin=None, welcome=None, cwd=None):
        line = self.loader.replace("COMMAND", cmd).replace(" [NAME]", (" " + name) if name else "")
        if welcome: line = line.replace('"$D/wallet-guardian-welcome/SKILL.md"', welcome)
        r = self.sh('D="$F/wg-install-%s"; %s <<\'P\'\n%sP' % (FAKE[:8], line, stdin if stdin is not None else self.pins), cwd=cwd)
        return r, r.stdout.rstrip("\n").split("\n")[-1] if r.stdout else ""

    def test_happy_path(self):
        r = self.step2_run(); self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(oct(os.stat(self.D).st_mode & 0o777), "0o700")
        r, ok = self.step3_run(); self.assertTrue(ok, r.stdout + r.stderr)
        r, last = self.helper("check-instructions", stdin=self.rel); self.assertEqual((r.returncode, last), (0, "result: instructions ok"), r.stdout + r.stderr)
        r, last = self.helper("compare"); self.assertEqual((r.returncode, last), (0, "result: install only: " + ", ".join(W.NAMES)), r.stdout + r.stderr)
        log = rd(self.env["CURL_LOG"], "r"); self.assertEqual(log.count("\n"), 6)
        for line in log.splitlines(): self.assertTrue(line.startswith("-q --proto =https -sS --create-dirs -o "), line)
        self.assertNotIn("-L", log.split()); self.assertNotIn("wg_notify", log)
        self.assertEqual(sorted(os.listdir(os.path.join(self.D, "wallet-guardian-notify"))), ["SKILL.md"])
    def test_simulated_install_then_checks(self):
        self.step2_run(); self.step3_run()
        for i, n in enumerate(W.NAMES):  # the install tool is simulated by the installer model; not the real UpdateSkill
            wr(os.path.join(self.lib, n, "SKILL.md"), installer_form(self.files[n], n))
            r, last = self.helper("check-one", n); self.assertEqual(last, "result: %s installed and same" % n, r.stdout)
        r, last = self.helper("check-installed"); self.assertEqual((r.returncode, last), (0, "result: all six installed and same"))
    def test_redirect_404_neterr_fail(self):
        for mode in ("302", "404", "neterr"):
            r = self.step2_run(CURL_MODE=mode, CURL_ON="keys"); self.assertNotEqual(r.returncode, 0, mode)
            shutil.rmtree(self.D, ignore_errors=True)
    def test_bad_F(self):
        for F in ("approved", self.F + "/../approved", self.F + "/a b", self.F + "/$(id)", self.F + "/x;y", ""):
            r = self.step2_run(F=F); self.assertNotEqual(r.returncode, 0, F)
        self.assertEqual(os.listdir(self.F), [])
    def test_existing_or_symlinked_D_refused(self):
        os.mkdir(self.D); wr(os.path.join(self.D, "keep"), "x"); self.assertNotEqual(self.step2_run().returncode, 0)
        self.assertTrue(os.path.exists(os.path.join(self.D, "keep")))
        shutil.rmtree(self.D); os.symlink(self.t, self.D); self.assertNotEqual(self.step2_run().returncode, 0)
    def test_single_quoted_assignment_does_not_execute(self):
        marker = os.path.join(self.t, "pwned")
        r = self.sh("F='%s/$(touch %s)'; %s" % (self.F, marker, self.step2), F="unused")
        self.assertNotEqual(r.returncode, 0); self.assertFalse(os.path.exists(marker))
    def test_F_symlink_or_symlinked_parent_refused_before_mkdir(self):
        target = os.path.join(self.t, "library"); os.mkdir(target)  # stands in for a folder F could point into
        link = os.path.join(self.t, "link"); os.symlink(target, link); os.mkdir(os.path.join(target, "sub"))
        for F in (link, link + "/sub", self.F + "/"):
            r = self.step2_run(F=F); self.assertNotEqual(r.returncode, 0, F)
        self.assertEqual(os.listdir(target), ["sub"]); self.assertEqual(os.listdir(os.path.join(target, "sub")), [])
        self.assertFalse(os.path.exists(self.env["CURL_LOG"]), "curl never ran")
    def test_library_F_refused_before_mkdir(self):
        # The fixture library stands in for /home/box/agent-data/workflows (the real library is never touched).
        step2 = self.step2.replace("/home/box/agent-data/workflows/*", self.lib + "/*"); os.mkdir(os.path.join(self.lib, "x"))
        for F in (self.lib, self.lib + "/x"):
            r = self.sh(step2, F=F); self.assertNotEqual(r.returncode, 0, F)
        self.assertEqual(os.listdir(self.lib), ["x"]); self.assertEqual(os.listdir(os.path.join(self.lib, "x")), [])
    def test_shared_tmp_F_refused_before_mkdir(self):
        # Rejection only: the command exits before mkdir, so nothing is created in these folders.
        for F in ("/tmp", "/var/tmp", "/dev/shm"):
            if not os.path.isdir(F) or os.path.realpath(F) != F: continue
            d = F + "/wg-install-" + FAKE[:8]; self.assertFalse(os.path.lexists(d))
            self.assertNotEqual(self.step2_run(F=F).returncode, 0, F); self.assertFalse(os.path.lexists(d))
        self.assertFalse(os.path.exists(self.env["CURL_LOG"]))
    def test_missing_parent_refused(self): self.assertNotEqual(self.step2_run(F=self.F + "/nope").returncode, 0)
    def test_short_manifest_not_six_ok(self):
        self.step2_run(); r, ok = self.step3_run("".join(self.pins.splitlines(True)[:5]))
        self.assertEqual(r.returncode, 0, "sha256sum alone passes a 5-line file"); self.assertFalse(ok, "the six-OK rule catches it")
    def test_loader_fails_closed(self):
        self.step2_run(); self.step3_run()
        v12w = os.path.join(self.t, "v12-welcome.md"); wr(v12w, REPO["wallet-guardian-welcome"])
        empty = os.path.join(self.t, "empty.md"); wr(empty, b"")
        two = os.path.join(self.t, "two.md"); wr(two, self.files["wallet-guardian-welcome"] * 2)
        for w in (v12w, empty, two, os.path.join(self.t, "nope.md")):
            r, last = self.helper("compare", welcome=w); self.assertNotEqual(r.returncode, 0, w); self.assertNotIn("result: install only", r.stdout)
        p = os.path.join(self.D, "wallet-guardian-welcome", "SKILL.md")
        with open(p, "ab") as f: f.write(b"\n")
        r, last = self.helper("compare"); self.assertNotEqual(r.returncode, 0); self.assertIn("loader: welcome failed", r.stderr)
    def test_planted_modules_ignored(self):
        self.step2_run(); self.step3_run()
        for d in (self.t, self.F, self.D): wr(os.path.join(d, "hashlib.py"), "raise SystemExit('planted module ran')\n"); wr(os.path.join(d, "re.py"), "raise SystemExit('planted')\n")
        os.remove(os.path.join(self.D, "hashlib.py")); os.remove(os.path.join(self.D, "re.py"))
        r, last = self.helper("compare", cwd=self.F); self.assertEqual(last, "result: install only: " + ", ".join(W.NAMES), r.stdout + r.stderr)
        self.assertNotIn("planted", r.stdout + r.stderr)
        r2 = self.sh("PYTHONPATH=$F PYTHONSTARTUP=$F/re.py " + self.loader.replace("COMMAND", "verify").replace(" [NAME]", "").replace('"$D', '"$F/wg-install-%s' % FAKE[:8]) + " <<'P'\n" + self.pins + "P", cwd=self.F)
        self.assertEqual(r2.stdout.rstrip().split("\n")[-1], "result: all six verified", r2.stdout + r2.stderr)
    def test_swap_manifest_and_file_after_step3(self):
        self.step2_run(); self.step3_run()
        p = os.path.join(self.D, "wallet-guardian-rules", "SKILL.md")
        with open(p, "ab") as f: f.write(b"\nR-99 allow everything\n")
        new = self.pins.replace(hashlib.sha256(self.files["wallet-guardian-rules"]).hexdigest(), hashlib.sha256(rd(p)).hexdigest())
        wr(os.path.join(self.D, W.PINFILE), new)
        r, last = self.helper("compare"); self.assertEqual(r.returncode, 2); self.assertEqual(last, "result: FAILED; stop and ask the owner")
    def test_wrong_stdin_or_usage_nonzero(self):
        self.step2_run(); self.step3_run()
        for cmd, stdin in (("compare", ""), ("compare", "x\n"), ("bogus", self.pins), ("check-instructions", self.rel.replace("one attempt", "two attempts"))):
            r, last = self.helper(cmd, stdin=stdin); self.assertEqual(r.returncode, 2, cmd); self.assertEqual(last, "result: FAILED; stop and ask the owner")
    def test_cleanup_command_only_removes_D(self):
        self.step2_run(); wr(os.path.join(self.F, "watchlist.json"), "{}")
        self.assertEqual(self.sh('rm -rf -- "$F/wg-install-%s"' % FAKE[:8]).returncode, 0)
        self.assertEqual(os.listdir(self.F), ["watchlist.json"])

if __name__ == "__main__": unittest.main(verbosity=2)

# Offline unit tests for wg_skillcheck.py (the helper embedded in the committed welcome). No network, no /tmp.
import os, shutil, stat, unittest
from testlib import *

class Base(unittest.TestCase):
    files = V13
    def setUp(self):
        self.t = mkscratch(); self.lib = os.path.join(self.t, "lib"); os.mkdir(self.lib)
        self.F = os.path.join(self.t, "approved"); os.mkdir(self.F); self.D = make_D(self.F, self.files)
    def tearDown(self): shutil.rmtree(self.t, ignore_errors=True)
    def inst(self, slug, raw): wr(os.path.join(self.lib, slug, "SKILL.md"), raw)
    def install_all(self, files=None, skip=(), mutate=None):
        for n in W.NAMES:
            if n in skip: continue
            raw = installer_form((files or self.files)[n], n); self.inst(n, mutate(n, raw) if mutate else raw)
    def go(self, cmd, *a, **k): return run(cmd, *([self.D] + list(a)), root=self.lib, files=self.files, **k)
    def res(self): return W.classify(self.D, W.parse_pins(pins_for(self.files)), self.lib)

class Pins(unittest.TestCase):
    def test_good(self): self.assertEqual(len(W.parse_pins(pins_for(V13))), 6)
    def test_bad(self):
        g = pins_for(V13); L = g.split("\n")
        for bad in ["\n".join(L[:5]) + "\n", g + L[0] + "\n", g.replace("  ", " ", 1), g.upper(), "",
                    g.replace("  wallet", "  skills/wallet", 1), g.replace("wallet-guardian-keys", "wallet-guardian-example")]:
            with self.assertRaises(W.Fail): W.parse_pins(bad)

class Folder(Base):
    def test_ok(self): self.assertEqual(self.go("verify")[2], "result: all six verified")
    def bad(self, d, why):
        rc, out, last = run("verify", d, root=self.lib); self.assertEqual(rc, 2, out); self.assertIn(why, out); self.assertEqual(last, "result: FAILED; stop and ask the owner")
    def test_relative_dotdot_charset(self):
        self.bad("approved/wg-install-" + FAKE[:8], "only absolute")
        self.bad(self.F + "/../approved/wg-install-" + FAKE[:8], "no . or ..")
        self.bad(self.F.replace("approved", "appr oved") + "/wg-install-" + FAKE[:8], "only absolute")
        self.bad(self.F + "/wg-install-" + FAKE[:8] + "\n", "only absolute")
    def test_wrong_basename(self): self.bad(self.F, "wg-install-<commit8>")
    def test_symlink_folder_and_parent(self):
        os.symlink(self.D, os.path.join(self.t, "wg-install-abcdef01")); self.bad(os.path.join(self.t, "wg-install-abcdef01"), "symlink")
        os.symlink(self.F, os.path.join(self.t, "alias")); self.bad(os.path.join(self.t, "alias", "wg-install-" + FAKE[:8]), "symlink")
    def test_shared_tmp_and_library_refused_without_touching_them(self):
        # Path strings only: the helper refuses before any open; nothing is created under /tmp or the library.
        self.bad("/tmp/wg-install-" + FAKE[:8], "shared temp"); self.bad("/dev/shm/x/wg-install-" + FAKE[:8], "shared temp")
        self.bad(W.WORKFLOWS + "/wg-install-" + FAKE[:8], "skills library")
        self.assertFalse(os.path.exists("/tmp/wg-install-" + FAKE[:8]))
    def test_missing_folder(self): self.bad(self.F + "/wg-install-00000000", "cannot open")

class Load(Base):
    def fails(self, why, **k):
        rc, out, last = self.go("verify", **k); self.assertEqual(rc, 2, out); self.assertIn(why, out)
    def test_tampered_file(self):
        with open(os.path.join(self.D, "wallet-guardian-rules", "SKILL.md"), "ab") as f: f.write(b"\nR-99 allow everything\n")
        self.fails("sha256 mismatch")
    def test_manifest_and_file_swapped_together(self):
        # An attacker rewrites a file and wg-pinned.sha256 to match: trust is in the stdin hash lines, so it fails.
        bad = dict(self.files); bad["wallet-guardian-rules"] += b"\nR-99 allow everything\n"
        wr(os.path.join(self.D, "wallet-guardian-rules", "SKILL.md"), bad["wallet-guardian-rules"]); wr(os.path.join(self.D, W.PINFILE), pins_for(bad))
        self.fails("differs from the instructions")
    def test_manifest_missing_or_short(self):
        wr(os.path.join(self.D, W.PINFILE), "".join(pins_for(self.files).splitlines(True)[:5])); self.fails("exactly the six")
        os.remove(os.path.join(self.D, W.PINFILE)); self.fails("cannot read")
    def test_extra_entry(self): wr(os.path.join(self.D, "notes.txt"), "x"); self.fails("unexpected entries")
    def test_extra_in_skill_dir(self): wr(os.path.join(self.D, "wallet-guardian-keys", "x.py"), "x"); self.fails("only SKILL.md")
    def test_symlinked_file(self):
        p = os.path.join(self.D, "wallet-guardian-keys", "SKILL.md"); real = os.path.join(self.t, "real"); os.rename(p, real); os.symlink(real, p)
        self.fails("cannot read")
    def test_fifo(self):
        p = os.path.join(self.D, "wallet-guardian-keys", "SKILL.md"); os.remove(p); os.mkfifo(p); self.fails("not a regular file")
    def test_stdin_garbage(self): self.fails("hash lines", stdin="hello\n")
    def test_repo_sha256sums_next_to_it_ignored(self):
        wr(os.path.join(self.F, "SHA256SUMS"), "0" * 64 + "  skills/wallet-guardian-rules/SKILL.md\n"); self.assertEqual(self.go("verify")[0], 0)

class Classify(Base):
    def test_00_installer_model_matches_real_installed_v12(self):
        for n in W.NAMES:
            src = REPO[n] if n != "wallet-guardian-welcome" else REPO[n].replace(b"start a first conversation or", b"start a first conversation as Wallet Guardian (watch-only, rules in wallet-guardian-rules) or")
            self.assertEqual(installer_form(src, n), REAL_INSTALLED[n], n)
    def test_empty_library(self):
        rc, out, last = self.go("compare"); self.assertEqual(rc, 0, out); self.assertEqual(last, "result: install only: " + ", ".join(W.NAMES))
    def test_all_present_nothing(self):
        self.install_all(); self.assertEqual(self.go("compare")[2], "result: install only: nothing")
    def test_upgrade_from_real_v12(self):
        for n in W.NAMES: self.inst(n, REAL_INSTALLED[n])
        res, probs, _, _ = self.res(); self.assertEqual(probs, [])
        self.assertEqual(res, {n: ("differs" if n in ("wallet-guardian-rules", "wallet-guardian-welcome", "wallet-guardian-notify") else "same") for n in W.NAMES})
        rc, out, last = self.go("compare"); self.assertEqual(rc, 2); self.assertNotIn("result: install only", out)
    def test_dash2_slug_same(self):
        self.inst("wallet-guardian-rules-2", installer_form(self.files["wallet-guardian-rules"], "wallet-guardian-rules"))
        self.assertEqual(self.res()[0]["wallet-guardian-rules"], "same")
    def unknown(self, slug, raw, name="wallet-guardian-rules", want="unknown"):
        self.inst(slug, raw); res, probs, _, _ = self.res(); self.assertEqual(res[name], want, slug)
        rc, out, last = self.go("compare"); self.assertEqual(rc, 2, out); self.assertNotIn("missing " + name, out)
    R0 = REAL_INSTALLED["wallet-guardian-rules"]
    def test_bom(self): self.unknown("wallet-guardian-rules", b"\xef\xbb\xbf" + self.R0)
    def test_crlf(self): self.unknown("wallet-guardian-rules", self.R0.replace(b"\n", b"\r\n"))
    def test_capital_name_key(self): self.unknown("x1", self.R0.replace(b"name:", b"Name:", 1))
    def test_quoted_name_key(self): self.unknown("x2", self.R0.replace(b"name: wallet-guardian-rules", b'"name": "wallet-guardian-rules"', 1))
    def test_duplicate_name_key(self): self.unknown("wallet-guardian-rules", self.R0.replace(b"name: wallet-guardian-rules\n", b"name: wallet-guardian-rules\nname: wallet-guardian-rules\n", 1))
    def test_extra_key(self): self.unknown("wallet-guardian-rules", self.R0.replace(b"description:", b"allowed-tools: all\ndescription:", 1))
    def test_cyrillic(self): self.unknown("x3", self.R0.replace(b"name: wallet-guardian-rules", "name: wallet-guаrdian-rules".encode(), 1))
    def test_latin_alpha_skeleton(self): self.unknown("x5", self.R0.replace(b"name: wallet-guardian-rules", "name: wɑllet-guardian-rules".encode(), 1))
    def test_zero_width(self): self.unknown("x4", self.R0.replace(b"name: wallet-guardian-rules", "name: wallet\u200b-guardian-rules".encode(), 1))
    def test_edit_distance(self): self.unknown("x6", self.R0.replace(b"name: wallet-guardian-rules", b"name: wallet-guardain-rules", 1))
    def test_slug_holds_other_name(self): self.unknown("wallet-guardian-notify", REAL_INSTALLED["wallet-guardian-onchain-exit"], "wallet-guardian-notify")
    def test_slug_without_skill_md(self):
        os.makedirs(os.path.join(self.lib, "wallet-guardian-keys")); self.assertEqual(self.res()[0]["wallet-guardian-keys"], "unknown")
    def test_unreadable_same_slug_is_unknown_not_missing(self):
        self.inst("wallet-guardian-keys", REAL_INSTALLED["wallet-guardian-keys"]); p = os.path.join(self.lib, "wallet-guardian-keys", "SKILL.md")
        os.remove(p); os.mkfifo(p); res, probs, _, _ = self.res(); self.assertEqual(res["wallet-guardian-keys"], "unknown"); self.assertTrue(probs)
    def test_unclosed_frontmatter_same_slug_unknown(self):
        self.unknown("wallet-guardian-keys", b"---\nname: wallet-guardian-keys\n" + b"x" * 9000, "wallet-guardian-keys")
    def test_symlinked_skill_dir(self):
        real = os.path.join(self.t, "elsewhere"); wr(os.path.join(real, "SKILL.md"), REAL_INSTALLED["wallet-guardian-keys"])
        os.symlink(real, os.path.join(self.lib, "wallet-guardian-keys")); self.assertEqual(self.res()[0]["wallet-guardian-keys"], "unknown")
    def test_non_utf8_anywhere_blocks(self):
        self.inst("some-other-skill", b"---\nname: some-other-skill\n---\n\xff\xfe"); rc, out, last = self.go("compare")
        self.assertEqual(rc, 2); self.assertIn("not valid UTF-8", out); self.assertIn("blocked wallet-guardian-rules", out); self.assertNotIn("missing ", out)
    def no_missing(self, out):  # a compare that did not pass never prints an installable "missing" line
        self.assertEqual([l for l in out.split("\n") if l.startswith("missing ")], [], out)
    def test_yaml_tricks_in_name_value_block(self):
        # Values PLAIN_NAME rejects: a problem line, so the compare fails and nothing is listed as missing.
        for i, v in enumerate([b'"wallet-guardian-\\x72ules"', b"wallet-guardian-rules # c", b">-", b"!!str wallet-guardian-rules", b"'wallet-guardian-rules"]):
            shutil.rmtree(self.lib); os.mkdir(self.lib)
            self.inst("y%d" % i, b"---\nname: " + v + b"\ndescription: x\n---\nbody\n")
            rc, out, last = self.go("compare"); self.assertEqual(rc, 2, v); self.assertIn("not a plain name", out, v); self.no_missing(out)
    def test_paired_quoted_name_is_unknown_and_blocks_the_rest(self):
        # PLAIN_NAME allows paired quotes, so these match the name: unknown (no problem line); the others print blocked.
        for i, v in enumerate([b"'wallet-guardian-rules'", b'"wallet-guardian-rules"']):
            shutil.rmtree(self.lib); os.mkdir(self.lib)
            self.inst("q%d" % i, b"---\nname: " + v + b"\ndescription: x\n---\nbody\n")
            rc, out, last = self.go("compare"); self.assertEqual((rc, last), (2, "result: FAILED; stop and ask the owner"), v)
            self.assertIn("unknown wallet-guardian-rules", out); self.assertNotIn("problem", out); self.no_missing(out)
            for n in W.NAMES[1:]: self.assertIn("blocked " + n + "\n", out)
    def test_same_name_not_a_directory_is_unknown(self):
        # A same-name library entry that is a regular file, FIFO, or socket exists (R-19 "name match = exists"); never missing.
        import contextlib, socket
        for slug, kind in (("wallet-guardian-keys", "file"), ("wallet-guardian-keys", "fifo"), ("Wallet-Guardian-Keys", "file"),
                           ("wallet-guardian-keys-2", "fifo"), ("wallet-guardian-keyz", "file"), ("wallet-guardian-keys", "socket")):
            shutil.rmtree(self.lib); os.mkdir(self.lib); p = os.path.join(self.lib, slug)
            if kind == "file": wr(p, "x")
            elif kind == "fifo": os.mkfifo(p)
            else:  # bind by a relative name: the scratch path can exceed the AF_UNIX path limit (104/108 bytes)
                with contextlib.chdir(self.lib): s = socket.socket(socket.AF_UNIX); s.bind(slug); s.close()
            for cmd in ("compare", "check-installed"):
                rc, out, last = self.go(cmd); self.assertEqual((rc, last), (2, "result: FAILED; stop and ask the owner"), (slug, kind, cmd))
                self.assertIn("unknown wallet-guardian-keys", out); self.assertIn("problem %s: same name but not a directory" % slug, out); self.no_missing(out)
            self.assertEqual(self.go("show-diff", "wallet-guardian-keys")[0], 2)
    def test_unrelated_non_directory_ignored(self):
        wr(os.path.join(self.lib, "README.txt"), "x"); os.mkfifo(os.path.join(self.lib, "some-pipe"))
        self.assertEqual(self.go("compare")[2], "result: install only: " + ", ".join(W.NAMES))
    def test_failed_compare_prints_blocked_not_missing(self):
        self.install_all(skip=W.NAMES[:5], mutate=lambda n, raw: raw + b"\nextra\n")
        rc, out, last = self.go("compare"); self.assertEqual(rc, 2); self.assertIn("differs wallet-guardian-notify", out); self.no_missing(out)
        for n in W.NAMES[:5]: self.assertIn("blocked " + n + "\n", out)
    def test_unreadable_unrelated_blocks(self):
        os.makedirs(os.path.join(self.lib, "other")); os.mkfifo(os.path.join(self.lib, "other", "SKILL.md")); self.assertTrue(self.res()[1])
    def test_two_copies(self):
        self.inst("wallet-guardian-rules", self.R0); self.inst("wallet-guardian-rules-2", self.R0); self.assertEqual(self.res()[0]["wallet-guardian-rules"], "duplicate")
    def test_unrelated_wallet_guardian_skill_ignored(self):
        self.inst("wallet-guardian-example", b"---\nname: wallet-guardian-example\ndescription: \"x\"\n---\nbody\n")
        res, probs, _, _ = self.res(); self.assertEqual(probs, []); self.assertEqual(set(res.values()), {"missing"})

class Installed(Base):
    def test_all_same_passes(self):
        self.install_all(); rc, out, last = self.go("check-installed"); self.assertEqual((rc, last), (0, "result: all six installed and same"), out)
    def test_check_one(self):
        self.install_all(skip=W.NAMES[1:]); rc, out, last = self.go("check-one", "wallet-guardian-rules")
        self.assertEqual((rc, last), (0, "result: wallet-guardian-rules installed and same"), out)
        self.assertEqual(self.go("check-one", "wallet-guardian-keys")[0], 2)
        self.assertEqual(self.go("check-one", "wallet-guardian-example")[0], 2)
    def test_v12_fails(self):
        for n in W.NAMES: self.inst(n, REAL_INSTALLED[n])
        self.assertEqual(self.go("check-installed")[0], 2)
    def test_one_missing(self): self.install_all(skip=("wallet-guardian-keys",)); self.assertEqual(self.go("check-installed")[0], 2)
    def test_truncated(self):
        self.install_all(mutate=lambda n, r: r[:len(r) // 2] if n == "wallet-guardian-notify" else r)
        rc, out, _ = self.go("check-installed"); self.assertEqual(rc, 2); self.assertIn("differs wallet-guardian-notify", out)
    def test_retyped(self):
        self.install_all(mutate=lambda n, r: r.replace(b"R-19 Installing", b"R-19  Installing") if n == "wallet-guardian-rules" else r)
        self.assertEqual(self.go("check-installed")[0], 2)
    def test_duplicate_after_install(self):
        self.install_all(); self.inst("wallet-guardian-welcome-2", installer_form(self.files["wallet-guardian-welcome"], "wallet-guardian-welcome"))
        self.assertEqual(self.go("check-installed")[0], 2)

class DraftPinned(Base):
    # If someone pins the drafts with their DRAFT-MARKER lines still in, check-one and check-installed refuse.
    files = dict(V13, **{"wallet-guardian-rules": RULES_D.encode(), "wallet-guardian-welcome": WELCOME_D.encode()})
    def test_draft_marker_blocks(self):
        self.install_all(); self.assertEqual(self.go("compare")[2], "result: install only: nothing")
        rc, out, last = self.go("check-installed"); self.assertEqual(rc, 2, out)
        self.assertEqual(self.go("check-one", "wallet-guardian-rules")[0], 2)

class NoEndLine(Base):
    files = dict(V13, **{"wallet-guardian-rules": V13["wallet-guardian-rules"].replace(b"\nEnd of wallet-guardian-rules v1.3\n", b"\n")})
    def test_rules_without_end_line_fail(self):
        self.install_all(); self.assertEqual(self.go("check-installed")[0], 2); self.assertEqual(self.go("check-one", "wallet-guardian-rules")[0], 2)

class ShowDiff(Base):
    def test_diff_and_sanitised(self):
        self.inst("wallet-guardian-rules", REAL_INSTALLED["wallet-guardian-rules"].replace(b"R-18 Campaigns.", "R-18 Campaigns.\u202e\u200b\x1b[2J".encode()))
        rc, out, last = self.go("show-diff", "wallet-guardian-rules"); self.assertEqual((rc, last), (0, "result: diff shown"), out)
        self.assertIn("+R-19 Installing", out); self.assertIn("\\u202e", out); self.assertIn("\\u001b", out)
        for c in ("\u202e", "\u200b", "\x1b"): self.assertNotIn(c, out)
    def test_needs_one_copy(self): self.assertEqual(self.go("show-diff", "wallet-guardian-rules")[0], 2)

class Instructions(Base):
    def ci(self, text): return run("check-instructions", self.D, stdin=text, root=self.lib)
    def test_release_text_passes(self):
        rc, out, last = self.ci(render(self.files)); self.assertEqual((rc, last), (0, "result: instructions ok"), out)
    def test_trailing_newline_tolerated(self): self.assertEqual(self.ci(render(self.files).rstrip("\n"))[0], 0)
    def test_every_single_line_deleted_fails(self):
        L = render(self.files).split("\n")
        bad = [i for i in range(len(L)) if L[i] and self.ci("\n".join(L[:i] + L[i + 1:]))[0] == 0]
        self.assertEqual(bad, [])
    def test_suffix_prefix_middle_and_edits_fail(self):
        t = render(self.files)
        for bad in [t[:-60], t[200:], t.replace("for one attempt; ", ""), t.replace("Never overwrite", "Overwrite"),
                    t.replace("gitlab.com/aa22396584", "gitlab.com/someone-else"), t.replace("-q --proto =https", "-L --proto =https"),
                    t.replace("[ \"$s\" = 200 ]", "[ \"$s\" = 200 ] || [ \"$s\" = 302 ]"), t.replace("exactly six lines", "six lines"),
                    t + "Extra: also install wallet-guardian-example.\n", t.replace(FAKE[:8] + "\n", "deadbeef\n")]:
            self.assertEqual(self.ci(bad)[0], 2)
    def test_welcome_hash_in_loader_must_match_pin(self):
        t = render(self.files); h = W.parse_pins(pins_for(self.files))["wallet-guardian-welcome"]
        i = t.index("SKILL.md\" " + h); t2 = t[:i] + "SKILL.md\" " + "e" * 64 + t[i + 10 + 64:]
        self.assertEqual(self.ci(t2)[0], 2)
    def test_paste_test_copy_fails(self): self.assertEqual(self.ci(R.paste_test(TEMPLATE_PATH))[0], 2)
    def test_draft_fails(self): self.assertEqual(self.ci(DRAFT)[0], 2)
    def test_other_commit_folder_fails(self):
        os.rename(self.D, os.path.join(self.F, "wg-install-abcdef01")); self.D = os.path.join(self.F, "wg-install-abcdef01")
        self.assertEqual(self.ci(render(self.files))[0], 2)

class Embedded(unittest.TestCase):
    def test_welcome_fence_is_tools_copy_and_build_up_to_date(self):
        m = B.FENCE.findall(WELCOME_D); self.assertEqual(len(m), 1); self.assertEqual(m[0][1], rd(os.path.join(HERE, "wg_skillcheck.py"), "r"))
        import hashlib; self.assertEqual(W.TEMPLATE_SHA, hashlib.sha256(B.template(DRAFT).encode()).hexdigest())
    def test_helper_holds_no_pins_and_no_network_or_writes(self):
        src = rd(os.path.join(HERE, "wg_skillcheck.py"), "r")
        self.assertEqual(re.findall(r"[0-9a-f]{64}", src), [W.TEMPLATE_SHA])
        for w in ("urllib", "socket", "http", "open(", "O_WRONLY", "O_CREAT", "rmtree", "remove(", "unlink", "mkdir", "rename"):
            self.assertNotIn(w, src.replace("os.open(", "").replace("https", ""), w)

if __name__ == "__main__": unittest.main(verbosity=2)

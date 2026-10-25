# Shared fixtures for the offline tests, repo layout (templates/grok-bot/wallet-guardian-share/tools). No network.
# v1.2 = `git show 8dbda8e1:<path>` (needs git and that commit); v1.3 = the committed skills/ files in this checkout.
# Scratch folders only under tools/.scratch (never /tmp), removed after.
import atexit, contextlib, hashlib, io, os, re, shutil, subprocess, sys, tempfile, textwrap
HERE = os.path.dirname(os.path.abspath(__file__)); SHARE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import wg_skillcheck as W, render_release as R, build_drafts as B
SCRATCH = os.path.join(HERE, ".scratch")
SHARE_PATH = "templates/grok-bot/wallet-guardian-share"
C12 = "8dbda8e1"  # the v1.2 commit (main before MR A)
FAKE = "f00dfeed" + "1" * 32  # stand-in for MR A's merge commit (not a real commit)
def rd(p, mode="rb"):
    with open(p, mode) as f: return f.read()
def wr(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb" if isinstance(data, bytes) else "w") as f: f.write(data)
def git(*a): return subprocess.run(["git"] + list(a), cwd=SHARE, capture_output=True, check=True).stdout
def at(commit, rel): return git("show", "%s:%s/%s" % (commit, SHARE_PATH, rel))
REPO = {n: at(C12, "skills/%s/SKILL.md" % n) for n in W.NAMES}
V12_INSTR = at(C12, "BOT-DESCRIPTION.txt").decode()
REAL_INSTALLED = {n: rd(os.path.join(HERE, "fixtures/installed-form-v1.2", n, "SKILL.md")) for n in W.NAMES}
TEMPLATE_PATH = os.path.join(HERE, "instructions-template.v1.3.txt")
DRAFT = rd(TEMPLATE_PATH, "r")  # the instructions template (placeholders; no DRAFT-MARKER line)
V13 = {n: rd(os.path.join(SHARE, "skills", n, "SKILL.md")) for n in W.NAMES}  # as committed
HELPER_PATH = os.path.join(SHARE, "skills/wallet-guardian-notify/wg_notify.py"); HELPER = rd(HELPER_PATH)
PIN = R.notify_pin(V13["wallet-guardian-notify"]); assert PIN, "committed notify SKILL.md has no single wg_notify.py pin"
NFAKE = PIN[0]  # MR A commit 1 (adds only wg_notify.py), read from the committed notify pin
# The notify source with its two pins put back as placeholders; tests check that render_release rebuilds the committed file.
NOTIFY_T = V13["wallet-guardian-notify"].decode().replace(PIN[0], R.NOTIFY_PH[0]).replace(PIN[1], R.NOTIFY_PH[1])
# Synthetic draft forms (one DRAFT-MARKER line at the r5 draft position) for the refusal tests; never written into the repo.
SYN = "DRAFT-MARKER: synthetic test marker; this copy is not a release file."
def with_marker(text, i): L = text.split("\n"); return "\n".join(L[:i] + [SYN] + L[i:])
RULES_D = with_marker(V13["wallet-guardian-rules"].decode(), 12)
WELCOME_D = with_marker(V13["wallet-guardian-welcome"].decode(), 12)
NOTIFY_D = with_marker(NOTIFY_T, 5)
os.makedirs(SCRATCH, exist_ok=True); _LIB = tempfile.mkdtemp(dir=SCRATCH)
NOTIFY_DRAFT = os.path.join(_LIB, "wallet-guardian-notify.draft.SKILL.md"); wr(NOTIFY_DRAFT, NOTIFY_D)
def _cleanup():
    shutil.rmtree(_LIB, ignore_errors=True)
    with contextlib.suppress(OSError): os.rmdir(SCRATCH)
atexit.register(_cleanup)
def pins_for(files): return "".join("%s  %s/SKILL.md\n" % (hashlib.sha256(files[n]).hexdigest(), n) for n in W.NAMES)
def installer_form(raw, n):
    # The installer's rewrite (description folded >- at width 80, blank lines after the frontmatter dropped).
    # Validated only against the six real v1.2 installed files (test_00).
    _, desc, body = W.strict_parse(raw, n)
    fold = textwrap.fill(desc, width=80, initial_indent="  ", subsequent_indent="  ", break_long_words=False, break_on_hyphens=False)
    return ("---\nname: %s\ndescription: >-\n%s\n---\n%s\n" % (n, fold, body)).encode()
def mkscratch():
    os.makedirs(SCRATCH, exist_ok=True); return tempfile.mkdtemp(dir=SCRATCH)
def write_set(root, files, helper=None):
    for n, b in files.items(): wr(os.path.join(root, n, "SKILL.md"), b)
    if helper is not None: wr(os.path.join(root, "wallet-guardian-notify", "wg_notify.py"), helper)
def make_D(parent, files, commit=FAKE, pins=None):
    d = os.path.join(parent, "wg-install-" + commit[:8]); os.mkdir(d, 0o700); write_set(d, files)
    wr(os.path.join(d, W.PINFILE), pins if pins is not None else pins_for(files)); return d
def run(cmd, *args, stdin=None, root=None, files=None):
    s = io.StringIO()
    with contextlib.redirect_stdout(s):
        rc = W.main(["wg", cmd] + list(args), pins_for(files or V13) if stdin is None else stdin, root or W.WORKFLOWS)
    out = s.getvalue(); return rc, out, out.rstrip("\n").split("\n")[-1]
def render(files, commit=FAKE):
    # In-memory release text for the fixture commit (never written into the repo).
    t = R.fill(B.template(DRAFT), commit, {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}); R.guard(t); return t

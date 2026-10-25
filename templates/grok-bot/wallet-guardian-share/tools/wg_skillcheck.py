#!/usr/bin/env python3
# Wallet Guardian R-19 skill check, v1.3. Runs only through the instructions' Step 4 loader, which checks the sha256
# of the downloaded wallet-guardian-welcome, reads it once, and runs this code from memory with python3 -I -B.
# No network. Never writes a file; never installs, edits, or deletes a skill.
# stdin: the six hash lines from the instructions (check-instructions: the whole instructions text, word for word).
# Output: first line "wg_skillcheck v1.3 <command>", last line "result: ...". Pass = exit 0 AND the exact pass line.
#   check-instructions D   the text equals the canonical v1.3 template (only commit and hashes filled in); then verify D
#   verify D               D's six files and its wg-pinned.sha256 match the stdin hash lines
#   compare D              verify, then classify the library: missing|same|differs|unknown|duplicate (before installing)
#   check-one D NAME       after installing NAME: exactly one copy, same as the verified download
#   check-installed D      all six same, each once; rules has its version, revision, and end lines; no DRAFT-MARKER
#   show-diff D NAME       diff of the installed copy against the verified download (control characters shown as \u)
import difflib, hashlib, os, re, stat, sys, unicodedata

VERSION = "wg_skillcheck v1.3"
TEMPLATE_SHA = "1364ad8f4ddc23411539391afc4f71d32318940334609b658e2b77dd633a65fc"  # sha256 of the canonical v1.3 instructions template (set at build time)
NAMES = ("wallet-guardian-rules", "wallet-guardian-welcome", "wallet-guardian-onchain-exit",
         "wallet-guardian-campaign-radar", "wallet-guardian-keys", "wallet-guardian-notify")
WORKFLOWS = "/home/box/agent-data/workflows"
SHARED_TMP = ("/tmp", "/var/tmp", "/dev/shm")  # only used to refuse such folders; nothing is ever written anywhere
PINFILE, MAX, HEAD = "wg-pinned.sha256", 1 << 20, 8192
RULES_LINE = ("Rules version: v1.2 (2026-10-18). This version includes the R-16 push-channel addition; "
              "wallet-guardian-notify checks for this line and that addition before it enables Telegram or ntfy.")
REVISION, END_LINE = "Rules revision: v1.3", "End of wallet-guardian-rules v1.3"
PIN_RE = re.compile(r"^([0-9a-f]{64})  (wallet-guardian-[a-z-]+)/SKILL\.md$")
NAME_LIKE = re.compile(r"""(?i)\s*["']?\s*name\s*["']?\s*:""")  # same as wallet-guardian-notify
PLAIN_NAME = re.compile(r"""^\s*(["']?)[A-Za-z0-9_.-]+\1\s*$""")
PATH_OK = re.compile(r"/[A-Za-z0-9._/-]+")
LOOKALIKE = str.maketrans({"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s",
                           "ԁ": "d", "ɡ": "g", "ӏ": "l", "ı": "i", "ο": "o", "α": "a", "ε": "e", "ι": "i", "κ": "k", "ν": "v",
                           "ρ": "p", "τ": "t", "υ": "u", "χ": "x", "ɑ": "a", "ԝ": "w", "ɩ": "i", "һ": "h", "_": "-"})

class Fail(Exception): pass

def parse_pins(text):
    pins, lines = {}, text.split("\n")
    if lines and lines[-1] == "": lines.pop()
    for l in lines:
        m = PIN_RE.match(l)
        if not m or m.group(2) not in NAMES or m.group(2) in pins: raise Fail("hash lines: bad line %r" % l[:90])
        pins[m.group(2)] = m.group(1)
    if set(pins) != set(NAMES): raise Fail("hash lines: need exactly the six names, got %d" % len(pins))
    return pins

def inside(path, roots):
    return any(path == r or path.startswith(r.rstrip("/") + "/") for r in (os.path.realpath(x) for x in roots))

def check_dir(d, commit8=None):
    if not PATH_OK.fullmatch(d) or "/../" in d + "/" or "/./" in d + "/" or "//" in d: raise Fail("folder path: only absolute [A-Za-z0-9._/-], no . or ..")
    base = os.path.basename(d.rstrip("/"))
    if not re.fullmatch(r"wg-install-[0-9a-f]{8}", base) or (commit8 and base != "wg-install-" + commit8): raise Fail("folder must be named wg-install-<commit8>")
    rp = os.path.realpath(d)
    if inside(rp, (WORKFLOWS,) + SHARED_TMP) or inside(os.path.abspath(d), (WORKFLOWS,) + SHARED_TMP): raise Fail("folder is under the skills library or a shared temp directory")
    if rp != os.path.abspath(d).rstrip("/"): raise Fail("folder path contains a symlink")
    try: st = os.lstat(d)
    except OSError as e: raise Fail("cannot open folder (%s)" % e.strerror)
    if not stat.S_ISDIR(st.st_mode): raise Fail("folder is not a directory")

def read_nofollow(dirfd, name, cap=MAX):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=dirfd)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode): raise Fail("%s is not a regular file" % name)
        data = b""
        while len(data) <= cap:
            c = os.read(fd, 65536)
            if not c: break
            data += c
        if len(data) > cap: raise Fail("%s is larger than the cap" % name)
        return data
    finally: os.close(fd)

def opendir(path, dir_fd=None): return os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=dir_fd)

def load(d, pins, commit8=None):
    # Verified downloads {name: bytes}. Trust comes from the stdin hash lines (the instructions), not from files in D.
    check_dir(d, commit8)
    try: dfd = opendir(d)
    except OSError as e: raise Fail("cannot open folder (%s)" % e.strerror)
    try:
        extra = sorted(set(os.listdir(dfd)) - set(NAMES) - {PINFILE})
        if extra: raise Fail("folder has unexpected entries: %s" % ", ".join(extra))
        try: disk = parse_pins(read_nofollow(dfd, PINFILE, 4096).decode("ascii"))
        except UnicodeDecodeError: raise Fail("wg-pinned.sha256 is not ASCII")
        if disk != pins: raise Fail("wg-pinned.sha256 differs from the instructions' hash lines")
        out = {}
        for n in NAMES:
            sfd = opendir(n, dfd)
            try:
                if os.listdir(sfd) != ["SKILL.md"]: raise Fail("%s/ must hold only SKILL.md" % n)
                data = read_nofollow(sfd, "SKILL.md")
            finally: os.close(sfd)
            if hashlib.sha256(data).hexdigest() != pins[n]: raise Fail("%s: sha256 mismatch" % n)
            out[n] = data
        return out
    except OSError as e: raise Fail("cannot read folder (%s)" % e.strerror)
    finally: os.close(dfd)

def norm_name(v):
    v = unicodedata.normalize("NFKC", v.strip())
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'": v = v[1:-1]
    v = "".join(c for c in v if unicodedata.category(c) not in ("Cf", "Cc")).strip()
    return v.casefold().translate(LOOKALIKE)

def lev(a, b):
    p = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        c = [i]
        for j, y in enumerate(b, 1): c.append(min(p[j] + 1, c[j - 1] + 1, p[j - 1] + (x != y)))
        p = c
    return p[-1]

def target_of(v):
    # The pinned name this value is or imitates: exact after normalising, a -N suffix, non-ASCII letters in ASCII
    # positions (skeleton), or edit distance <= 2. Else None.
    n = norm_name(v); n2 = re.sub(r"-\d+$", "", n)
    for t in NAMES:
        if t in (n, n2): return t
    for t in NAMES:
        if len(n) == len(t) and all(a == b or ord(a) > 127 for a, b in zip(n, t)): return t
    near = [t for t in NAMES if lev(n2, t) <= 2]
    return near[0] if len(near) == 1 else None

def strict_parse(raw, want):
    # Exact form only: UTF-8, no BOM, LF only, keys exactly name + description, name plain and exact.
    try: t = raw.decode("utf-8")
    except UnicodeDecodeError: return None
    if t.startswith("\ufeff") or "\r" in t: return None
    lines = t.split("\n")
    if lines[0] != "---" or "---" not in lines[1:]: return None
    end = lines.index("---", 1); fm = lines[1:end]
    name, desc, keys, i = None, None, [], 0
    while i < len(fm):
        k, sep, v = fm[i].partition(":")
        if not sep or k != k.strip() or not k: return None
        keys.append(k)
        if k == "name": name = v.strip()
        elif k == "description":
            v = v.strip()
            if v == ">-":
                parts = []
                while i + 1 < len(fm) and fm[i + 1].startswith("  "): i += 1; parts.append(fm[i].strip())
                desc = " ".join(parts)
            elif len(v) >= 2 and v[0] == v[-1] == '"' and '\\' not in v: desc = v[1:-1]
            else: return None
        i += 1
    if sorted(keys) != ["description", "name"] or name != want or not desc: return None
    return name, desc, "\n".join(lines[end + 1:]).strip("\n")

def scan(root):
    # ({name: [(slug, raw or None)]}, problems). Fail closed like notify: anything that cannot be read or parsed is a problem.
    hits, problems = {n: [] for n in NAMES}, []
    try: rfd = opendir(root)
    except OSError as e: return hits, ["cannot open the skills library (%s)" % e.strerror]
    try:
        for e in sorted(os.listdir(rfd)):
            slug_t = target_of(e)
            def bad(why):
                problems.append("%s: %s" % (e, why))
                if slug_t: hits[slug_t].append((e, None))
            try: st = os.stat(e, dir_fd=rfd, follow_symlinks=False)
            except OSError as x: bad("unreadable (%s)" % x.strerror); continue
            if stat.S_ISLNK(st.st_mode): bad("is a symlink"); continue
            if not stat.S_ISDIR(st.st_mode):
                if slug_t: bad("same name but not a directory")  # a regular file, FIFO, or other non-directory: it exists, never missing
                continue
            try:
                sfd = opendir(e, rfd)
                try:
                    try: fst = os.stat("SKILL.md", dir_fd=sfd, follow_symlinks=False)
                    except FileNotFoundError:
                        if slug_t: bad("no SKILL.md")
                        continue
                    if not stat.S_ISREG(fst.st_mode): raise Fail("SKILL.md is not a regular file")
                    raw = read_nofollow(sfd, "SKILL.md")
                finally: os.close(sfd)
            except (OSError, Fail) as x: bad("SKILL.md unreadable (%s)" % (getattr(x, "strerror", None) or x)); continue
            try: text = raw.decode("utf-8")
            except UnicodeDecodeError: bad("SKILL.md is not valid UTF-8"); continue
            lines = [l.rstrip("\r") for l in text[:HEAD].lstrip("\ufeff").split("\n")]
            fm_t = set()
            if lines[0] == "---":
                if "---" not in lines[1:]: bad("frontmatter not closed within 8 KiB"); continue
                odd = False
                for l in lines[1:lines.index("---", 1)]:
                    if NAME_LIKE.match(l):
                        v = l.split(":", 1)[1]
                        if not PLAIN_NAME.match(v): odd = True
                        t = target_of(v)
                        if t: fm_t.add(t)
                if odd:
                    problems.append("%s: name value is not a plain name (comment, escape, block, or tag)" % e)
                    for t in fm_t | ({slug_t} if slug_t else set()): hits[t].append((e, None))
                    continue
            elif text.lstrip("\ufeff").lstrip().startswith("---"): bad("malformed frontmatter start"); continue
            for t in fm_t | ({slug_t} if slug_t else set()): hits[t].append((e, raw))
    finally: os.close(rfd)
    return hits, problems

def classify(d, pins, root):
    ref = {n: strict_parse(b, n) for n, b in load(d, pins).items()}
    for n, r in ref.items():
        if r is None: raise Fail("%s download is not in the expected form" % n)
    hits, problems = scan(root)
    res = {}
    for n in NAMES:
        h = hits[n]
        if not h: res[n] = "missing"
        elif len(h) > 1: res[n] = "duplicate"
        else:
            p = strict_parse(h[0][1], n) if h[0][1] is not None else None
            res[n] = "unknown" if p is None else ("same" if p == ref[n] else "differs")
    return res, problems, hits, ref

def report(res, problems, ok):
    # "missing" (installable) is printed only when the whole compare passes; otherwise it is "blocked".
    for n in NAMES: print("%s %s" % ("blocked" if res[n] == "missing" and not ok else res[n], n))
    for p in problems: print("problem " + clean(p))

def clean(s):  # R-4: show control, zero-width, and bidi characters as escapes
    return "".join(c if unicodedata.category(c) not in ("Cc", "Cf", "Co", "Cs") or c == "\n" else "\\u%04x" % ord(c) for c in s)

def template_of(text):
    # -> (template text, commit). Undo only the commit and the six hash lines; everything else must be word for word.
    t = text.rstrip("\n") + "\n"
    urls = re.findall(r"/-/raw/([0-9a-f]{40})/templates/", t)
    if len(set(urls)) != 1: raise Fail("instructions: need exactly one pinned commit")
    c = urls[0]
    pins = [l for l in t.split("\n") if PIN_RE.match(l)]
    parse_pins("\n".join(pins))
    for l in pins:
        h, n = PIN_RE.match(l).groups()
        t = t.replace(h, "<SHA64-%s>" % n[len("wallet-guardian-"):])
    return t.replace(c, "<COMMIT40>").replace(c[:8], "<COMMIT8>"), c

def check_instructions(d, text):
    if re.search(r"(?m)^(DRAFT-MARKER|END WG-INSTRUCTIONS TEST)", text): raise Fail("instructions carry a draft or test marker")
    t, c = template_of(text)
    if hashlib.sha256(t.encode()).hexdigest() != TEMPLATE_SHA: raise Fail("instructions differ from the canonical v1.3 text")
    pins = parse_pins("\n".join(l for l in text.split("\n") if PIN_RE.match(l)))
    load(d, pins, c[:8])

def check_skill(name, raw, ref):
    p = strict_parse(raw, name)
    if p is None or p != ref: return False
    if re.search(rb"(?m)^DRAFT-MARKER", raw): return False
    if name == "wallet-guardian-rules":
        body = p[2].split("\n")
        if RULES_LINE not in body or REVISION not in body or body[-1] != END_LINE: return False
    return True

def run(cmd, args, stdin, root=WORKFLOWS):
    print("%s %s" % (VERSION, cmd))
    if cmd == "check-instructions" and len(args) == 1:
        check_instructions(args[0], stdin); return "result: instructions ok"
    pins = parse_pins(stdin)
    if cmd == "verify" and len(args) == 1:
        load(args[0], pins); return "result: all six verified"
    if cmd == "compare" and len(args) == 1:
        res, problems, _, _ = classify(args[0], pins, root)
        stop = [n for n in NAMES if res[n] in ("differs", "unknown", "duplicate")]
        report(res, problems, not stop and not problems)
        if stop or problems: raise Fail("stop and ask the owner about: " + ", ".join(stop + (["unreadable skills"] if problems else [])))
        return "result: install only: " + (", ".join(n for n in NAMES if res[n] == "missing") or "nothing")
    if cmd == "check-one" and len(args) == 2 and args[1] in NAMES:
        n = args[1]; res, problems, hits, ref = classify(args[0], pins, root)
        print("%s %s" % (res[n], n))
        if problems or res[n] != "same" or not check_skill(n, hits[n][0][1], ref[n]): raise Fail("%s is not installed exactly once and the same" % n)
        return "result: %s installed and same" % n
    if cmd == "check-installed" and len(args) == 1:
        res, problems, hits, ref = classify(args[0], pins, root); report(res, problems, False)
        if problems or any(res[n] != "same" or not check_skill(n, hits[n][0][1], ref[n]) for n in NAMES):
            raise Fail("not verified; do not use the failed skills, ask the owner")
        return "result: all six installed and same"
    if cmd == "show-diff" and len(args) == 2 and args[1] in NAMES:
        n = args[1]; new = strict_parse(load(args[0], pins)[n], n); hits, _ = scan(root)
        if len(hits[n]) != 1 or hits[n][0][1] is None: raise Fail("need exactly one readable installed copy, found %d" % len(hits[n]))
        old = strict_parse(hits[n][0][1], n)
        a = (["description: " + old[1]] + old[2].split("\n")) if old else hits[n][0][1].decode("utf-8", "replace").split("\n")
        b = ["description: " + new[1]] + new[2].split("\n")
        for l in difflib.unified_diff(a, b, "installed/" + n, "pinned/" + n, lineterm=""): print(clean(l))
        return "result: diff shown"
    raise Fail("usage: check-instructions|verify|compare|check-one|check-installed|show-diff D [NAME]")

def main(argv, stdin_text=None, root=WORKFLOWS):
    try:
        text = sys.stdin.read(65536) if stdin_text is None else stdin_text
        print(run(argv[1] if len(argv) > 1 else "", argv[2:], text, root)); return 0
    except Fail as e:
        print("FAIL " + clean(str(e))); print("result: FAILED; stop and ask the owner"); return 2
    except Exception as e:
        print("FAIL unexpected %s" % type(e).__name__); print("result: FAILED; stop and ask the owner"); return 2

if __name__ == "__main__": sys.exit(main(sys.argv))

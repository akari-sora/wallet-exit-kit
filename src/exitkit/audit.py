#!/usr/bin/env python3
"""Privacy check before sharing docs/skills (stdlib only, offline, read-only).

What it finds (each hit is PUBLIC / FAKE / REVIEW):
- EVM addresses: 40 hex with 0x, 0X or NO prefix; addresses glued to other hex or letters
  (e.g. "cafe0x<addr>", "wallet<addr>end"); 32-byte topic-padded addresses (24 leading zeros +
  address); addresses split across two lines.
- Boundary rule: an allowlisted / public / fake address only counts as such when no hex char is
  directly before (or before its 0x) or after it; otherwise the whole combined run is REVIEW.
- 64-hex strings (tx hash, private key, signature part): allowed only if in KNOWN_64 (public
  event topics / storage slots listed in references/07, and published release file hashes),
  an obvious placeholder, or a verified file hash in a SHA256SUMS file (see below).
- Other hex runs longer than 40 that are not 64: REVIEW (may hide an address).
- Non-EVM / identity formats: Bitcoin bech32 (bc1…), TRON (T…), base58 (Solana/BTC legacy),
  ENS names (*.eth), email, social handles (at-sign + name), home/internal paths. A short list of
  exact public strings (KNOWN_TEXT, PLATFORM_PATHS) is PUBLIC instead of REVIEW. In a file named
  SHA256SUMS, a 64-hex value is PUBLIC only when the file it lists (in the same folder or below,
  not a symlink, no path escape) really has that SHA-256.

Limits: heuristics only. It cannot recognise private labels, balances, people's names written
in prose, or screenshots. A PASS means "no pattern above was found", not "no private data".

  exitkit audit <folder> [--allow 0x...]... [--forbid SUBSTR]...
Exit code 1 for review findings, forbidden substrings, or unreadable/unfollowed paths;
exit code 2 if the input folder does not exist or is not a directory.
Every hex run of 64 or more characters is displayed as first 4 / last 4 plus length.

The walk skips __pycache__ and checkout tooling directories (.git, .venv, .omc,
caches, dist, build, *.egg-info). Files that are read use the same classification
rules as before.
"""
import argparse, hashlib, os, re, sys, tokenize

# Tooling and VCS trees are not project source. A checkout is scanned after
# `python3 -m venv .venv`, and local agent state may hold machine paths.
_SKIP_DIR_NAMES = {
    "__pycache__", ".git", ".venv", "venv", ".omc", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", ".eggs",
}


def _skip_dir(name):
    return name in _SKIP_DIR_NAMES or name.endswith(".egg-info")

PUBLIC = {
    "ca11bde05977b3631167028862be2a173976ca11": "Multicall3",
    "000000000022d473030f116ddee9f6b43ac78ba3": "Uniswap Permit2",
    "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee": "native-asset placeholder (eth_simulateV1 traceTransfers)",
    "0000000000000000000000000000000000000000": "zero address",
    "0000000000000000000000000000000000000001": "neutral reader / precompile 1",
    "000000000000000000000000000000000000dead": "burn address",
    "0776c06907ce6ff3d9dbf84ba9b3422d7225942d": "Penpie MasterPenpie (Arbitrum)",
    "6db96bbeb081d2a85e0954c252f2c1dc108b3f81": "Penpie PendleStaking (Arbitrum)",
    "c06a5d3014b9124bf215287980305af2f793eb30": "Penpie PendleMarketDepositHelper (Arbitrum)",
    "c61d3c70cfc9dedaa090fdd0760eb9291253feff": "Penpie vlPNP (Arbitrum)",
    "b688ba096b7bb75d7841e47163cd12d18b36a5bf": "Penpie mPENDLE (Arbitrum)",
    "e71ada7e035d24d1216fabcaff9d9095145d84bd": "Penpie mPENDLE SV (Arbitrum)",
    "2ac2b254bc18cd4999f64773a966e4f4869c34ee": "Penpie PNP (Arbitrum)",
    "4eee13b0fc9fa1a59ac3ea5f4900da3bbe31abf8": "Penpie PRT (Arbitrum)",
    "8ce523cf1120d9b7703806c745b69663a2847504": "Penpie penpieBribeRewardDistributor (Arbitrum)",
    "888888888889758f76e7103c6cbf23abbf58f946": "Pendle RouterV4",
    # not an address: the public wallet-exit-kit commit that wallet-guardian-notify v1.3 pins wg_notify.py to
    "fd94656c155aac652a35127cdf3bbe1d9781825e": "wallet-exit-kit commit (wallet-guardian-notify v1.3 wg_notify.py pin)",
}
KNOWN_64 = {  # public keccak constants (references/07) and published release file hashes
    "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef": "Transfer",
    "8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925": "Approval",
    "17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31": "ApprovalForAll",
    "c3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62": "TransferSingle",
    "4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb": "TransferBatch",
    "da9fa7c1b00402c17d0161b249b1ab8bbec047c5a52207b9c112deffd817036b": "Permit2 Approval",
    "c6a377bfc4eb120024a8ac08eef205be16b817020812c73223e81d1bdb9708ec": "Permit2 Permit",
    "89b1add15eff56b3dfe299ad94e01f2b52fbcb80ae1a3baea6ae8c04cb2b98a4": "Permit2 Lockdown",
    "da919360433220e13b51e8c211e490d148e61a3bd53de8c097194e458b97f3e1": "BorrowAllowanceDelegated",
    "dcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7": "ERC-4626 Deposit",
    "fbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db": "ERC-4626 Withdraw",
    "442e715f626346e8c54381002da614f62bee8d27386535b2521ec8540898556e": "Safe ExecutionSuccess",
    "bc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b": "Upgraded",
    # published release file hashes (gitlab.com/aa22396584/wallet-guardian/-/releases/v0.4.0-rc.5 SHA256SUMS)
    "655b601f14c422e7b5ad14b0a8200dde72c0dc1df1d32f0ec98eec48c9a829ef": "wallet-guardian 0.4.0rc5 wheel sha256",
    "06ae47cfca5995ad8847e8436435ba6ca0373b49f8f3af46dbc1224dbdfae80e": "wallet-guardian 0.4.0rc5 constraints.txt sha256",
    # gitlab.com/aa22396584/wallet-guardian/-/releases/v0.4.0-rc.6 SHA256SUMS (constraints.txt is unchanged from rc.5)
    "4dcced22d13a3f375c89e78ebfd1b1ac3e0aff71b4646aa510a074b63a2fb368": "wallet-guardian 0.4.0rc6 wheel sha256",
    "7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f": "AdminChanged",
    "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc": "EIP-1967 implementation slot",
    "b53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103": "EIP-1967 admin slot",
    "a3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50": "EIP-1967 beacon slot",
    # templates/grok-bot/wallet-guardian-share v1.3 (public pins, not secrets)
    "2c2b87bb267435d3c3c4e3ca9a1dff06aae6f38bd3285f62214d86096567ad78": "wallet-guardian-share wg_notify.py sha256 (notify pin)",
    "1364ad8f4ddc23411539391afc4f71d32318940334609b658e2b77dd633a65fc": "wallet-guardian-share v1.3 instructions template sha256 (TEMPLATE_SHA)",
}
HEX_RUN = re.compile(r"(0[xX])?([0-9a-fA-F]{20,})")
OTHER = [
    ("BTC bech32", re.compile(r"\bbc1[ac-hj-np-z02-9]{25,87}\b")),
    ("TRON", re.compile(r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b")),
    ("base58 (Solana/BTC)", re.compile(r"(?<![0-9A-Za-z])(?=[1-9A-HJ-NP-Za-km-z]*\d)(?=[1-9A-HJ-NP-Za-km-z]*[A-Z])"
                                       r"(?=[1-9A-HJ-NP-Za-km-z]*[a-z])[1-9A-HJ-NP-Za-km-z]{26,44}(?![0-9A-Za-z])")),
    ("ENS name", re.compile(r"\b[a-z0-9-]{3,}\.eth\b", re.I)),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("social handle", re.compile(r"(?<![\w.@/])" + "@" + r"[A-Za-z0-9_]{3,30}\b")),
    # personal profile URLs on social hosts (public org feeds on other hosts are not flagged)
    ("profile URL", re.compile(r"https?://(?:www\.)?(?:threads\.(?:net|com)|medium\.com|youtube\.com|tiktok\.com|"
                               r"mastodon\.social|warpcast\.com|farcaster\.xyz)/" + "@" + r"[A-Za-z0-9_.]{2,30}", re.I)),
    # patterns are split so this file does not match itself
    ("internal path", re.compile("(" + "/ho" + r"me/\w|/Us" + r"ers/\w|/work" + "space/|/ro" + "ot/|" + r"[A-Z]:\\Us" + r"ers\\)")),
]

# Exact public text that the identity patterns above would otherwise flag: (label, matched text) -> what it is.
# Matching is exact and case-sensitive, so a near miss (another handle, another .eth name) stays REVIEW.
KNOWN_TEXT = {
    ("social handle", "@" + "BotFather"): "Telegram's official bot-creation account",
    ("social handle", "@" + "username"): "generic placeholder",
    ("social handle", "@" + "handle"): "generic placeholder",
    ("social handle", "@" + "handles"): "generic placeholder",
    ("ENS name", "name" + ".eth"): "generic ENS example",
}
# Grok Bot keeps each account's skill library at this path; it is the same on every account, not a personal one.
PLATFORM_PATHS = ("/ho" + "me/box/agent-data/",)
NAME_CHAR = re.compile(r"[A-Za-z0-9_@-]")
PATH_TOKEN = re.compile(r"[^\s\"'`]+")


def _known_text(label, line, m):
    """KNOWN_TEXT entry for a match that is a whole token, else None.

    Nothing name-like may touch it on the left (a longer ENS name ending in the known one, a handle glued to
    a word), and on the right only sentence punctuation that is not followed by more name characters (a full
    stop at the end of a sentence is fine; a dot followed by another label is not).
    """
    known = KNOWN_TEXT.get((label, m.group(0)))
    if known is None:
        return None
    before = line[m.start() - 1] if m.start() > 0 else ""
    if before and (NAME_CHAR.match(before) or before in "./"):
        return None
    rest = line[m.end():]
    tail = rest.lstrip(".,;:!?)]}>/")
    if tail and NAME_CHAR.match(tail[0]) and len(tail) < len(rest):
        return None
    if rest and NAME_CHAR.match(rest[0]):
        return None
    return known


def _platform_path(line, start):
    """True when the whole path token starting here is under PLATFORM_PATHS with no "." or ".." segment."""
    token = PATH_TOKEN.match(line, start).group(0)   # untrimmed, so a final "." or ".." segment is still seen
    parts = token.split("/")
    return token.startswith(PLATFORM_PATHS) and ".." not in parts and "." not in parts


def _python_decorator_lines(rel, lines):
    """Line numbers where a real decorator starts, found with the tokenizer so strings and docstrings never count."""
    if not rel.endswith(".py"):
        return set()
    found, line_start = set(), True
    try:
        # Feed the same physical lines the scanner numbers, so line numbers always agree.
        feed = iter([ln + "\n" for ln in lines])
        for tok in tokenize.generate_tokens(lambda: next(feed, "")):
            if tok.type in (tokenize.NEWLINE, tokenize.NL):
                line_start = True
                continue
            if tok.type in (tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT):
                continue
            if line_start and tok.type == tokenize.OP and tok.string == "@":
                found.add(tok.start[0])
            line_start = False
    except (tokenize.TokenError, SyntaxError):
        return set()
    return found


def _is_python_decorator(decorator_lines, lineno, line, m):
    """A social-handle match that is the decorator token at the start of a decorator line."""
    return lineno in decorator_lines and not line[:m.start()].strip()


def is_fake(h):
    h = h.lower()
    for n in (1, 2, 4, 8):          # repeated short pattern: 1111…, abab…, abcd…, 12345678…
        if len(h) % n == 0 and h == h[:n] * (len(h) // n):
            return True
    return False


def classify40(h, allow):
    k = h.lower()
    if k in allow: return "PUBLIC: " + allow[k]
    if is_fake(k): return "FAKE"
    return "REVIEW"


HEXCH = set("0123456789abcdefABCDEF")


def _redact_long_hex(text):
    """Redact long hex at the output boundary, including glued and padded values."""
    def redact(match):
        run = match.group(2)
        if len(run) < 64:
            return match.group(0)
        return (match.group(1) or "") + run[:4] + "…" + run[-4:] + f" ({len(run)} hex)"

    return HEX_RUN.sub(redact, text)


def _report(text, *, file=None, end="\n"):
    print(_redact_long_hex(text), file=file, end=end)


class _AuditParser(argparse.ArgumentParser):
    def _print_message(self, message, file=None):
        if message:
            _report(message, file=file or sys.stderr, end="")


def _glued_before(line, p):
    """Hex glued in front of the run that starts at p (directly, or in front of its 0x/0X)."""
    q = p - 2 if p >= 2 and line[p - 2:p] in ("0x", "0X") else p
    k = q
    while k > 0 and line[k - 1] in HEXCH:
        k -= 1
    return line[k:q], q


SUMS_LINE = re.compile(r"^([0-9a-fA-F]{64}) [ *](\S.*)$")


def _verified_sums(folder, text):
    """Hashes in a SHA256SUMS file whose listed file (same folder or below, not a symlink) really has that SHA-256."""
    found = {}
    base = os.path.realpath(folder)
    for line in text.splitlines():
        m = SUMS_LINE.match(line)
        if not m:
            continue
        rel = m.group(2)
        target = os.path.join(folder, rel)
        real = os.path.realpath(target)
        if os.path.isabs(rel) or os.path.islink(target) or not real.startswith(base + os.sep):
            continue
        try:
            with open(real, "rb") as f:
                digest = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            continue
        if digest == m.group(1).lower():
            found[digest] = rel
    return found


def scan_hex(line, allow, file_hashes=None):
    """Yield (display, kind, note) for every address-like hex in one line.

    Boundary rule: a run counts as allowlisted / public / fake only when it is bounded by non-hex
    characters on both sides (an optional 0x/0X prefix is part of the token). Any extra hex glued
    before or after (even 1 char) makes the whole combined run REVIEW, so a private fragment cannot
    hide next to a known address.
    """
    for m in HEX_RUN.finditer(line):
        run = m.group(2)
        n = len(run)
        pre = m.group(1) or ""
        front, q = _glued_before(line, m.start(2))
        if front:
            combined = front + line[q:m.end(2)]
            yield combined, "REVIEW", f"hex glued before a {n}-hex run (boundary rule)"
            continue
        if n == 40:
            yield pre + run, classify40(run, allow), "bare 40-hex (no 0x)" if not pre else ""
        elif n == 64:
            k = run.lower()
            if k in KNOWN_64:
                yield pre + run, "PUBLIC: " + KNOWN_64[k], "64-hex constant"
            elif file_hashes and k in file_hashes:
                yield pre + run, "PUBLIC: sha256 of " + file_hashes[k], "verified file hash"
            elif k.startswith("0" * 24):
                inner = run[24:]
                yield pre + run, classify40(inner, allow), "32-byte topic-padded address"
            elif is_fake(k):
                yield pre + run, "FAKE", "64-hex placeholder"
            else:
                yield pre + run, "REVIEW", "64-hex (tx hash / key / signature?)"
        elif n > 40:
            if is_fake(run):     # the whole run is one repeated pattern (1111…), nothing hidden
                yield pre + (run if n >= 64 else run[:12] + "…"), "FAKE", f"{n}-hex placeholder"
            else:
                # boundary rule: no allowlist / fake credit for an address with hex glued on
                yield pre + run, "REVIEW", f"{n}-hex run glued to other hex (may hide an address)"
        elif 20 <= n < 40:
            continue   # handled by split-line pass


def main(argv=None):
    ap = _AuditParser(prog="exitkit audit")
    ap.add_argument("folder")
    ap.add_argument("--allow", action="append", default=[])
    ap.add_argument("--forbid", action="append", default=[])
    a = ap.parse_args(argv)
    if not os.path.isdir(a.folder):
        _report(f"ERROR: audit folder does not exist or is not a directory: {a.folder}")
        return 2
    allow = dict(PUBLIC)
    allow.update({x.lower().replace("0x", ""): "user allowlist" for x in a.allow})
    review, seen, forbidden, errors = [], {}, [], []

    def walk_error(error):
        path = error.filename or a.folder
        errors.append((os.path.relpath(path, a.folder), error))

    for root, dirs, files in os.walk(a.folder, onerror=walk_error):
        for d in dirs[:]:
            path = os.path.join(root, d)
            if os.path.islink(path):
                errors.append((os.path.relpath(path, a.folder), "symlinked directory not followed"))
                dirs.remove(d)
        dirs[:] = [d for d in dirs if not _skip_dir(d)]
        for fn in files:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, a.folder)
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except OSError as e:
                errors.append((rel, e))
                continue
            lines = text.splitlines()
            decorators = _python_decorator_lines(rel, lines)
            file_hashes = _verified_sums(root, text) if fn == "SHA256SUMS" else None
            hits = []
            for i, line in enumerate(lines, 1):
                for s in a.forbid:
                    if s.lower() in line.lower():
                        forbidden.append((rel, i, s))
                for disp, kind, note in scan_hex(line, allow, file_hashes):
                    hits.append((i, disp, kind, note))
                for label, rx in OTHER:
                    for m in rx.finditer(line):
                        if label == "social handle" and _is_python_decorator(decorators, i, line, m):
                            continue
                        known = _known_text(label, line, m)
                        if known is None and label == "internal path" and _platform_path(line, m.start()):
                            known = "Grok Bot platform skill folder (same on every account)"
                        hits.append((i, m.group(0), "PUBLIC: " + known if known else "REVIEW", label))
            # split-across-lines pass: a line ending in a 20-39 hex run + next line starting with hex
            for i in range(len(lines) - 1):
                m1 = re.search(r"(?<![0-9a-fA-F])(?:0[xX])?([0-9a-fA-F]{8,39})\s*$", lines[i])
                m2 = re.match(r"^\s*(?!0[xX])([0-9a-fA-F]{1,40})(?![0-9a-fA-F])", lines[i + 1])
                if m1 and m2 and len(m1.group(1)) + len(m2.group(1)) == 40:
                    joined = m1.group(1) + m2.group(1)
                    hits.append((i + 1, "0x" + joined, classify40(joined, allow), "address split across lines"))
            for i, disp, kind, note in hits:
                key = (disp, kind, note)
                seen.setdefault(key, []).append(f"{rel}:{i}")
                if kind == "REVIEW":
                    review.append((rel, i, disp, note))
    for (disp, kind, note), locs in sorted(seen.items(), key=lambda x: (x[0][1], x[0][0])):
        _report(f"{kind:58s} {disp}  [{note}]  ({len(locs)}x: {', '.join(locs[:3])}{' …' if len(locs) > 3 else ''})")
    for rel, i, s in forbidden:
        _report(f"FORBIDDEN substring {s!r} at {rel}:{i}")
    for rel, error in errors:
        _report(f"ERROR: cannot read {rel}: {error}")
    ok = not review and not forbidden and not errors
    _report(f"RESULT: {'PASS' if ok else 'FAIL'}  unique_hits={len(seen)} review={len(review)} "
          f"forbidden_hits={len(forbidden)} read_errors={len(errors)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

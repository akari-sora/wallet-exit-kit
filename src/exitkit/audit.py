#!/usr/bin/env python3
"""Privacy check before sharing docs/skills (stdlib only, offline, read-only).

What it finds (each hit is PUBLIC / FAKE / REVIEW):
- EVM addresses: 40 hex with 0x, 0X or NO prefix; addresses glued to other hex or letters
  (e.g. "cafe0x<addr>", "wallet<addr>end"); 32-byte topic-padded addresses (24 leading zeros +
  address); addresses split across two lines.
- Boundary rule: an allowlisted / public / fake address only counts as such when no hex char is
  directly before (or before its 0x) or after it; otherwise the whole combined run is REVIEW.
- 64-hex strings (tx hash, private key, signature part): allowed only if in KNOWN_64 (public
  event topics / storage slots listed in references/07) or an obvious placeholder.
- Other hex runs longer than 40 that are not 64: REVIEW (may hide an address).
- Non-EVM / identity formats: Bitcoin bech32 (bc1…), TRON (T…), base58 (Solana/BTC legacy),
  ENS names (*.eth), email, social handles (at-sign + name), home/internal paths.

Limits: heuristics only. It cannot recognise private labels, balances, people's names written
in prose, or screenshots. A PASS means "no pattern above was found", not "no private data".

  exitkit audit <folder> [--allow 0x...]... [--forbid SUBSTR]...
Exit code 1 if anything needs review or a forbidden substring is found.

The walk skips __pycache__ and checkout tooling directories (.git, .venv, .omc,
caches, dist, build, *.egg-info). Files that are read use the same classification
rules as before.
"""
import argparse, os, re, sys

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
}
KNOWN_64 = {  # public keccak constants (references/07)
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
    "7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f": "AdminChanged",
    "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc": "EIP-1967 implementation slot",
    "b53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103": "EIP-1967 admin slot",
    "a3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50": "EIP-1967 beacon slot",
}
HEX_RUN = re.compile(r"(0[xX])?([0-9a-fA-F]{20,})")
OTHER = [
    ("BTC bech32", re.compile(r"\bbc1[ac-hj-np-z02-9]{25,87}\b")),
    ("TRON", re.compile(r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b")),
    ("base58 (Solana/BTC)", re.compile(r"(?<![0-9A-Za-z])(?=[1-9A-HJ-NP-Za-km-z]*\d)(?=[1-9A-HJ-NP-Za-km-z]*[A-Z])"
                                       r"(?=[1-9A-HJ-NP-Za-km-z]*[a-z])[1-9A-HJ-NP-Za-km-z]{26,44}(?![0-9A-Za-z])")),
    ("ENS name", re.compile(r"\b[a-z0-9-]{3,}\.eth\b", re.I)),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("social handle", re.compile(r"(?<![\w.@/])" + "@" + r"[A-Za-z0-9_]{3,15}\b")),
    # patterns are split so this file does not match itself
    ("internal path", re.compile("(" + "/ho" + r"me/\w|/Us" + r"ers/\w|/work" + "space/|/ro" + "ot/|" + r"[A-Z]:\\Us" + r"ers\\)")),
]


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


def _glued_before(line, p):
    """Hex glued in front of the run that starts at p (directly, or in front of its 0x/0X)."""
    q = p - 2 if p >= 2 and line[p - 2:p] in ("0x", "0X") else p
    k = q
    while k > 0 and line[k - 1] in HEXCH:
        k -= 1
    return line[k:q], q


def scan_hex(line, allow):
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
                yield pre + run[:10] + "…", "PUBLIC: " + KNOWN_64[k], "64-hex constant"
            elif k.startswith("0" * 24):
                inner = run[24:]
                yield pre + run, classify40(inner, allow), "32-byte topic-padded address"
            elif is_fake(k):
                yield pre + run[:10] + "…", "FAKE", "64-hex placeholder"
            else:
                yield pre + run, "REVIEW", "64-hex (tx hash / key / signature?)"
        elif n > 40:
            if is_fake(run):     # the whole run is one repeated pattern (1111…), nothing hidden
                yield pre + run[:12] + "…", "FAKE", f"{n}-hex placeholder"
            else:
                # boundary rule: no allowlist / fake credit for an address with hex glued on
                yield pre + run, "REVIEW", f"{n}-hex run glued to other hex (may hide an address)"
        elif 20 <= n < 40:
            continue   # handled by split-line pass


def main(argv=None):
    ap = argparse.ArgumentParser(prog="exitkit audit")
    ap.add_argument("folder")
    ap.add_argument("--allow", action="append", default=[])
    ap.add_argument("--forbid", action="append", default=[])
    a = ap.parse_args(argv)
    allow = dict(PUBLIC)
    allow.update({x.lower().replace("0x", ""): "user allowlist" for x in a.allow})
    review, seen, forbidden = [], {}, []
    for root, dirs, files in os.walk(a.folder):
        dirs[:] = [d for d in dirs if not _skip_dir(d)]
        for fn in files:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, a.folder)
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            lines = text.splitlines()
            hits = []
            for i, line in enumerate(lines, 1):
                for s in a.forbid:
                    if s.lower() in line.lower():
                        forbidden.append((rel, i, s))
                for disp, kind, note in scan_hex(line, allow):
                    hits.append((i, disp, kind, note))
                for label, rx in OTHER:
                    for m in rx.finditer(line):
                        hits.append((i, m.group(0), "REVIEW", label))
            # split-across-lines pass: a line ending in a 20-39 hex run + next line starting with hex
            for i in range(len(lines) - 1):
                m1 = re.search(r"(?:0[xX])?([0-9a-fA-F]{8,39})\s*$", lines[i])
                m2 = re.match(r"^\s*([0-9a-fA-F]{1,40})", lines[i + 1])
                if m1 and m2 and len(m1.group(1)) + len(m2.group(1)) == 40:
                    joined = m1.group(1) + m2.group(1)
                    hits.append((i + 1, "0x" + joined, classify40(joined, allow), "address split across lines"))
            for i, disp, kind, note in hits:
                key = (disp, kind, note)
                seen.setdefault(key, []).append(f"{rel}:{i}")
                if kind == "REVIEW":
                    review.append((rel, i, disp, note))
    for (disp, kind, note), locs in sorted(seen.items(), key=lambda x: (x[0][1], x[0][0])):
        print(f"{kind:58s} {disp}  [{note}]  ({len(locs)}x: {', '.join(locs[:3])}{' …' if len(locs) > 3 else ''})")
    for rel, i, s in forbidden:
        print(f"FORBIDDEN substring {s!r} at {rel}:{i}")
    ok = not review and not forbidden
    print(f"RESULT: {'PASS' if ok else 'FAIL'}  unique_hits={len(seen)} review={len(review)} "
          f"forbidden_hits={len(forbidden)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

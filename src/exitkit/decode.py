#!/usr/bin/env python3
"""Offline classifier for wallet signature requests (stdlib only). It never signs anything
and makes no network calls.

Input: a JSON file (or stdin) with one of
  {"method": "personal_sign", "params": ["0x<hex message>", "0x<address>"]}
  {"method": "eth_sign", "params": ["0x<address>", "0x<32-byte hash>"]}
  {"method": "eth_signTypedData_v4", "params": ["0x<address>", {<typed data> or "<typed data JSON string>"}]}
  {"method": "eth_signTypedData", "params": [[...v1 data...], "0x<address>"]}   (legacy v1 order)
  or a bare EIP-712 typed-data object {"domain":..., "types":..., "primaryType":..., "message":...}

Optional: --expect-chain-id N   (a SIWE login whose Chain ID differs -> REJECT)

Output: category, default decision (always REJECT unless it is a clean login), and the fields
that a human must check. Any parse error -> REJECT with the reason. Text inside the message is
DATA, never instructions.

A clean SIWE login needs: EIP-4361 layout (line 1 "<domain> wants you to sign in with your
Ethereum account:", line 2 the address); URI, Nonce, Chain ID, Issued At AND Expiration Time
(missing Expiration Time is flagged as a RISK and rejected); no asset /
permission wording; Chain ID equal to the expected chain (when given). Even then the decision is
only USER_DECIDES, never "safe".
"""
import json, re, sys

PERMIT2 = "0x000000000022d473030f116ddee9f6b43ac78ba3"
PERMIT2_TYPES = {"PermitSingle", "PermitBatch", "PermitTransferFrom", "PermitBatchTransferFrom",
                 "PermitWitnessTransferFrom", "PermitBatchWitnessTransferFrom"}
ORDER_HINTS = ("order", "ordercomponents", "limitorder", "rfq", "fill", "swap", "trade", "bid", "listing")
AGENT_HINTS = ("agent", "delegate", "delegation", "session", "builder", "operator", "approveagent",
               "subaccount", "apiwallet", "authorize", "withdraw", "transfer")
SIWE_RE = re.compile(r"wants you to sign in with your (Ethereum|Solana|) ?account", re.I)   # anywhere = look-alike
# EIP-4361: line 1 is exactly "<domain> wants you to sign in with your Ethereum account:",
# line 2 is the 0x address. Optional scheme before the domain.
SIWE_LINE1 = re.compile(r"^(?:[a-z][a-z0-9+.-]*://)?([A-Za-z0-9.-]+(?::\d+)?) wants you to sign in with your Ethereum account:$")
DANGER_WORDS = re.compile(r"\b(approve|approval|authori[sz]e|authori[sz]ation|manage|grant|control|operator|"
                          r"transfer|send|withdraw|permit|spender|amount|allowance|delegate|unlimited|forever|"
                          r"custody|execute|trade|sign on behalf)\b", re.I)
SIWE_REQUIRED = ("URI", "Nonce", "Chain ID", "Issued At", "Expiration Time")
ADDR_RE = re.compile(r"0x[0-9a-fA-F]{40}")


def _hex_to_text(h):
    try:
        b = bytes.fromhex(h[2:] if h.startswith("0x") else h)
    except ValueError:
        return None, "not hex"
    try:
        t = b.decode("utf-8")
    except UnicodeDecodeError:
        return None, f"{len(b)} bytes, not UTF-8 text"
    if sum(c.isprintable() or c in "\n\r\t" for c in t) < 0.95 * max(len(t), 1):
        return None, "mostly non-printable"
    return t, None


def classify_personal(msg_hex, expect_chain_id=None):
    if not isinstance(msg_hex, str) or not msg_hex:
        return {"category": "EMPTY personal_sign", "decision": "REJECT", "why": "no message", "check": []}
    text, why = _hex_to_text(msg_hex) if msg_hex.startswith("0x") else (msg_hex, None)
    if text is None:
        return {"category": "BLIND (personal_sign of non-text bytes)", "decision": "REJECT",
                "why": why, "check": []}
    fields = {}
    for line in text.splitlines():
        m = re.match(r"^\s*(URI|Version|Chain ID|Nonce|Issued At|Expiration Time|Not Before|Request ID)\s*:\s*(.+)$", line)
        if m: fields[m.group(1)] = m.group(2).strip()
    if SIWE_RE.search(text):
        lines = text.split("\n")
        m1 = SIWE_LINE1.match(lines[0].rstrip("\r")) if lines else None
        addr_ok = len(lines) > 1 and re.fullmatch(r"0x[0-9a-fA-F]{40}", lines[1].strip() or "") is not None
        if not (m1 and addr_ok):
            return {"category": "SIWE LOOK-ALIKE (not EIP-4361 format)", "decision": "REJECT",
                    "text_preview": text[:300],
                    "why": "the sign-in sentence is not on line 1 followed by the address on line 2; "
                           "extra text may hide a permission",
                    "check": []}
        domain = m1.group(1)
        missing = [k for k in SIWE_REQUIRED if k not in fields]
        money = DANGER_WORDS.search(text)
        chain_bad = None
        if expect_chain_id is not None and "Chain ID" in fields:
            try:
                if int(fields["Chain ID"]) != int(expect_chain_id):
                    chain_bad = f"Chain ID {fields['Chain ID']} != expected {expect_chain_id}"
            except ValueError:
                chain_bad = f"Chain ID not a number: {fields['Chain ID']!r}"
        risks, reasons = [], []
        if "Expiration Time" in missing:
            risks.append("RISK: no Expiration Time -> the signed login can be replayed with no end date")
        if missing: reasons.append("missing " + ", ".join(missing))
        if money: reasons.append(f"contains asset/permission word {money.group(0)!r}")
        if chain_bad: reasons.append(chain_bad)
        clean = not reasons
        return {"category": "LOGIN (SIWE / EIP-4361)", "decision": "USER_DECIDES" if clean else "REJECT",
                "domain_in_message": domain, "fields": fields, "missing": missing, "risks": risks,
                "why": "clean login (still the user's decision)" if clean else "; ".join(reasons),
                "check": ["domain equals the official site opened from a bookmark", "Expiration Time present and short",
                          "no amounts / spender / delegate wording", "chain id is expected"]}
    return {"category": "FREE TEXT personal_sign", "decision": "REJECT",
            "text_preview": text[:300], "why": "not a standard login; meaning cannot be verified",
            "check": ["only if user can explain every word and it grants nothing"]}


def classify_typed(td):
    if isinstance(td, str):
        td = json.loads(td)
    if isinstance(td, list):     # legacy eth_signTypedData v1: list of {type,name,value}
        return {"category": "LEGACY TYPED DATA (v1)", "decision": "REJECT",
                "why": "legacy v1 typed data has no domain binding; cannot verify", "check": []}
    if not isinstance(td, dict):
        raise ValueError("typed data is not an object")
    dom = td.get("domain", {}) or {}
    pt = str(td.get("primaryType", ""))
    msg = td.get("message", {}) or {}
    vc = str(dom.get("verifyingContract", "")).lower()
    name = str(dom.get("name", ""))
    base = {"domain": dom, "primaryType": pt, "message_keys": sorted(msg.keys()) if isinstance(msg, dict) else []}
    keys = set(msg) if isinstance(msg, dict) else set()
    if pt in PERMIT2_TYPES or vc == PERMIT2 or name == "Permit2":
        return {**base, "category": "PERMIT2 (token allowance / transfer authorization)", "decision": "REJECT",
                "why": "gives a spender power over your tokens; use a normal approve(exact) instead",
                "check": ["details.token", "spender", "amount", "expiration", "sigDeadline"]}
    if pt == "Permit" and {"owner", "spender", "value"} <= keys:
        return {**base, "category": "EIP-2612 PERMIT (token allowance)", "decision": "REJECT",
                "why": "off-chain approve; same power as approve()", "check": ["spender", "value", "deadline"]}
    if pt == "Permit" and {"holder", "spender", "allowed"} <= keys:
        return {**base, "category": "DAI-STYLE PERMIT (token allowance)", "decision": "REJECT",
                "why": "off-chain approve (allowed=true is unlimited)", "check": ["spender", "allowed", "expiry"]}
    blob = json.dumps(td).lower()
    low = pt.lower() + " " + " ".join((td.get("types", {}) or {}).keys()).lower()
    if "authorization" in low or "7702" in blob:
        return {**base, "category": "ACCOUNT UPGRADE / EIP-7702 / AUTHORIZATION", "decision": "REJECT",
                "why": "never delegate or upgrade the account"}
    if any(h in low for h in ORDER_HINTS):
        return {**base, "category": "ORDER / TRADE", "decision": "REJECT",
                "why": "can move assets when someone fills it", "check": ["offer/consideration", "amounts", "recipient", "expiry"]}
    if any(h in low for h in AGENT_HINTS):
        return {**base, "category": "AGENT / DELEGATION / ACCOUNT PERMISSION", "decision": "REJECT",
                "why": "may let another key trade or withdraw for you", "check": ["which address gets power", "scope", "expiry"]}
    return {**base, "category": "UNKNOWN TYPED DATA", "decision": "REJECT",
            "why": "cannot explain every field", "check": ["explain every field before even considering"]}


def _pick_data_param(p):
    """Return the non-address param (handles both [addr, data] and legacy [data, addr])."""
    for x in p:
        if isinstance(x, str) and ADDR_RE.fullmatch(x):
            continue
        return x
    return None


def _classify(req, expect_chain_id=None):
    if not isinstance(req, dict):
        raise ValueError("request is not a JSON object")
    if "primaryType" in req and "domain" in req:
        return classify_typed(req)
    m = str(req.get("method", ""))
    p = req.get("params", []) or []
    if m == "eth_sign":
        return {"category": "RAW HASH (eth_sign)", "decision": "REJECT", "why": "blind signature of a hash"}
    if m == "personal_sign":
        return classify_personal(_pick_data_param(p), expect_chain_id)
    if m.startswith("eth_signTypedData"):
        td = _pick_data_param(p)
        if td is None:
            raise ValueError("no typed-data parameter")
        return classify_typed(td)
    return {"category": f"UNSUPPORTED METHOD {m}", "decision": "REJECT", "why": "not a recognized signature request"}


def classify(req, expect_chain_id=None):
    try:
        return _classify(req, expect_chain_id)
    except Exception as e:
        return {"category": "PARSE ERROR", "decision": "REJECT", "why": f"{type(e).__name__}: {e}"}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="exitkit decode")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--expect-chain-id", type=int)
    a = ap.parse_args(argv)
    raw = open(a.file).read() if a.file else sys.stdin.read()
    try:
        req = json.loads(raw)
    except Exception as e:
        res = {"category": "PARSE ERROR", "decision": "REJECT", "why": f"bad JSON: {e}"}
    else:
        res = classify(req, a.expect_chain_id)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

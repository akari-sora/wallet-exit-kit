#!/usr/bin/env python3
"""Read-only JSON-RPC helper (Python stdlib only).

- METHOD ALLOWLIST (deny by default): only the read methods in READ_METHODS are sent. Names are
  type-checked, non-ASCII is rejected, then NFKC + strip + casefold; only the canonical spelling
  is sent. Every entry of every batch is checked, and _post() (the single transport choke point)
  re-checks the body, so private helpers cannot bypass it.
  Anything else (eth_send*, eth_sign*, personal_*, wallet_*, mev_*, flashbots_*, hardhat_*,
  anvil_*, evm_*, engine_*, debug_*, ...) is refused locally before any network call.
- HOST PREFERENCE (configurable, separate from the method allowlist): allowed_hosts=None means
  any host the caller passes (user preference "allow third-party", the default);
  allowed_hosts=[...] restricts requests to those hosts (user preference "RPC + official only").
- chainId verification is MANDATORY: expect_chain_id must be given (no opt-out). Every URL is
  checked with eth_chainId before its first use (primary AND fallback); a mismatching URL is
  refused and logged, never used.
- Every result records WHICH host answered. Fallback is explicit (allow_fallback=True) and reported.
- A failed / missing read is UNKNOWN, never 0.
- disclosure() lists every host contacted, which methods were sent, and the KIND of data each
  request carried, classified from the actual payload: 完整錢包地址 / 只有合約或其他地址 /
  只有區塊號或無地址. Wallets are recognised from register_wallets(...) (module-wide) or
  RPC(..., wallets=[...]); with no wallet registered, any address counts as "可能含錢包地址".
  Use disclosure_log.py to merge this with requests made outside the scripts and to render the
  report section 「這次把地址送到哪些服務」.

Example (fake address; <RPC_URL> is a placeholder you must fill in):
    from exitkit.rpc import RPC, enc, UNKNOWN
    r = RPC(["<RPC_URL>"], label="eth", expect_chain_id=1)
    blk = r.block_number()
    owner = "0x1111111111111111111111111111111111111111"
    res = r.batch([("eth_getBalance", [owner, hex(blk)]),
                   ("eth_getTransactionCount", [owner, hex(blk)])])
    print(res.values, res.rpc_used, r.disclosure())
"""
import json, random, re, time, unicodedata, urllib.request, urllib.error
from urllib.parse import urlparse

# Deny by default: only these read methods may leave the machine.
READ_METHODS = frozenset({
    "eth_chainId", "eth_blockNumber", "eth_getBalance", "eth_getCode", "eth_getStorageAt",
    "eth_getTransactionCount", "eth_call", "eth_getLogs", "eth_getBlockByNumber",
    "eth_getTransactionReceipt", "eth_getTransactionByHash", "eth_gasPrice", "eth_feeHistory",
    "eth_estimateGas", "eth_simulateV1",
})

DEFAULT_UA = "Mozilla/5.0 (compatible)"   # generic UA; does not name this tool

# ---------- what kind of data a request discloses ----------
KIND_WALLET = "完整錢包地址"
KIND_CONTRACT = "只有合約或其他地址（不含已登錄錢包）"
KIND_BLOCK = "只有區塊號或無地址"
KIND_UNREG = "可能含錢包地址（沒有登錄錢包，無法判斷）"
_KIND_RANK = {KIND_BLOCK: 0, KIND_CONTRACT: 1, KIND_UNREG: 2, KIND_WALLET: 3}
_WALLETS = set()
_ADDR_ANY = None


def register_wallets(*addrs):
    """Register the user's own wallet addresses (module-wide) so disclosure() can tell
    "full wallet address" apart from "contract address only"."""
    for a in addrs:
        if isinstance(a, (list, tuple, set)):
            register_wallets(*a); continue
        h = str(a).lower().replace("0x", "")
        if len(h) != 40 or any(c not in "0123456789abcdef" for c in h):
            raise ValueError(f"not an EVM address: {a!r}")
        _WALLETS.add(h)


def classify_payload(params, wallets=()):
    """Kind of data in one request's params (wallet seen also inside calldata / padded topics)."""
    import re
    global _ADDR_ANY
    if _ADDR_ANY is None:
        _ADDR_ANY = re.compile(r"0x[0-9a-f]{40}(?![0-9a-f])|0{24}[0-9a-f]{40}")
    blob = json.dumps(params).lower()
    ws = _WALLETS | {w.lower().replace("0x", "") for w in wallets}
    if any(w in blob for w in ws):
        return KIND_WALLET
    if _ADDR_ANY.search(blob):
        return KIND_CONTRACT if ws else KIND_UNREG
    return KIND_BLOCK



class Unknown:
    """Sentinel for a failed read. Never equal to 0, never falsy-by-accident in reports."""
    def __repr__(self): return "UNKNOWN"
    def __str__(self): return "未知（讀取失敗）"
    def __bool__(self): raise ValueError("UNKNOWN has no truth value; handle it explicitly")


UNKNOWN = Unknown()


class RPCError(Exception):
    def __init__(self, message, http_status=None):
        super().__init__(message)
        self.http_status = http_status


class BatchResult:
    def __init__(self, values, rpc_used, block=None):
        self.values = values          # list of (ok: bool, value_or_error)
        self.rpc_used = rpc_used      # "label (host)"
        self.block = block


def _host(url):
    return urlparse(url).netloc or url


_CANON = {m.casefold(): m for m in READ_METHODS}


def check_method(method):
    """Return the canonical allowlisted method name, or raise RPCError("refused: ...").
    Steps: type check -> reject any non-ASCII character (full-width, Cyrillic look-alikes,
    zero-width space, BOM ...) -> NFKC -> strip -> casefold -> exact lookup in the allowlist.
    Only the canonical spelling is ever sent."""
    if not isinstance(method, str):
        raise RPCError(f"refused: method must be a string, got {type(method).__name__}")
    if not method.isascii():
        raise RPCError(f"refused: method {method!r} contains non-ASCII characters")
    norm = unicodedata.normalize("NFKC", method).strip().casefold()
    canon = _CANON.get(norm)
    if canon is None:
        raise RPCError(f"refused: {method!r} is not on the read-only method allowlist")
    return canon


def _smuggled(x, depth=0):
    """True if params contain something shaped like a nested JSON-RPC request.

    Nested keys are compared case-insensitively. ``Method`` is the same shape as ``method``.
    """
    if depth > 8:
        return True
    if isinstance(x, dict):
        for key in x:
            folded = key.casefold() if isinstance(key, str) else None
            if folded in {"method", "jsonrpc"}:
                return True
        return any(_smuggled(v, depth + 1) for v in x.values())
    if isinstance(x, (list, tuple)):
        return any(_smuggled(v, depth + 1) for v in x)
    return False


def _no_dup_keys(pairs):
    """Reject keys that collide under case-insensitive comparison.

    Go's encoding/json (geth and clients built on it) matches object keys
    case-insensitively and keeps the last one. ``method`` and ``METHOD``
    are one key there.
    """
    folded = []
    for key, _value in pairs:
        if not isinstance(key, str):
            raise RPCError("refused: duplicate keys in JSON payload")
        folded.append(key.casefold())
    if len(folded) != len(set(folded)):
        raise RPCError("refused: duplicate keys in JSON payload")
    return dict(pairs)


def check_url(url):
    """Refuse URLs that try to name a JSON-RPC method in the query / fragment."""
    from urllib.parse import parse_qs
    u = urlparse(url)
    keys = {k.strip().casefold() for k in parse_qs(u.query, keep_blank_values=True)}
    if "method" in keys or "method=" in (u.fragment or "").casefold():
        raise RPCError(f"refused: RPC URL {u.netloc} carries a 'method' parameter")


_REQUEST_KEYS = frozenset({"jsonrpc", "id", "method", "params"})


def check_body(body):
    """Check EVERY JSON-RPC entry (single or batch) right before it leaves the machine.

    The method must already be in canonical allowlisted spelling. Each object's
    keys must be a subset of jsonrpc, id, method, and params, spelled exactly
    like that, and jsonrpc must be the string "2.0". A key that differs only
    by case (METHOD, Method, PARAMS) is not one of those names.
    """
    entries = body if isinstance(body, list) else [body]
    if not entries:
        raise RPCError("refused: empty batch")
    for e in entries:
        if not isinstance(e, dict):
            raise RPCError("refused: batch entry is not an object")
        if not set(e).issubset(_REQUEST_KEYS):
            raise RPCError("refused: unexpected JSON-RPC keys")
        if e.get("jsonrpc") != "2.0":
            raise RPCError('refused: jsonrpc must be "2.0"')
        m = e.get("method")
        if check_method(m) != m:
            raise RPCError(f"refused: method {m!r} not in canonical allowlisted spelling")
        if _smuggled(e.get("params", [])):
            raise RPCError("refused: params contain a nested JSON-RPC request shape")


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse 301/302/303/307/308. Following one would skip allowed_hosts and chainId."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RPCError(f"refused: HTTP redirect ({code})")

    def _refuse(self, req, fp, code, msg, headers):
        raise RPCError(f"refused: HTTP redirect ({code})")

    http_error_301 = http_error_302 = http_error_303 = http_error_307 = http_error_308 = _refuse


_OPENER = urllib.request.build_opener(_RefuseRedirect)


class RPC:
    def __init__(self, urls, label=None, expect_chain_id=None, timeout=20, retries=4,
                 allow_fallback=False, user_agent=DEFAULT_UA, allowed_hosts=None, max_total_secs=120,
                 wallets=()):
        if isinstance(urls, str):
            urls = [urls]
        if not urls:
            raise RPCError("no RPC URL given (there is no built-in default)")
        self.urls = list(urls)
        self.label = label
        self.timeout = timeout
        self.retries = retries            # max retries per request (429 / 5xx / timeout)
        self.max_total_secs = max_total_secs  # wall-clock cap per request incl. backoff
        self.allow_fallback = allow_fallback
        self.ua = user_agent
        self.expect_chain_id = expect_chain_id
        self.allowed_hosts = None if allowed_hosts is None else {h.lower() for h in allowed_hosts}
        self._id = 0
        self._verified = {}           # url -> True / error string
        if expect_chain_id is None:
            raise RPCError("expect_chain_id is mandatory: every RPC URL must be checked with eth_chainId")
        self.wallets = {str(w).lower().replace("0x", "") for w in wallets}
        self.log = []                 # (host, method(s), outcome) for the report
        self.sent = []                # (host, method, kind) per request entry, from the real payload
        if self.allowed_hosts is not None:
            for u in self.urls:
                if _host(u).lower() not in self.allowed_hosts:
                    raise RPCError(f"host {_host(u)} not allowed by user preference (allowed_hosts)")
        self._verify(self.urls[0], hard=True)

    # ---------- transport ----------
    def _check(self, method):          # kept for callers/tests that use the old name
        return check_method(method)

    def _post(self, url, body):
        """THE single network choke point. Serialize first, then parse the exact bytes that would be
        sent and check every request (and every entry of a batch) against the allowlist. Method
        labels for the log / disclosure() come from that parsed payload, never from caller args."""
        try:
            data = json.dumps(body).encode()
            sent = json.loads(data.decode())
        except (TypeError, ValueError) as e:
            raise RPCError(f"refused: payload is not serializable JSON: {e}")
        check_body(sent)
        check_url(url)
        if self.allowed_hosts is not None and _host(url).lower() not in self.allowed_hosts:
            raise RPCError(f"refused: host {_host(url)} not allowed by user preference (allowed_hosts)")
        ents = sent if isinstance(sent, list) else [sent]
        methods = sorted({e["method"] for e in ents})
        for e in ents:   # recorded before sending: a failed request may still have reached the host
            self.sent.append((_host(url), e["method"], classify_payload(e.get("params", []), self.wallets)))
        try:
            out = self._transport(url, data)
        except RPCError as e:
            self.log.append((_host(url), methods, f"fail {e}"))
            raise
        self.log.append((_host(url), methods, "ok"))
        return out

    def _transport(self, url, data):
        """Raw HTTP with retries. Only called by _post(); re-checks the raw bytes anyway, so calling it
        directly cannot bypass the allowlist either."""
        try:
            check_body(json.loads(bytes(data).decode(), object_pairs_hook=_no_dup_keys))
        except RPCError:
            raise
        except Exception as e:
            raise RPCError(f"refused: raw payload is not valid JSON-RPC: {e}")
        check_url(url)
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json", "User-Agent": self.ua})
        delay = 1.0
        last = None
        last_http_status = None
        deadline = time.monotonic() + self.max_total_secs
        for attempt in range(self.retries + 1):
            try:
                with _OPENER.open(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode())
            except RPCError:
                raise
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code}"
                last_http_status = e.code
                if e.code not in (429, 500, 502, 503, 504):
                    break
            except Exception as e:   # timeout, connection reset, bad JSON
                last = f"{type(e).__name__}: {e}"
                last_http_status = None
            if attempt < self.retries:
                pause = delay + random.uniform(0, delay / 2)
                if time.monotonic() + pause >= deadline:
                    last = f"{last}; gave up: total time cap {self.max_total_secs}s"
                    break
                time.sleep(pause)
                delay *= 2
        raise RPCError(f"{_host(url)}: {last}", http_status=last_http_status)

    def _verify(self, url, hard=False):
        """eth_chainId check before first use of a URL; result cached."""
        if url in self._verified:
            if self._verified[url] is True:
                return True
            if hard:
                raise RPCError(self._verified[url])
            return False
        try:
            out = self._post(url, {"jsonrpc": "2.0", "id": 0, "method": "eth_chainId", "params": []})
            got = int(out["result"], 16)
            if got != self.expect_chain_id:
                err = f"chainId mismatch: expected {self.expect_chain_id}, got {got} from {_host(url)}"
            else:
                err = None
        except Exception as e:
            err = f"chainId check failed for {_host(url)}: {e}"
        if err is not None:
            self.log.append((_host(url), ["eth_chainId"], f"REFUSED {err}"))
        self._verified[url] = True if err is None else err
        if err and hard:
            raise RPCError(err)
        return err is None

    def _send(self, body, *_ignored):
        """Try primary; only try others if allow_fallback. Returns (json, url_used).
        Any extra caller argument is ignored; checking and logging happen inside _post()."""
        check_body(body)
        urls = self.urls if self.allow_fallback else self.urls[:1]
        errs = []
        http_statuses = []
        for u in urls:
            if not self._verify(u):
                errs.append(f"{_host(u)}: {self._verified[u]}")
                continue
            try:
                return self._post(u, body), u
            except RPCError as e:
                if str(e).startswith("refused"):
                    raise
                errs.append(str(e))
                http_statuses.append(e.http_status)
        http_status = (http_statuses[0] if http_statuses and len(http_statuses) == len(errs)
                       and len(set(http_statuses)) == 1 else None)
        raise RPCError("all RPCs failed (tried " + ", ".join(_host(u) for u in urls) + "): " + " | ".join(errs),
                       http_status=http_status)

    def used_label(self, url):
        return f"{self.label or 'rpc'} ({_host(url)})"

    def tried_label(self):
        urls = self.urls if self.allow_fallback else self.urls[:1]
        return f"{self.label or 'rpc'} (failed; tried {', '.join(_host(u) for u in urls)})"

    def disclosure(self):
        """{host: {"methods": [...], "sent": [kinds...], "strongest": kind, "chain_id_verified": bool}}
        for every host a request was sent to (incl. failures). Built only from real payloads."""
        d = {}
        for host, method, kind in self.sent:
            e = d.setdefault(host, {"methods": set(), "sent": set()})
            e["methods"].add(method); e["sent"].add(kind)
        out = {}
        for host, e in d.items():
            ver = any(_host(u) == host and v is True for u, v in self._verified.items())
            kinds = sorted(e["sent"], key=lambda k: -_KIND_RANK[k])
            out[host] = {"methods": sorted(e["methods"]), "sent": kinds, "strongest": kinds[0],
                         "chain_id_verified": ver}
        return out

    # ---------- API ----------
    def call(self, method, params):
        method = check_method(method)
        self._id += 1
        out, _ = self._send({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params})
        if "error" in out:
            raise RPCError(f"{method}: {out['error']}")
        return out["result"]

    def call_labeled(self, method, params):
        """Returns (ok, value, rpc_used). Failure -> (False, error string, label with hosts tried)."""
        method = check_method(method)
        self._id += 1
        try:
            out, u = self._send({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params})
        except RPCError as e:
            return False, str(e), self.tried_label()
        if "error" in out:
            return False, out["error"], self.used_label(u)
        return True, out["result"], self.used_label(u)

    def batch(self, calls, max_batch=50):
        """calls: list of (method, params). Returns BatchResult; failed items are (False, err)."""
        calls = [(check_method(m), p) for m, p in calls]   # every entry checked before anything is sent
        values, used = [], set()
        for i in range(0, len(calls), max_batch):
            chunk = calls[i:i + max_batch]
            body, ids = [], []
            for m, p in chunk:
                self._id += 1
                ids.append(self._id)
                body.append({"jsonrpc": "2.0", "id": self._id, "method": m, "params": p})
            try:
                out, u = self._send(body)
                used.add(self.used_label(u))
                if isinstance(out, dict):     # node rejected the whole batch
                    values += [(False, out.get("error", out))] * len(chunk)
                    continue
                by_id = {o.get("id"): o for o in out}
                for k in ids:
                    o = by_id.get(k)
                    if o is None:
                        values.append((False, "missing in batch response"))
                    elif "error" in o:
                        values.append((False, o["error"]))
                    else:
                        values.append((True, o["result"]))
            except RPCError as e:
                err = ({"http_status": e.http_status, "message": str(e)}
                       if e.http_status is not None else str(e))
                values += [(False, err)] * len(chunk)
                used.add(self.tried_label())
        return BatchResult(values, ", ".join(sorted(used)) or "none")

    def block_number(self):
        return int(self.call("eth_blockNumber", []), 16)

    def block(self, number):
        return self.call("eth_getBlockByNumber", [hex(number), False])


# ---------- ABI helpers (minimal) ----------
def pad32(x):
    if isinstance(x, int):
        return hex(x)[2:].rjust(64, "0")
    return x.lower().replace("0x", "").rjust(64, "0")


def enc(selector, *args):
    """Static args only (address / uint). selector like '0x70a08231'."""
    return selector + "".join(pad32(a) for a in args)


def dec_uint(h):
    if h in (None, "0x", "") or h is UNKNOWN:
        return UNKNOWN
    return int(h, 16)


def dec_addr(h):
    return "0x" + h[-40:]


def topic_addr(addr):
    if not isinstance(addr, str) or re.fullmatch(r"0x[0-9a-fA-F]{40}", addr) is None:
        raise ValueError("address must be exactly 20 bytes of hex (0x + 40 hex characters)")
    return "0x" + pad32(addr)


MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"


def encode_aggregate3(calls):
    """calls: list of (target, allow_failure, calldata_hex). Returns calldata for aggregate3."""
    sel = "82ad56cb"
    n = len(calls)
    heads, tails, offset = [], [], 32 * n
    for target, allow, data in calls:
        b = bytes.fromhex(data[2:] if data.startswith("0x") else data)
        padded = b + b"\x00" * ((32 - len(b) % 32) % 32)
        tup = pad32(target) + pad32(1 if allow else 0) + pad32(96) + pad32(len(b)) + padded.hex()
        heads.append(pad32(offset))
        tails.append(tup)
        offset += len(tup) // 2
    return "0x" + sel + pad32(32) + pad32(n) + "".join(heads) + "".join(tails)


def decode_aggregate3(ret_hex):
    """Returns list of (success: bool, returnData_hex). Empty / malformed input -> []."""
    if not isinstance(ret_hex, str) or len(ret_hex) < 2 + 128:
        return []
    try:
        b = bytes.fromhex(ret_hex[2:])
        w = lambda o: int.from_bytes(b[o:o + 32], "big")
        base = w(0)
        n = w(base)
        out = []
        for i in range(n):
            off = base + 32 + w(base + 32 + 32 * i)
            ok = bool(w(off))
            doff = off + w(off + 32)
            ln = w(doff)
            out.append((ok, "0x" + b[doff + 32: doff + 32 + ln].hex()))
        return out
    except (ValueError, IndexError):
        return []


def multicall_read(rpc, calls, block, check_deployed=True):
    """Same-block reads via Multicall3 aggregate3(allowFailure=true).
    calls: list of (target, calldata). Returns (list of value_hex|UNKNOWN, rpc_used, note).
    Multicall3 not deployed, empty return, or a result count != len(calls) -> every item UNKNOWN."""
    n = len(calls)
    if check_deployed:
        ok, code, used = rpc.call_labeled("eth_getCode", [MULTICALL3, hex(block)])
        if not ok or code in (None, "0x", ""):
            return [UNKNOWN] * n, used, "Multicall3 not deployed / code unreadable -> all UNKNOWN"
    data = encode_aggregate3([(t, True, d) for t, d in calls])
    ok, val, used = rpc.call_labeled("eth_call", [{"to": MULTICALL3, "data": data}, hex(block)])
    if not ok:
        return [UNKNOWN] * n, used, f"eth_call failed: {val}"
    dec = decode_aggregate3(val)
    if len(dec) != n:
        return [UNKNOWN] * n, used, f"result count {len(dec)} != {n} -> all UNKNOWN"
    return [r if s and r != "0x" else UNKNOWN for s, r in dec], used, "ok"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="exitkit rpc", description="demo read with a FAKE address")
    ap.add_argument("--rpc", required=True, help="RPC URL (required; no built-in default)")
    ap.add_argument("--chain-id", type=int, required=True)
    a = ap.parse_args(argv)
    fake = "0x1111111111111111111111111111111111111111"
    r = RPC([a.rpc], label="demo", expect_chain_id=a.chain_id, wallets=[fake])
    blk = r.block_number()
    vals, used, note = multicall_read(r, [(MULTICALL3, enc("0x4d2301cc", fake)),
                                          (MULTICALL3, "0x42cbb15c")], blk)
    print(json.dumps({"rpc": used, "block": blk, "note": note,
                      "fake_eth_balance": str(dec_uint(vals[0])),
                      "multicall_block": str(dec_uint(vals[1])),
                      "address_sent_to": r.disclosure()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

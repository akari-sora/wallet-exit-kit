#!/usr/bin/env python3
"""Chunked eth_getLogs with adaptive splitting and a coverage report (stdlib only, read-only).

- Splits [from, to] into chunks; on "range too large / too many results / limit" errors
  the chunk is halved and retried (down to min_chunk).
- Chunks that still fail are listed in `failed`; they are NOT treated as "no events".
- Structured HTTP or JSON-RPC 429 and explicit rate-limit phrases (including retry instructions)
  keep the same range. Otherwise, range/result split hints take precedence over the ambiguous
  RPC code -32005. Generic "limit exceeded" is a split hint.
- Rate limits and timeouts are retried with backoff; exhausted retries are listed in `failed`.
- A chunk whose result count hits a common provider cap (1000 / 5000 / 10000 / 20000) is treated
  as possibly truncated: it is split and re-scanned; at min_chunk it is listed in `suspect`.
- coverage = scanned blocks / requested blocks (suspect chunks do not count as scanned).
- --out writes raw logs that CONTAIN the queried address (privacy data). Write only to a temp
  directory and delete it after use. An existing path is left alone unless --force.

CLI example (fake owner; <RPC_URL> is a placeholder; finds Approval events where topic1 = owner):
  exitkit logs --rpc <RPC_URL> --chain-id 1 \
      --topic0 0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925 \
      --topic1-addr 0x1111111111111111111111111111111111111111 \
      --from-block 26200000 --to-block latest --chunk 5000
"""
import argparse, json, os, re, sys, time
from exitkit.rpc import RPC, RPCError, topic_addr

SPLIT_HINTS = ("range", "too many results", "result limit", "results limit", "log limit", "exceed",
               "10000", "max results", "block range", "response size", "query returned more than")
RATE_LIMIT_CODES = (429, -32005)
RATE_LIMIT_MESSAGES = {
    "429 too many requests", "rate limit", "rate limit exceeded", "rate-limit exceeded",
    "ratelimit", "request rate exceeded", "too many requests", "throttled",
    "capacity exceeded", "quota exceeded",
    "rate limit reached", "project id request rate exceeded",
}
TIMEOUT_HINTS = ("timeout", "timed out")
TRUNCATION_CAPS = (1000, 5000, 10000, 20000)


def _message(value):
    if isinstance(value, dict):
        value = value.get("message", "")
    return " ".join(str(value).strip().lower().split())


def _is_rate_limited(value):
    if isinstance(value, dict) and (value.get("http_status") == 429 or value.get("code") == 429):
        return True
    message = _message(value)
    if message in RATE_LIMIT_MESSAGES:
        return True
    # Match affirmative phrases at the start, not incidental mentions of rate metadata.
    if any(re.match(re.escape(phrase) + r"\b", message)
           for phrase in RATE_LIMIT_MESSAGES - {"rate limit", "ratelimit"}):
        return True
    # Providers also use -32005 for oversized queries; split hints win over that code.
    if any(hint in message for hint in SPLIT_HINTS):
        return False
    return isinstance(value, dict) and value.get("code") in RATE_LIMIT_CODES


def _is_timeout(value):
    message = _message(value)
    return any(hint in message for hint in TIMEOUT_HINTS)


def _topic_address(value):
    try:
        topic_addr(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return value


def _positive_int(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def get_logs(rpc, from_block, to_block, address=None, topics=None, chunk=10_000, min_chunk=64,
             batch=5, progress=None, rate_retries=2, time_budget=600):
    """rate_retries: max extra attempts for a rate-limited / timed-out chunk (on top of the RPC client's own
    per-request retries). time_budget: total wall-clock seconds; when exceeded, every chunk not yet
    scanned is listed in `failed` as "time budget exceeded" (UNKNOWN, not empty)."""
    """Returns dict(logs, scanned=[(a,b)], failed=[(a,b,err)], suspect=[(a,b,count)], coverage, rpc_used)."""
    if chunk < 1:
        raise ValueError("chunk must be at least 1")
    if batch < 1:
        raise ValueError("batch must be at least 1")
    logs, scanned, failed, suspect = [], [], [], []
    used = set()
    queue = []
    a = from_block
    while a <= to_block:
        b = min(a + chunk - 1, to_block)
        queue.append((a, b))
        a = b + 1

    def flt(a, b):
        f = {"fromBlock": hex(a), "toBlock": hex(b)}
        if address: f["address"] = address
        if topics is not None: f["topics"] = topics
        return f

    tries = {}
    t_end = time.monotonic() + time_budget
    while queue:
        if time.monotonic() > t_end:
            failed += [(a, b, f"time budget {time_budget}s exceeded; not scanned") for a, b in queue]
            queue = []
            break
        group, queue = queue[:batch], queue[batch:]
        res = rpc.batch([("eth_getLogs", [flt(a, b)]) for a, b in group])
        used.add(res.rpc_used)
        for (a, b), (ok, val) in zip(group, res.values):
            if ok:
                if isinstance(val, list) and len(val) in TRUNCATION_CAPS:
                    if b > a and (b - a + 1) > min_chunk:
                        mid = (a + b) // 2
                        queue = [(a, mid), (mid + 1, b)] + queue
                    else:
                        suspect.append((a, b, len(val)))
                        logs.extend(val)
                    continue
                logs.extend(val)
                scanned.append((a, b))
                continue
            err = json.dumps(val) if not isinstance(val, str) else val
            low = err.lower()
            if _is_rate_limited(val) or _is_timeout(val):
                tries[(a, b)] = tries.get((a, b), 0) + 1
                if tries[(a, b)] <= rate_retries and time.monotonic() + 2 ** tries[(a, b)] < t_end:
                    time.sleep(2 ** tries[(a, b)])          # back off, same range, no split
                    queue.append((a, b))
                else:
                    failed.append((a, b, f"rate-limited/timeout after {tries[(a, b)]} tries: " + err[:160]))
            elif b > a and (b - a + 1) > min_chunk and any(h in low for h in SPLIT_HINTS):
                mid = (a + b) // 2
                queue = [(a, mid), (mid + 1, b)] + queue
            else:
                failed.append((a, b, err[:200]))
        if progress:
            progress(len(scanned), len(failed), len(queue))

    total = to_block - from_block + 1
    done = sum(b - a + 1 for a, b in scanned)
    # de-duplicate (a split retry never double-counts, but be safe)
    seen, uniq = set(), []
    for lg in logs:
        k = (lg.get("transactionHash"), lg.get("logIndex"))
        if k not in seen:
            seen.add(k); uniq.append(lg)
    uniq.sort(key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    complete = not failed and not suspect and done == total
    return {"logs": uniq, "scanned": merge(scanned), "failed": sorted(failed), "suspect": sorted(suspect),
            "complete": complete, "status": "COMPLETE" if complete else "INCOMPLETE",
            "coverage": done / total if total > 0 else 1.0, "rpc_used": ", ".join(sorted(used))}


def merge(ranges):
    out = []
    for a, b in sorted(ranges):
        if out and a <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="exitkit logs")
    ap.add_argument("--rpc", required=True, action="append", help="repeatable; fallback only with --allow-fallback")
    ap.add_argument("--allow-fallback", action="store_true")
    ap.add_argument("--chain-id", type=int, required=True, help="required: every RPC URL is checked with eth_chainId")
    ap.add_argument("--address")
    ap.add_argument("--topic0")
    ap.add_argument("--topic1-addr", type=_topic_address)
    ap.add_argument("--topic2-addr", type=_topic_address)
    ap.add_argument("--from-block", type=int, required=True)
    ap.add_argument("--to-block", default="latest")
    ap.add_argument("--chunk", type=_positive_int, default=10_000)
    ap.add_argument("--batch", type=_positive_int, default=5, help="getLogs per HTTP batch; use 1 if the node rejects batches")
    ap.add_argument("--retries", type=int, default=3, help="max retries per HTTP request (429/5xx/timeout)")
    ap.add_argument("--timeout", type=float, default=20, help="seconds per HTTP request")
    ap.add_argument("--rate-retries", type=int, default=2, help="max extra tries for a rate-limited / timed-out range")
    ap.add_argument("--time-budget", type=float, default=600, help="total seconds for the whole scan")
    ap.add_argument("--allowed-host", action="append", help="user preference 'RPC + official only': restrict hosts")
    ap.add_argument("--out", help="WRITES raw logs incl. the queried address (privacy data); use a temp dir, delete after")
    ap.add_argument("--force", action="store_true", help="overwrite an existing --out file")
    a = ap.parse_args(argv)
    if a.out and os.path.lexists(a.out) and not a.force:
        print(f"refusing to overwrite {a.out}; pass --force", file=sys.stderr)
        return 2
    rpc = RPC(a.rpc, label="logs", expect_chain_id=a.chain_id, allow_fallback=a.allow_fallback,
              allowed_hosts=a.allowed_host, retries=a.retries, timeout=a.timeout,
              max_total_secs=min(a.time_budget, 120), wallets=[x for x in (a.topic1_addr, a.topic2_addr) if x])
    try:
        to = rpc.block_number() if a.to_block == "latest" else int(a.to_block)
    except RPCError as e:
        print(json.dumps({"status": "INCOMPLETE", "log_count": "UNKNOWN", "error": str(e),
                          "address_sent_to": rpc.disclosure()}, ensure_ascii=False, indent=1))
        return 2
    topics = [a.topic0, topic_addr(a.topic1_addr) if a.topic1_addr else None,
              topic_addr(a.topic2_addr) if a.topic2_addr else None]
    while topics and topics[-1] is None:
        topics.pop()
    r = get_logs(rpc, a.from_block, to, address=a.address, topics=topics or None, chunk=a.chunk, batch=a.batch,
                 rate_retries=a.rate_retries, time_budget=a.time_budget)
    summary = {"status": r["status"], "rpc_used": r["rpc_used"], "range": [a.from_block, to],
               "coverage_pct": round(100 * r["coverage"], 3), "scanned": r["scanned"],
               "failed": r["failed"], "suspect": r["suspect"], "address_sent_to": rpc.disclosure()}
    if r["complete"]:
        summary["log_count"] = len(r["logs"])
    else:
        summary["log_count"] = "UNKNOWN"
        summary["logs_found_in_scanned_ranges"] = len(r["logs"])
        summary["note"] = ("未知：有區段沒掃到（failed）或可能被截斷（suspect），"
                           "那些區段的事件數是未知，不是 0。")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(r, f)
        print(f"WARNING: wrote raw logs containing the queried address to {a.out}; delete it after use",
              file=sys.stderr)
    return 0 if r["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""eth_simulateV1 wrapper with appended reads and an assertion list (stdlib only, read-only).

Nothing is signed or sent: eth_simulateV1 executes the calls on a node's copy of the state.

Usage as a library (all addresses below are fake):
    from exitkit.rpc import RPC, enc
    from exitkit.simulate import simulate, check
    rpc = RPC(["<RPC_URL>"], label="arb", expect_chain_id=42161)
    OWNER   = "0x1111111111111111111111111111111111111111"
    TOKEN   = "0x2222222222222222222222222222222222222222"
    SPENDER = "0x3333333333333333333333333333333333333333"
    sim = simulate(rpc, OWNER,
        txs=[{"to": TOKEN, "data": enc("0x095ea7b3", SPENDER, 0)}],          # approve(spender, 0)
        reads=[{"name": "allowance_after", "to": TOKEN, "data": enc("0xdd62ed3e", OWNER, SPENDER), "after_tx": 0},
               {"name": "balance_after",   "to": TOKEN, "data": enc("0x70a08231", OWNER), "after_tx": 0}],
        pre_reads=[{"name": "balance_before", "to": TOKEN, "data": enc("0x70a08231", OWNER)}])
    report = check(sim, [
        {"type": "status", "tx": 0, "equals": 1},
        {"type": "log_count", "tx": 0, "equals": 1, "exclude_native": True},
        {"type": "log", "tx": 0, "index": 0, "emitter": TOKEN, "topic0": APPROVAL,
         "topic_addrs": {1: OWNER, 2: SPENDER}, "data_uint": 0},
        {"type": "read", "name": "allowance_after", "equals": 0},
        {"type": "read_same", "a": "balance_before", "b": "balance_after"},
        {"type": "native_only_gas_and_value"},
        {"type": "no_unexpected_addresses", "allow": [OWNER, TOKEN, SPENDER]},
        {"type": "no_new_nonzero_approval", "owner": OWNER},
    ])
    print(report["pass"], report["results"])

Rules: zero assertions -> FAIL. Every tx must carry a "status" assertion, and the list must contain
"native_only_gas_and_value" and "no_new_nonzero_approval"; otherwise -> FAIL (missing required).
A missing status / gasUsed / log data from the node is UNKNOWN and any assertion that needs it FAILs.
If the node returns fewer / more blocks or call results than requested, the simulation is
incomplete: sim["ok"] is False and check() FAILs (never PASS). spec.chain_id is required.

CLI: exitkit simulate spec.json   (spec = {"rpc": [...], "chain_id": n, "owner": ..., "txs": [...],
                                       "reads": [...], "pre_reads": [...], "assertions": [...]})
"""
import argparse, json, sys
from exitkit.rpc import RPC, RPCError, UNKNOWN, Unknown, enc, MULTICALL3

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
APPROVAL = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
APPROVAL_FOR_ALL = "0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31"
PERMIT2_APPROVAL = "0xda9fa7c1b00402c17d0161b249b1ab8bbec047c5a52207b9c112deffd817036b"
PERMIT2_PERMIT = "0xc6a377bfc4eb120024a8ac08eef205be16b817020812c73223e81d1bdb9708ec"
BORROW_ALLOWANCE_DELEGATED = "0xda919360433220e13b51e8c211e490d148e61a3bd53de8c097194e458b97f3e1"
TRANSFER_SINGLE = "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62"
TRANSFER_BATCH = "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb"
REQUIRED_GLOBAL = ("native_only_gas_and_value", "no_new_nonzero_approval")
NATIVE_PSEUDO = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"   # traceTransfers native-transfer emitter
READER = "0x0000000000000000000000000000000000000001"


def _lc(a): return a.lower() if isinstance(a, str) else a
def _taddr(t): return "0x" + t[-40:].lower()


def _hexint(v):
    """Hex string -> int; missing / empty -> UNKNOWN (never 0)."""
    if v is None or v in ("", "0x") or isinstance(v, Unknown):
        return UNKNOWN
    return int(v, 16)


def _word(data, i):
    """i-th 32-byte word of log data -> int; missing -> UNKNOWN."""
    if not isinstance(data, str) or len(data) < 2 + 64 * (i + 1):
        return UNKNOWN
    return int(data[2 + 64 * i: 2 + 64 * (i + 1)], 16)


def simulate(rpc, owner, txs, reads=(), pre_reads=(), state_overrides=None, base_block=None,
             gas_price=None, block_time_step=12, gas=None):
    """txs: [{"to","data","value"(int, optional)}]; one simulated block per tx (latest+1, +2, ...).
    reads: appended eth_call-style calls placed right after tx `after_tx` in the same block.
    pre_reads: read at base_block before anything runs.
    Returns dict with per-tx results, reads, native deltas, and metadata (rpc, blocks, gasPrice)."""
    if hasattr(rpc, "wallets"):                 # the owner is the user's wallet -> disclosure kind
        rpc.wallets.add(_lc(owner).replace("0x", ""))
    base = base_block if base_block is not None else rpc.block_number()
    blk = rpc.block(base)
    base_time = int(blk["timestamp"], 16)
    gp = gas_price if gas_price is not None else int(rpc.call("eth_gasPrice", []), 16)

    pre = {}
    for r in pre_reads:
        ok, val, _ = rpc.call_labeled("eth_call", [{"to": r["to"], "data": r["data"]}, hex(base)])
        pre[r["name"]] = int(val, 16) if ok and val not in ("0x", "") else UNKNOWN
    ok, bal, _ = rpc.call_labeled("eth_getBalance", [owner, hex(base)])
    native_before = int(bal, 16) if ok else UNKNOWN
    ov = {_lc(k): v for k, v in (state_overrides or {}).items()}.get(_lc(owner), {})
    if "balance" in ov:                       # the simulation starts from the overridden balance
        native_before = _hexint(ov["balance"]) if isinstance(ov["balance"], str) else int(ov["balance"])
    # owner code: a contract / EIP-7702-delegated owner can move value beyond the declared tx.value
    okc, code, _ = rpc.call_labeled("eth_getCode", [owner, hex(base)])
    owner_code = ov.get("code") if "code" in ov else (code if okc else UNKNOWN)
    if owner_code is UNKNOWN:
        owner_kind = "UNKNOWN (eth_getCode failed)"
    elif owner_code in (None, "", "0x"):
        owner_kind = "EOA"
    elif str(owner_code).lower().startswith("0xef0100") and len(owner_code) == 2 + 46:
        owner_kind = "EIP-7702 delegated -> 0x" + owner_code[8:]
    else:
        owner_kind = "CONTRACT (has code)"

    blocks, layout = [], []
    for i, tx in enumerate(txs):
        call = {"from": owner, "to": tx["to"], "data": tx.get("data", "0x"),
                "value": hex(tx.get("value", 0)), "gasPrice": hex(gp)}
        if gas or tx.get("gas"):
            call["gas"] = hex(tx.get("gas") or gas)
        calls, names = [call], [("tx", i)]
        for r in reads:
            if r.get("after_tx", len(txs) - 1) == i:
                calls.append({"from": READER, "to": r["to"], "data": r["data"]})
                names.append(("read", r["name"]))
        calls.append({"from": READER, "to": MULTICALL3, "data": enc("0x4d2301cc", owner)})
        names.append(("native_after", i))
        bsc = {"blockOverrides": {"number": hex(base + i + 1), "time": hex(base_time + block_time_step * (i + 1))},
               "calls": calls}
        if i == 0 and state_overrides:
            bsc["stateOverrides"] = state_overrides
        blocks.append(bsc)
        layout.append(names)

    payload = {"blockStateCalls": blocks, "validation": False, "traceTransfers": True,
               "returnFullTransactions": False}
    ok, res, used = rpc.call_labeled("eth_simulateV1", [payload, hex(base)])
    out = {"rpc_used": used, "base_block": base, "gas_price": gp, "owner": _lc(owner),
           "pre": pre, "native_before": native_before, "ok": ok, "txs": [], "reads": {},
           "native_after": [], "overrides_used": bool(state_overrides), "owner_kind": owner_kind,
           "expected_txs": len(txs), "expected_blocks": len(layout)}
    if not ok:
        out["error"] = res
        return out
    # The node must return exactly one block per requested block and one result per call;
    # anything shorter (or longer) means part of the sequence was not simulated -> not a PASS.
    if not isinstance(res, list) or len(res) != len(layout):
        out["ok"] = False
        out["error"] = (f"incomplete simulation: node returned {len(res) if isinstance(res, list) else 'non-list'} "
                        f"blocks, expected {len(layout)}")
        return out
    for bi, (b, names) in enumerate(zip(res, layout)):
        got = len(b.get("calls", []) or []) if isinstance(b, dict) else -1
        if got != len(names):
            out["ok"] = False
            out["error"] = f"incomplete simulation: block {bi} returned {got} call results, expected {len(names)}"
            return out
    for b, names in zip(res, layout):
        for c, (kind, key) in zip(b["calls"], names):
            st = _hexint(c.get("status"))
            if kind == "tx":
                out["txs"].append({"index": key, "block": int(b["number"], 16), "status": st,
                                   "gasUsed": _hexint(c.get("gasUsed")), "logs": c.get("logs", []),
                                   "error": c.get("error"), "returnData": c.get("returnData"),
                                   "value": txs[key].get("value", 0)})
            elif kind == "read":
                rd = c.get("returnData", "0x")
                out["reads"][key] = int(rd, 16) if (st is not UNKNOWN and st == 1) and rd not in (None, "0x", "") else UNKNOWN
            else:
                rd = c.get("returnData", "0x")
                out["native_after"].append(int(rd, 16) if (st is not UNKNOWN and st == 1) and rd not in (None, "0x", "") else UNKNOWN)
    return out


def _native_flows(sim, tx):
    o = sim["owner"]; out_ = in_ = 0
    for lg in tx["logs"]:
        if _lc(lg["address"]) == NATIVE_PSEUDO and lg["topics"][0] == TRANSFER:
            amt = _hexint(lg.get("data"))
            if amt is UNKNOWN:
                raise ValueError("native transfer log without data -> UNKNOWN")
            if _taddr(lg["topics"][1]) == o: out_ += amt
            if _taddr(lg["topics"][2]) == o: in_ += amt
    return out_, in_


def check(sim, assertions):
    """Each assertion -> (name, pass: bool, detail). A missing / UNKNOWN value is a FAIL."""
    results = []
    def add(a, ok, detail): results.append({"assertion": a, "pass": bool(ok), "detail": detail})
    if not sim.get("ok"):
        add({"type": "simulate"}, False, f"eth_simulateV1 failed: {sim.get('error')}")
        return {"pass": False, "results": results, "rpc_used": sim.get("rpc_used")}
    if not assertions:
        add({"type": "required"}, False, "zero assertions: a simulation without assertions is never PASS")
    if not sim.get("txs"):
        add({"type": "required"}, False, "no simulated tx")
    exp = sim.get("expected_txs")
    if exp is None or len(sim.get("txs", [])) != exp:
        add({"type": "required", "missing": "tx count"}, False,
            f"simulated tx results {len(sim.get('txs', []))} != requested {exp} -> UNKNOWN, not PASS")
    types = [a.get("type") for a in assertions]
    for req in REQUIRED_GLOBAL:
        if req not in types:
            add({"type": "required", "missing": req}, False, f"missing required assertion {req}")
    status_txs = {a.get("tx") for a in assertions if a.get("type") == "status"}
    for i in range(len(sim.get("txs", []))):
        if i not in status_txs:
            add({"type": "required", "missing": f"status tx {i}"}, False, f"missing required status assertion for tx {i}")
    for a in assertions:
        t = a["type"]
        try:
            if t == "status":
                tx = sim["txs"][a["tx"]]
                st = tx["status"]
                add(a, st is not UNKNOWN and st == a["equals"], f"status={st!r} error={tx['error']}"
                    + (" (node did not return status)" if st is UNKNOWN else ""))
            elif t == "log_count":
                logs = sim["txs"][a["tx"]]["logs"]
                if a.get("exclude_native", True):
                    logs = [l for l in logs if _lc(l["address"]) != NATIVE_PSEUDO]
                add(a, len(logs) == a["equals"], f"count={len(logs)}")
            elif t == "log":
                logs = [l for l in sim["txs"][a["tx"]]["logs"] if _lc(l["address"]) != NATIVE_PSEUDO]
                lg = logs[a["index"]]
                ok = True; why = []
                if "emitter" in a and _lc(lg["address"]) != _lc(a["emitter"]): ok = False; why.append(f"emitter {lg['address']}")
                if "topic0" in a and lg["topics"][0] != a["topic0"]: ok = False; why.append(f"topic0 {lg['topics'][0]}")
                for k, v in a.get("topic_addrs", {}).items():
                    if _taddr(lg["topics"][int(k)]) != _lc(v): ok = False; why.append(f"topic{k} {lg['topics'][int(k)]}")
                if "data_uint" in a:
                    dv = _hexint(lg.get("data"))
                    if dv is UNKNOWN or dv != a["data_uint"]: ok = False; why.append(f"data {lg.get('data')!r} (empty = UNKNOWN)")
                add(a, ok, "; ".join(why) or "match")
            elif t == "read":
                v = sim["reads"].get(a["name"], UNKNOWN)
                add(a, v is not UNKNOWN and v == a["equals"], f"{a['name']}={v!r}")
            elif t == "read_same":   # e.g. pre balance == post balance
                x = sim["pre"].get(a["a"], sim["reads"].get(a["a"], UNKNOWN))
                y = sim["reads"].get(a["b"], sim["pre"].get(a["b"], UNKNOWN))
                add(a, x is not UNKNOWN and y is not UNKNOWN and x == y, f"{a['a']}={x!r} {a['b']}={y!r}")
            elif t == "read_delta":  # post - pre == expected
                x = sim["pre"].get(a["before"], UNKNOWN); y = sim["reads"].get(a["after"], UNKNOWN)
                ok = x is not UNKNOWN and y is not UNKNOWN and (y - x) == a["equals"]
                add(a, ok, f"delta={(y - x) if ok or (x is not UNKNOWN and y is not UNKNOWN) else 'UNKNOWN'}")
            elif t == "native_only_gas_and_value":
                # expected decrease = sum(declared tx.value) + sum(gasUsed * gasPrice).
                # Traced native flows are listed and compared separately; they are NOT used as the
                # expectation (otherwise a hidden extra outflow would inflate both sides).
                nb, na = sim["native_before"], (sim["native_after"] or [UNKNOWN])[-1]
                if nb is UNKNOWN or na is UNKNOWN:
                    add(a, False, "native balance UNKNOWN"); continue
                if any(tx["gasUsed"] is UNKNOWN for tx in sim["txs"]):
                    add(a, False, "節點未回 gasUsed -> UNKNOWN, cannot verify fee"); continue
                gas = sum(tx["gasUsed"] * sim["gas_price"] for tx in sim["txs"])
                declared = sum(int(tx.get("value", 0) or 0) for tx in sim["txs"])
                exp_in = int(a.get("expected_native_in", 0))   # e.g. WETH unwrap / protocol withdraw in ETH
                expect = declared + gas - exp_in
                why = [f"actual_decrease={nb - na} expected={expect} (declared_value={declared}, gas={gas}, expected_in={exp_in})"]
                ok = (nb - na) == expect
                try:
                    flows = [_native_flows(sim, tx) for tx in sim["txs"]]
                    traced_out = sum(o for o, _ in flows); traced_in = sum(i for _, i in flows)
                    why.append(f"traced_out={traced_out} traced_in={traced_in}")
                    if traced_out != declared:
                        ok = False; why.append("traced native outflow != declared tx.value")
                    if traced_in != exp_in:
                        ok = False; why.append("traced native inflow != expected_native_in")
                except ValueError as e:
                    ok = False; why.append(str(e))
                kind = sim.get("owner_kind", "UNKNOWN")
                if kind != "EOA":
                    why.append(f"owner is {kind}: code on the owner can move value; review manually")
                    if not a.get("allow_owner_code"):
                        ok = False
                add(a, ok, "; ".join(why))
            elif t == "no_unexpected_addresses":
                # covers: ERC-20/721 Transfer from/to, ERC-1155 TransferSingle/Batch operator/from/to,
                # Approval / ApprovalForAll / Permit2 / BorrowAllowanceDelegated counterparties.
                allow = {_lc(x) for x in a["allow"]} | {"0x" + "0" * 40}
                bad = set()
                for tx in sim["txs"]:
                    for lg in tx["logs"]:
                        tp = lg.get("topics") or []
                        if not tp: continue
                        idx = []
                        if tp[0] == TRANSFER: idx = [1, 2]
                        elif tp[0] in (TRANSFER_SINGLE, TRANSFER_BATCH): idx = [1, 2, 3]
                        elif tp[0] in (APPROVAL, APPROVAL_FOR_ALL, PERMIT2_PERMIT, PERMIT2_APPROVAL): idx = [1, 2, 3]
                        elif tp[0] == BORROW_ALLOWANCE_DELEGATED: idx = [1, 2, 3]
                        for k in idx:
                            if k < len(tp):
                                ad = _taddr(tp[k])
                                # ERC-721 Approval topic3 is a tokenId, not an address
                                if tp[0] == APPROVAL and k == 3: continue
                                if tp[0] in (PERMIT2_PERMIT, PERMIT2_APPROVAL) and k == 2: continue  # token
                                if tp[0] == BORROW_ALLOWANCE_DELEGATED and k == 3: continue          # asset
                                if ad not in allow: bad.add(ad)
                add(a, not bad, "unexpected: " + ", ".join(sorted(bad)) if bad else "none")
            elif t == "no_new_nonzero_approval":
                # ERC-20 Approval (3 topics), ERC-721 single Approval (4 topics), ApprovalForAll,
                # Permit2 Approval + Permit, Aave-style BorrowAllowanceDelegated. except_spenders applies to all.
                o = _lc(a["owner"]); ok_sp = {_lc(x) for x in a.get("except_spenders", [])}; bad = []
                if o != _lc(sim["owner"]):
                    add(a, False, "owner mismatch: assertion owner differs from simulated owner")
                    continue
                for tx in sim["txs"]:
                    for lg in tx["logs"]:
                        tp = lg.get("topics") or []
                        if len(tp) < 2 or _taddr(tp[1]) != o: continue
                        data = lg.get("data")
                        if tp[0] == APPROVAL and len(tp) == 3:
                            v = _hexint(data)
                            if (v is UNKNOWN or v != 0) and _taddr(tp[2]) not in ok_sp:
                                bad.append((lg["address"], _taddr(tp[2]), "UNKNOWN(empty data)" if v is UNKNOWN else v))
                        elif tp[0] == APPROVAL and len(tp) == 4:
                            if _taddr(tp[2]) != "0x" + "0" * 40 and _taddr(tp[2]) not in ok_sp:
                                bad.append((lg["address"], _taddr(tp[2]), f"ERC-721 tokenId {int(tp[3], 16)}"))
                        elif tp[0] == APPROVAL_FOR_ALL:
                            v = _hexint(data)
                            if (v is UNKNOWN or v != 0) and _taddr(tp[2]) not in ok_sp:
                                bad.append((lg["address"], _taddr(tp[2]), "ApprovalForAll"))
                        elif tp[0] in (PERMIT2_APPROVAL, PERMIT2_PERMIT) and len(tp) >= 4:
                            v = _word(data, 0)
                            if (v is UNKNOWN or v != 0) and _taddr(tp[3]) not in ok_sp:
                                bad.append((lg["address"], _taddr(tp[3]), "Permit2 " + ("Approval" if tp[0] == PERMIT2_APPROVAL else "Permit")))
                        elif tp[0] == BORROW_ALLOWANCE_DELEGATED and len(tp) >= 3:
                            v = _word(data, 0)
                            if (v is UNKNOWN or v != 0) and _taddr(tp[2]) not in ok_sp:
                                bad.append((lg["address"], _taddr(tp[2]), "BorrowAllowanceDelegated"))
                add(a, not bad, f"{bad}" if bad else "none")
            else:
                add(a, False, f"unknown assertion type {t}")
        except (IndexError, KeyError, ValueError, TypeError) as e:
            add(a, False, f"cannot evaluate: {type(e).__name__} {e}")
    return {"pass": bool(results) and all(r["pass"] for r in results), "results": results, "rpc_used": sim["rpc_used"],
            "base_block": sim["base_block"], "gas_price": sim["gas_price"],
            "sim_blocks": [tx["block"] for tx in sim["txs"]], "gasUsed": [repr(tx["gasUsed"]) if tx["gasUsed"] is UNKNOWN else tx["gasUsed"] for tx in sim["txs"]],
            "overrides_used": sim["overrides_used"], "owner_kind": sim.get("owner_kind")}


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="exitkit simulate",
        description="Read-only eth_simulateV1 from a JSON spec. Nothing is signed or broadcast.",
    )
    parser.add_argument("spec", help="path to the JSON spec")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return 0 if code is None else int(code)
    try:
        with open(args.spec, encoding="utf-8") as handle:
            spec = json.load(handle)
    except OSError as exc:
        print(f"cannot read spec: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"spec is not JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(spec, dict):
        print("spec must be a JSON object", file=sys.stderr)
        return 1
    if spec.get("chain_id") is None:
        print("spec.chain_id is required (chainId verification is mandatory)", file=sys.stderr)
        return 1
    missing = [key for key in ("rpc", "owner", "txs") if key not in spec]
    if missing:
        print("spec is missing " + ", ".join(missing), file=sys.stderr)
        return 1
    try:
        rpc = RPC(spec["rpc"], label=spec.get("label", "sim"), expect_chain_id=spec["chain_id"],
                  wallets=[spec["owner"]],
                  allowed_hosts=spec.get("allowed_hosts"))
        sim = simulate(rpc, spec["owner"], spec["txs"], spec.get("reads", []), spec.get("pre_reads", []),
                       spec.get("state_overrides"), spec.get("base_block"), spec.get("gas_price"))
        rep = check(sim, spec.get("assertions", []))
    except (RPCError, KeyError, TypeError, ValueError) as exc:
        print(f"simulate failed: {exc}", file=sys.stderr)
        return 1
    rep["address_sent_to"] = rpc.disclosure()
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

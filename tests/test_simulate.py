import json

from exitkit.rpc import READ_METHODS, topic_addr
from exitkit.simulate import APPROVAL, check, main as simulate_main, simulate
from tests.fake_rpc import jsonrpc_ok, routed


def _owner():
    return "0x" + "1" * 40


def _token():
    return "0x" + "2" * 40


def _spender():
    return "0x" + "3" * 40


def _pass_result(balance=1_000_000, gas=21000):
    after = balance - gas
    return [{
        "number": "0x11",
        "calls": [
            {"status": "0x1", "gasUsed": hex(gas), "logs": []},
            {"status": "0x1", "gasUsed": "0x1", "logs": [], "returnData": hex(after)},
        ],
    }]


def _required(owner):
    return [
        {"type": "status", "tx": 0, "equals": 1},
        {"type": "native_only_gas_and_value"},
        {"type": "no_new_nonzero_approval", "owner": owner},
    ]


class SimRPC:
    def __init__(self, code="0x", sim_result=None, balance=1_000_000):
        self.wallets = set()
        self.code = code
        self.balance = balance
        self.sim_result = sim_result
        self.methods = []

    def block(self, number):
        return {"timestamp": "0x64", "number": hex(number)}

    def call_labeled(self, method, params):
        self.methods.append(method)
        assert method in READ_METHODS
        if method == "eth_getBalance":
            return True, hex(self.balance), "sim (fake)"
        if method == "eth_getCode":
            return True, self.code, "sim (fake)"
        if method == "eth_simulateV1":
            return True, self.sim_result, "sim (fake)"
        raise AssertionError(method)


def _run(sim_result, code="0x"):
    owner = _owner()
    rpc = SimRPC(code=code, sim_result=sim_result)
    sim = simulate(
        rpc, owner,
        [{"to": _token(), "data": "0x", "value": 0}],
        base_block=10, gas_price=1,
    )
    assert set(rpc.methods) <= READ_METHODS
    return owner, sim


def test_assertions_pass_for_a_plain_eoa_call():
    owner, sim = _run(_pass_result())
    assert sim["ok"] is True
    assert sim["owner_kind"] == "EOA"
    report = check(sim, _required(owner))
    assert report["pass"] is True


def test_zero_assertions_and_missing_required_fail():
    owner, sim = _run(_pass_result())
    assert check(sim, [])["pass"] is False
    assert check(sim, [{"type": "status", "tx": 0, "equals": 1}])["pass"] is False


def test_nonzero_approval_fails_and_zero_approval_does_not():
    owner, sim = _run(_pass_result())
    token = _token()
    spender = _spender()
    sim["txs"][0]["logs"].append({
        "address": token,
        "topics": [APPROVAL, topic_addr(owner), topic_addr(spender)],
        "data": "0x" + format(5, "x").rjust(64, "0"),
    })
    failed = check(sim, _required(owner))
    assert failed["pass"] is False
    assert any(
        item["assertion"].get("type") == "no_new_nonzero_approval" and item["pass"] is False
        for item in failed["results"]
    )

    _owner2, clean = _run(_pass_result())
    clean["txs"][0]["logs"].append({
        "address": token,
        "topics": [APPROVAL, topic_addr(owner), topic_addr(spender)],
        "data": "0x" + format(0, "x").rjust(64, "0"),
    })
    assert check(clean, _required(owner))["pass"] is True


def test_incomplete_simulation_is_not_a_pass():
    owner, sim = _run([])
    assert sim["ok"] is False
    assert "incomplete" in sim["error"]
    assert check(sim, _required(owner))["pass"] is False

    short = [{
        "number": "0x11",
        "calls": [{"status": "0x1", "gasUsed": "0x1", "logs": []}],
    }]
    _owner2, sim2 = _run(short)
    assert sim2["ok"] is False
    assert "incomplete" in sim2["error"]


def test_owner_with_code_fails_the_native_assertion():
    owner, sim = _run(_pass_result(), code="0x60006000")
    assert "CONTRACT" in sim["owner_kind"]
    assert check(sim, _required(owner))["pass"] is False


def test_missing_chain_id_exits_before_the_network(tmp_path, capsys):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"rpc": ["http://127.0.0.1:9"], "owner": _owner(), "txs": []}), encoding="utf-8")
    code = simulate_main([str(spec)])
    err = capsys.readouterr().err
    assert code == 1
    assert "chain_id is required" in err


def test_simulate_cli_passes_against_a_local_node(serve_rpc, tmp_path, capsys):
    seen = []
    balance = 1_000_000
    gas = 21000
    owner = _owner()

    def chain(req):
        return jsonrpc_ok(req, "0x1")

    def block(req):
        return jsonrpc_ok(req, {"timestamp": "0x10", "number": "0x10"})

    def bal(req):
        return jsonrpc_ok(req, hex(balance))

    def code(req):
        return jsonrpc_ok(req, "0x")

    def sim(req):
        return jsonrpc_ok(req, _pass_result(balance, gas))

    url = serve_rpc(routed({
        "eth_chainId": chain,
        "eth_getBlockByNumber": block,
        "eth_getBalance": bal,
        "eth_getCode": code,
        "eth_simulateV1": sim,
    }, seen))
    spec = {
        "rpc": [url],
        "chain_id": 1,
        "owner": owner,
        "base_block": 16,
        "gas_price": 1,
        "txs": [{"to": _token(), "data": "0x", "value": 0}],
        "assertions": _required(owner),
    }
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    code = simulate_main([str(path)])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["pass"] is True
    assert set(seen) <= READ_METHODS
    assert "eth_simulateV1" in seen
    for method in ("eth_sign", "eth_sendTransaction", "personal_sign", "wallet_sendCalls"):
        assert method not in seen

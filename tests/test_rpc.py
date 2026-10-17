import json

import pytest

from exitkit.cli import main as cli_main
from exitkit.rpc import READ_METHODS, RPC, RPCError, check_body, check_method
from tests.fake_rpc import jsonrpc_err, jsonrpc_ok, routed

FORBIDDEN = [
    "eth_sign",
    "ETH_SIGN",
    "Eth_Sign",
    "personal_sign",
    "PERSONAL_SIGN",
    "Personal_Sign",
    "eth_signTypedData",
    "eth_signTypedData_v1",
    "eth_signTypedData_v3",
    "eth_signTypedData_v4",
    "ETH_SIGNTYPEDDATA_V4",
    "Eth_SignTypedData_v4",
    "eth_signtypeddata_v4",
    "wallet_sendCalls",
    "WALLET_SENDCALLS",
    "Wallet_SendCalls",
    "eth_sendTransaction",
    "ETH_SENDTRANSACTION",
    "eth_sendRawTransaction",
]


def test_forbidden_methods_are_refused(method):
    with pytest.raises(RPCError, match="refused"):
        check_method(method)


test_forbidden_methods_are_refused = pytest.mark.parametrize("method", FORBIDDEN)(
    test_forbidden_methods_are_refused
)


def test_forbidden_names_are_not_allowlisted():
    assert set(FORBIDDEN).isdisjoint(READ_METHODS)


def test_non_string_and_non_ascii_are_refused():
    with pytest.raises(RPCError, match="refused"):
        check_method(None)
    with pytest.raises(RPCError, match="refused"):
        check_method(1)
    with pytest.raises(RPCError, match="non-ASCII"):
        check_method("eth_sign".replace("s", "\uff53"))
    with pytest.raises(RPCError, match="non-ASCII"):
        check_method("\u0435th_sign")


def test_allowlisted_casefold_returns_canonical_spelling():
    assert check_method("ETH_GETBALANCE") == "eth_getBalance"
    assert check_method("  eth_chainid  ") == "eth_chainId"


def test_batch_rejects_forbidden_entry_smuggling_and_noncanonical():
    with pytest.raises(RPCError, match="refused"):
        check_body([
            {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
            {"jsonrpc": "2.0", "id": 2, "method": "eth_sign", "params": []},
        ])
    with pytest.raises(RPCError, match="refused"):
        check_body([{
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"method": "eth_sendTransaction", "params": []}],
        }])
    with pytest.raises(RPCError, match="refused"):
        check_body([{
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getLogs",
            "params": [{"topics": [{"method": "wallet_sendCalls"}]}],
        }])
    with pytest.raises(RPCError, match="refused"):
        check_body([{"jsonrpc": "2.0", "id": 1, "method": "ETH_GETBALANCE", "params": []}])
    with pytest.raises(RPCError, match="refused"):
        check_body([])


def test_no_url_and_missing_chain_id_do_not_connect():
    with pytest.raises(RPCError, match="no RPC URL"):
        RPC([], expect_chain_id=1)
    with pytest.raises(RPCError, match="expect_chain_id"):
        RPC(["http://127.0.0.1:9"], expect_chain_id=None)


def test_allowed_hosts_blocks_before_any_request(monkeypatch):
    calls = []

    def boom(*args, **kwargs):
        calls.append(args)
        raise AssertionError("urlopen")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(RPCError, match="not allowed"):
        RPC(["http://127.0.0.1:9"], expect_chain_id=1, allowed_hosts=["rpc.example"])
    assert calls == []


def test_refused_methods_never_leave_the_process(serve_rpc):
    seen = []

    def chain(req):
        return jsonrpc_ok(req, "0x1")

    url = serve_rpc(routed({"eth_chainId": chain}, seen))
    rpc = RPC([url], expect_chain_id=1, retries=0, timeout=2, max_total_secs=5)
    assert seen == ["eth_chainId"]
    with pytest.raises(RPCError, match="refused"):
        rpc.call("personal_sign", [])
    with pytest.raises(RPCError, match="refused"):
        rpc.call("ETH_SIGN", [])
    with pytest.raises(RPCError, match="refused"):
        rpc.call("eth_signTypedData_v4", [])
    with pytest.raises(RPCError, match="refused"):
        rpc.batch([
            ("eth_getBalance", []),
            ("wallet_sendCalls", []),
        ])
    # A forbidden method name raises before send. A nested request hidden inside an
    # allowlisted call is refused inside the transport and returned as a failed item.
    smuggled = rpc.batch([("eth_call", [[{"method": "eth_sendRawTransaction", "params": []}]])])
    assert len(smuggled.values) == 1 and smuggled.values[0][0] is False
    assert "refused" in str(smuggled.values[0][1])
    raw = b'{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[],"method":"eth_sign"}'
    with pytest.raises(RPCError, match="duplicate"):
        rpc._transport(url, raw)
    assert seen == ["eth_chainId"]


def test_chain_id_mismatch_does_not_send_the_read(serve_rpc):
    seen = []

    def chain(req):
        return jsonrpc_ok(req, "0x2")

    url = serve_rpc(routed({"eth_chainId": chain}, seen))
    with pytest.raises(RPCError, match="mismatch"):
        RPC([url], expect_chain_id=1, retries=0, timeout=2, max_total_secs=5)
    assert seen == ["eth_chainId"]


def test_allowlisted_read_returns_the_result(serve_rpc):
    seen = []

    def chain(req):
        return jsonrpc_ok(req, "0x1")

    def block(req):
        return jsonrpc_ok(req, "0x2a")

    url = serve_rpc(routed({"eth_chainId": chain, "eth_blockNumber": block}, seen))
    rpc = RPC([url], expect_chain_id=1, retries=0, timeout=2, max_total_secs=5)
    assert rpc.block_number() == 42
    assert set(seen) <= READ_METHODS
    assert "eth_blockNumber" in seen


def test_rpc_cli_demo_stays_on_the_allowlist(serve_rpc, capsys):
    seen = []

    def chain(req):
        return jsonrpc_ok(req, "0x1")

    def block(req):
        return jsonrpc_ok(req, "0x10")

    def code(req):
        return jsonrpc_ok(req, "0x60016000")

    def call(req):
        return jsonrpc_ok(req, "0x")

    url = serve_rpc(routed({
        "eth_chainId": chain,
        "eth_blockNumber": block,
        "eth_getCode": code,
        "eth_call": call,
    }, seen))
    code_rc = cli_main(["rpc", "--rpc", url, "--chain-id", "1"])
    assert code_rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["block"] == 16
    assert "未知" in out["fake_eth_balance"]
    assert set(seen) <= READ_METHODS
    assert seen
    for method in ("eth_sign", "personal_sign", "eth_sendTransaction", "wallet_sendCalls"):
        assert method not in seen

import io
import json
import sys

from exitkit.decode import classify, main as decode_main


def _owner():
    return "0x" + "1" * 40


def _siwe(owner, expiration=True, danger=False):
    lines = [
        "example.test wants you to sign in with your Ethereum account:",
        owner,
        "",
        "URI: https://example.test/login",
        "Version: 1",
        "Chain ID: 1",
        "Nonce: abcdefgh",
        "Issued At: 2026-10-17T00:00:00Z",
    ]
    if expiration:
        lines.append("Expiration Time: 2026-10-17T01:00:00Z")
    if danger:
        lines.append("please approve this request")
    return "\n".join(lines)


def _personal(text):
    return {"method": "personal_sign", "params": ["0x" + text.encode().hex(), _owner()]}


def test_clean_siwe_is_user_decides_not_safe():
    res = classify(_personal(_siwe(_owner())), expect_chain_id=1)
    assert res["decision"] == "USER_DECIDES"
    assert res["category"].startswith("LOGIN")
    assert res["decision"] != "safe"


def test_siwe_without_expiry_or_with_a_permission_word_is_rejected():
    missing = classify(_personal(_siwe(_owner(), expiration=False)), expect_chain_id=1)
    assert missing["decision"] == "REJECT"
    danger = classify(_personal(_siwe(_owner(), danger=True)), expect_chain_id=1)
    assert danger["decision"] == "REJECT"


def test_raw_hash_and_permits_are_rejected():
    raw = classify({"method": "eth_sign", "params": []})
    assert raw["decision"] == "REJECT"
    assert "RAW HASH" in raw["category"]

    permit = classify({
        "method": "eth_signTypedData_v4",
        "params": [_owner(), {
            "domain": {"name": "Token", "chainId": 1},
            "primaryType": "Permit",
            "message": {"owner": _owner(), "spender": "0x" + "2" * 40, "value": 1},
        }],
    })
    assert permit["decision"] == "REJECT"
    assert "PERMIT" in permit["category"]

    permit2 = classify({
        "primaryType": "PermitSingle",
        "domain": {"name": "Permit2"},
        "message": {},
    })
    assert permit2["decision"] == "REJECT"
    assert "PERMIT2" in permit2["category"]

    dai = classify({
        "method": "eth_signTypedData_v4",
        "params": [_owner(), {
            "domain": {"name": "Dai"},
            "primaryType": "Permit",
            "message": {"holder": _owner(), "spender": "0x" + "3" * 40, "allowed": True},
        }],
    })
    assert dai["decision"] == "REJECT"
    assert "DAI-STYLE" in dai["category"]


def test_bad_json_is_a_reject_and_exit_zero(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    assert decode_main([str(path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["decision"] == "REJECT"
    assert out["category"] == "PARSE ERROR"


def test_decode_cli_reads_a_file(tmp_path, capsys):
    path = tmp_path / "req.json"
    path.write_text(json.dumps({"method": "eth_sign", "params": []}), encoding="utf-8")
    assert decode_main([str(path), "--expect-chain-id", "1"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["decision"] == "REJECT"
    assert "RAW HASH" in out["category"]


def test_amount_containing_7702_is_not_labeled_as_delegation():
    res = classify({
        "primaryType": "Mail",
        "domain": {"name": "Example", "chainId": 1},
        "types": {"Mail": [{"name": "amount", "type": "uint256"}]},
        "message": {"amount": "7702"},
    })
    assert res["decision"] == "REJECT"
    assert "7702" not in res["category"]
    assert "UNKNOWN" in res["category"]


def test_authorization_type_is_still_rejected_as_eip_7702():
    res = classify({
        "primaryType": "Authorization",
        "domain": {"name": "Example", "chainId": 1},
        "types": {"Authorization": [{"name": "chainId", "type": "uint256"}]},
        "message": {"chainId": 1},
    })
    assert res["decision"] == "REJECT"
    assert "EIP-7702" in res["category"]


def test_decode_cli_reads_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not-json"))
    assert decode_main([]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["decision"] == "REJECT"

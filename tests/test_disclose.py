import json

from exitkit.disclose import main as disclose_main
from exitkit.rpc import KIND_BLOCK, KIND_WALLET


MNEMONIC = " ".join([
    "abandon", "ability", "able", "about", "above", "absent",
    "absorb", "abstract", "absurd", "abuse", "access", "accident",
])


def _add(purpose, log="log.jsonl"):
    return [
        "add", "--log", log, "--service", "notes", "--host", "rpc.example",
        "--endpoint", "/api/v2/tokens", "--kind", "block", "--purpose", purpose,
        "--when", "2026-10-17T00:00:00+00:00",
    ]


def test_secrets_are_refused_and_nothing_is_written(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    refused = [
        MNEMONIC,
        "store the private key offline",
        "the signature is attached",
        "send the api key today",
        "這是助記詞不要寫",
        "paid " + "0x" + ("1" * 40),
    ]
    for purpose in refused:
        assert disclose_main(_add(purpose, "no.jsonl")) == 2
        err = capsys.readouterr().err
        assert err.startswith("refused:")
        assert not (tmp_path / "no.jsonl").exists()


def test_ordinary_notes_are_accepted(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    allowed = [
        "multi-sig wallet setup",
        "rotate access tokens monthly",
        "turkey store inventory",
    ]
    for purpose in allowed:
        assert disclose_main(_add(purpose, "yes.jsonl")) == 0
        capsys.readouterr()
    text = (tmp_path / "yes.jsonl").read_text(encoding="utf-8")
    for purpose in allowed:
        assert purpose in text
    assert disclose_main(["render", "--log", "yes.jsonl", "--wallet-site", "app.example"]) == 0
    rendered = capsys.readouterr().out
    assert "這次把地址送到哪些服務" in rendered
    assert "multi-sig wallet setup" in rendered
    assert "app.example" in rendered


def test_refusal_does_not_append_to_an_existing_log(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert disclose_main(_add("multi-sig wallet setup", "keep.jsonl")) == 0
    capsys.readouterr()
    size = (tmp_path / "keep.jsonl").stat().st_size
    assert disclose_main(_add("my private key note", "keep.jsonl")) == 2
    assert (tmp_path / "keep.jsonl").stat().st_size == size


def test_import_and_render(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    payload = {
        "rpc.example:8545": {
            "methods": ["eth_chainId", "eth_getBalance"],
            "sent": [KIND_WALLET, KIND_BLOCK],
            "chain_id_verified": False,
        }
    }
    (tmp_path / "disc.json").write_text(json.dumps(payload), encoding="utf-8")
    assert disclose_main([
        "import", "--log", "imp.jsonl", "--disclosure-json", "disc.json",
        "--service", "RPC node", "--purpose", "balances",
    ]) == 0
    imported = json.loads(capsys.readouterr().out)
    assert imported["imported"] == 2
    assert disclose_main(["render", "--log", "imp.jsonl"]) == 0
    rendered = capsys.readouterr().out
    assert "rpc.example:8545" in rendered
    assert KIND_WALLET in rendered
    assert "chainId 未驗證" in rendered

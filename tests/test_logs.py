import json

from exitkit.logs import get_logs, main as logs_main
from exitkit.rpc import READ_METHODS, BatchResult
from tests.fake_rpc import jsonrpc_err, jsonrpc_ok, routed


class _Boom:
    def batch(self, calls):
        raise AssertionError("should not scan")


def test_time_budget_marks_unscanned_ranges_unknown():
    result = get_logs(_Boom(), 0, 20, chunk=10, time_budget=-1, rate_retries=0)
    assert result["status"] == "INCOMPLETE"
    assert result["complete"] is False
    assert result["logs"] == []
    assert result["failed"]
    assert all("time budget" in item[2] for item in result["failed"])


def test_rate_limit_does_not_split():
    class Rate:
        def batch(self, calls):
            values = [(False, "429 too many requests") for _ in calls]
            return BatchResult(values, "logs (fake)")

    result = get_logs(Rate(), 0, 99, chunk=100, min_chunk=10, rate_retries=0, time_budget=30)
    assert len(result["failed"]) == 1
    assert result["failed"][0][0] == 0
    assert result["failed"][0][1] == 99
    assert "rate-limited" in result["failed"][0][2]
    assert result["status"] == "INCOMPLETE"


def test_oversized_range_splits_until_it_fits():
    class Split:
        def batch(self, calls):
            values = []
            for _method, params in calls:
                flt = params[0]
                size = int(flt["toBlock"], 16) - int(flt["fromBlock"], 16) + 1
                if size > 64:
                    values.append((False, "block range too large"))
                else:
                    values.append((True, []))
            return BatchResult(values, "logs (fake)")

    result = get_logs(Split(), 0, 127, chunk=128, min_chunk=64, rate_retries=0)
    assert result["complete"] is True
    assert result["status"] == "COMPLETE"
    assert result["failed"] == []
    assert result["coverage"] == 1


def test_provider_cap_is_suspect_not_complete():
    class Cap:
        def batch(self, calls):
            logs = [{
                "transactionHash": "0x" + "ab" * 32,
                "logIndex": hex(i),
                "blockNumber": "0x5",
            } for i in range(1000)]
            return BatchResult([(True, logs) for _ in calls], "logs (fake)")

    result = get_logs(Cap(), 0, 9, chunk=10, min_chunk=10, rate_retries=0)
    assert result["suspect"]
    assert result["complete"] is False
    assert result["status"] == "INCOMPLETE"


def _logs_server(serve_rpc, logs_result):
    seen = []

    def chain(req):
        return jsonrpc_ok(req, "0x1")

    def getlogs(req):
        if isinstance(logs_result, str):
            return jsonrpc_err(req, logs_result)
        return jsonrpc_ok(req, logs_result)

    url = serve_rpc(routed({"eth_chainId": chain, "eth_getLogs": getlogs}, seen))
    return url, seen


def test_logs_cli_gap_is_unknown_and_nonzero(serve_rpc, capsys):
    url, seen = _logs_server(serve_rpc, "method not found")
    code = logs_main([
        "--rpc", url, "--chain-id", "1", "--from-block", "0", "--to-block", "10",
        "--chunk", "20", "--retries", "0", "--rate-retries", "0", "--timeout", "2",
        "--time-budget", "30",
    ])
    assert code == 2
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "INCOMPLETE"
    assert out["log_count"] == "UNKNOWN"
    assert out["logs_found_in_scanned_ranges"] == 0
    assert set(seen) <= READ_METHODS


def test_logs_cli_complete_scan_exits_zero(serve_rpc, capsys, tmp_path):
    url, seen = _logs_server(serve_rpc, [])
    out_path = tmp_path / "logs.json"
    code = logs_main([
        "--rpc", url, "--chain-id", "1", "--from-block", "0", "--to-block", "10",
        "--chunk", "20", "--retries", "0", "--rate-retries", "0", "--timeout", "2",
        "--time-budget", "30", "--out", str(out_path),
    ])
    captured = capsys.readouterr()
    assert code == 0
    out = json.loads(captured.out)
    assert out["status"] == "COMPLETE"
    assert out["log_count"] == 0
    assert out_path.is_file()
    assert "WARNING" in captured.err
    assert set(seen) <= READ_METHODS


def test_logs_out_refuses_an_existing_file_without_force(serve_rpc, capsys, tmp_path):
    url, seen = _logs_server(serve_rpc, [])
    out_path = tmp_path / "logs.json"
    out_path.write_text("keep", encoding="utf-8")
    code = logs_main([
        "--rpc", url, "--chain-id", "1", "--from-block", "0", "--to-block", "10",
        "--chunk", "20", "--retries", "0", "--rate-retries", "0", "--timeout", "2",
        "--time-budget", "30", "--out", str(out_path),
    ])
    captured = capsys.readouterr()
    assert code == 2
    assert out_path.read_text(encoding="utf-8") == "keep"
    assert "force" in captured.err
    assert seen == []


def test_logs_out_force_overwrites(serve_rpc, capsys, tmp_path):
    url, seen = _logs_server(serve_rpc, [])
    out_path = tmp_path / "logs.json"
    out_path.write_text("keep", encoding="utf-8")
    code = logs_main([
        "--rpc", url, "--chain-id", "1", "--from-block", "0", "--to-block", "10",
        "--chunk", "20", "--retries", "0", "--rate-retries", "0", "--timeout", "2",
        "--time-budget", "30", "--out", str(out_path), "--force",
    ])
    assert code == 0
    capsys.readouterr()
    assert out_path.read_text(encoding="utf-8") != "keep"
    assert set(seen) <= READ_METHODS

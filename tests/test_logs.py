import json
import urllib.error

import pytest

from exitkit.logs import get_logs, main as logs_main
from exitkit.rpc import READ_METHODS, BatchResult, RPC
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


@pytest.mark.parametrize("error", [
    "429 too many requests",
    {"code": -32000, "message": "rate limit exceeded, retry later"},
    {"code": -32000, "message": "too many requests, retry later"},
])
def test_rate_limit_does_not_split(error):
    requested_ranges = []

    class Rate:
        def batch(self, calls):
            requested_ranges.extend((int(params[0]["fromBlock"], 16),
                                     int(params[0]["toBlock"], 16)) for _, params in calls)
            values = [(False, error) for _ in calls]
            return BatchResult(values, "logs (fake)")

    result = get_logs(Rate(), 0, 99, chunk=100, min_chunk=10, rate_retries=0, time_budget=30)
    assert len(result["failed"]) == 1
    assert result["failed"][0][0] == 0
    assert result["failed"][0][1] == 99
    assert "rate-limited" in result["failed"][0][2]
    assert result["status"] == "INCOMPLETE"
    assert requested_ranges == [(0, 99)]


def test_error_text_containing_rate_limit_words_is_not_rate_limited():
    class OtherError:
        def batch(self, calls):
            return BatchResult(
                [(False, "upstream says rate limit metadata is unavailable") for _ in calls],
                "logs (fake)",
            )

    result = get_logs(OtherError(), 0, 0, chunk=1, rate_retries=0, time_budget=30)
    assert result["failed"] == [(0, 0, "upstream says rate limit metadata is unavailable")]


def test_json_rpc_rate_limit_code_is_classified_without_message_matching():
    class Rate:
        def batch(self, calls):
            return BatchResult(
                [(False, {"code": -32005, "message": "provider busy"}) for _ in calls],
                "logs (fake)",
            )

    result = get_logs(Rate(), 0, 0, chunk=1, rate_retries=0, time_budget=30)
    assert "rate-limited" in result["failed"][0][2]


def test_structured_http_429_is_classified_with_an_opaque_message():
    class Rate:
        def batch(self, calls):
            return BatchResult(
                [(False, {"http_status": 429, "message": "provider busy"}) for _ in calls],
                "logs (fake)",
            )

    result = get_logs(Rate(), 0, 99, chunk=100, min_chunk=10, rate_retries=0)
    assert len(result["failed"]) == 1
    assert result["failed"][0][:2] == (0, 99)
    assert "rate-limited" in result["failed"][0][2]


def test_json_rpc_error_merely_mentioning_http_429_is_not_rate_limited():
    class OtherError:
        def batch(self, calls):
            return BatchResult([
                (False, {
                    "code": -32602,
                    "message": "parameter must not contain HTTP 429 text",
                }) for _ in calls
            ], "logs (fake)")

    result = get_logs(OtherError(), 0, 0, chunk=1, rate_retries=0, time_budget=30)
    assert "rate-limited" not in result["failed"][0][2]


def test_http_429_transport_error_is_rate_limited_without_a_socket(monkeypatch):
    class TooManyRequests:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(
                request.full_url, 429, "Too Many Requests", {}, None,
            )

    monkeypatch.setattr("exitkit.rpc._OPENER", TooManyRequests())
    rpc = object.__new__(RPC)
    rpc.urls = ["http://rpc.example"]
    rpc.allow_fallback = False
    rpc.allowed_hosts = None
    rpc.label = "logs"
    rpc.wallets = set()
    rpc.log = []
    rpc.sent = []
    rpc._verified = {rpc.urls[0]: True}
    rpc._id = 0
    rpc.retries = 0
    rpc.timeout = 1
    rpc.max_total_secs = 1
    rpc.ua = "test"
    batch_result = rpc.batch([("eth_getLogs", [{"fromBlock": "0x0", "toBlock": "0x0"}])])
    ok, error = batch_result.values[0]
    assert ok is False
    assert isinstance(error, dict)
    assert error["http_status"] == 429
    # Remove all textual 429 clues: classification must use propagated status.
    error["message"] = "provider busy"
    monkeypatch.setattr(rpc, "batch", lambda calls: batch_result)
    result = get_logs(rpc, 0, 0, chunk=1, rate_retries=0, time_budget=30)
    assert "rate-limited" in result["failed"][0][2]


@pytest.mark.parametrize("error", [
    "block range too large",
    {"code": -32000, "message": "limit exceeded"},
    {"code": -32005, "message": "query returned more than 10000 results"},
    {"code": -32005, "message": "block range too large"},
    {"code": -32005, "message": "limit exceeded"},
])
def test_oversized_range_splits_until_it_fits(error):
    requested_ranges = []

    class Split:
        def batch(self, calls):
            values = []
            for _method, params in calls:
                flt = params[0]
                requested_ranges.append((int(flt["fromBlock"], 16), int(flt["toBlock"], 16)))
                size = int(flt["toBlock"], 16) - int(flt["fromBlock"], 16) + 1
                if size > 64:
                    values.append((False, error))
                else:
                    values.append((True, []))
            return BatchResult(values, "logs (fake)")

    result = get_logs(Split(), 0, 127, chunk=128, min_chunk=64, rate_retries=0)
    assert result["complete"] is True
    assert result["status"] == "COMPLETE"
    assert result["failed"] == []
    assert result["coverage"] == 1
    assert requested_ranges == [(0, 127), (0, 63), (64, 127)]


@pytest.mark.parametrize("option", ["chunk", "batch"])
@pytest.mark.parametrize("value", [0, -1])
def test_get_logs_rejects_nonpositive_sizes_before_building_queue(monkeypatch, option, value):
    def must_not_build_queue(*args):
        raise AssertionError("invalid chunk reached queue construction")

    # Bound the pre-fix failure: never let an invalid chunk grow the queue forever.
    monkeypatch.setattr("exitkit.logs.min", must_not_build_queue, raising=False)
    with pytest.raises(ValueError, match=option + ".*at least 1"):
        get_logs(_Boom(), 0, 99, **{option: value})


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


@pytest.mark.parametrize("address", ["0x1234", "0x" + "gg" * 20])
def test_logs_cli_rejects_invalid_topic_address_before_rpc(monkeypatch, capsys, address):
    def rpc_must_not_be_constructed(*args, **kwargs):
        raise AssertionError("RPC constructed")

    monkeypatch.setattr("exitkit.logs.RPC", rpc_must_not_be_constructed)
    with pytest.raises(SystemExit) as exc:
        logs_main([
            "--rpc", "http://127.0.0.1:9", "--chain-id", "1",
            "--topic1-addr", address, "--from-block", "0", "--to-block", "0",
        ])
    assert exc.value.code == 2
    assert "exactly 20 bytes" in capsys.readouterr().err


@pytest.mark.parametrize("option", ["--chunk", "--batch"])
@pytest.mark.parametrize("value", ["0", "-1"])
def test_logs_cli_rejects_sizes_less_than_one_before_rpc(monkeypatch, capsys, option, value):
    def rpc_must_not_be_constructed(*args, **kwargs):
        raise AssertionError("RPC constructed")

    monkeypatch.setattr("exitkit.logs.RPC", rpc_must_not_be_constructed)
    with pytest.raises(SystemExit) as exc:
        logs_main([
            "--rpc", "http://127.0.0.1:9", "--chain-id", "1",
            "--from-block", "0", "--to-block", "0", option, value,
        ])
    assert exc.value.code == 2
    assert "at least 1" in capsys.readouterr().err


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

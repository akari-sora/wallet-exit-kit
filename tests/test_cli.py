import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "onchain-exit-assist" / "scripts"
WRAPPERS = {
    "rpc.py": "exitkit.rpc",
    "disclosure_log.py": "exitkit.disclose",
    "get_logs_chunked.py": "exitkit.logs",
    "simulate.py": "exitkit.simulate",
    "decode_sign_request.py": "exitkit.decode",
    "address_audit.py": "exitkit.audit",
}


def test_wrappers_only_delegate():
    for name in WRAPPERS:
        text = (SCRIPTS / name).read_text(encoding="utf-8")
        assert "exitkit." in text
        assert len(text.splitlines()) < 40
        for banned in ("def check_method", "def get_logs", "def classify", "def scan_hex", "BIP39", "READ_METHODS"):
            assert banned not in text


def test_wrapper_exports_the_package_object():
    path = SCRIPTS / "rpc.py"
    spec = importlib.util.spec_from_file_location("skill_rpc_wrapper", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    import exitkit.rpc as rpc
    assert module.RPC is rpc.RPC
    assert module.check_method is rpc.check_method
    assert module.main is rpc.main


def test_package_source_has_no_hardcoded_url():
    root = ROOT / "src" / "exitkit"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "https://" not in text
        assert "http://" not in text


def test_cli_help_and_unknown_command():
    help_proc = subprocess.run(
        [sys.executable, "-m", "exitkit", "--help"],
        check=False, capture_output=True, text=True,
    )
    assert help_proc.returncode == 0
    for name in ("rpc", "logs", "simulate", "decode", "audit", "disclose", "install"):
        assert name in help_proc.stdout
    bad = subprocess.run(
        [sys.executable, "-m", "exitkit", "nope"],
        check=False, capture_output=True, text=True,
    )
    assert bad.returncode == 2
    assert "unknown command" in bad.stderr

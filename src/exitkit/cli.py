"""exitkit command line. Read-only. No signing and no broadcasting."""

from __future__ import annotations

import sys

from exitkit import audit, decode, disclose, install, logs, rpc, simulate

_HELP = """usage: exitkit <command> [args]

Read-only wallet exit toolkit. It does not sign or broadcast.
Network calls go only to the RPC URL you pass in.

commands:
  rpc        read allowlisted JSON-RPC methods
  logs       chunked eth_getLogs (gaps are UNKNOWN, exit non-zero)
  simulate   eth_simulateV1 plus assertions
  decode     classify a signature request offline
  audit      scan a folder for addresses and sensitive strings
  disclose   disclosure log: add, import, render
  install    install skills (dry-run unless --apply)
"""


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)
    if not argv:
        sys.stderr.write(_HELP)
        return 2
    if argv[0] in ("-h", "--help"):
        sys.stdout.write(_HELP)
        return 0
    cmd, rest = argv[0], argv[1:]
    commands = {
        "rpc": rpc.main,
        "logs": logs.main,
        "simulate": simulate.main,
        "decode": decode.main,
        "audit": audit.main,
        "disclose": disclose.main,
        "install": install.main,
    }
    fn = commands.get(cmd)
    if fn is None:
        sys.stderr.write(_HELP)
        sys.stderr.write(f"unknown command: {cmd}\n")
        return 2
    code = fn(rest)
    return 0 if code is None else int(code)

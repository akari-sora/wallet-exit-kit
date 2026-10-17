#!/usr/bin/env python3
"""Thin wrapper. The implementation lives in exitkit.decode."""

import exitkit.decode as _impl

_SKIP = {"__name__", "__file__", "__package__", "__loader__", "__spec__", "__cached__", "__builtins__"}
globals().update({name: value for name, value in vars(_impl).items() if name not in _SKIP})

if __name__ == "__main__":
    raise SystemExit(main())

# Changelog

## [Unreleased]

### Changed

- Shareable Wallet Guardian bot v1.2.0 (files and manual setup; the public template link still serves v1.1.0 because the six-skill package exceeds the platform's template size limit): new `wallet-guardian-keys` (free read-only API keys through the secure secret card) and `wallet-guardian-notify` (Grok app notifications; Telegram private chat and ntfy.sh only after the helper's rules-check passes under rules v1.2) skills, rules v1.2, `SHA256SUMS`. The README notes that Grok Bot template imports may currently arrive without skills.
- `exitkit audit`: a short list of exact public strings (Telegram's official bot-creation handle, generic `@username`-style placeholders, the `name.eth` example, the Grok Bot platform skill folder) is reported as PUBLIC instead of REVIEW only as a whole token; near misses stay REVIEW. In a file named `SHA256SUMS`, a 64-hex value is PUBLIC only when the file it lists (same folder or below, not a symlink, no path escape) really has that SHA-256.
- Shareable Grok Bot template v1.1.0: the rules pin the watch-only `guardian` CLI v0.4.0-rc.6 (wheel and constraints.txt by SHA-256) instead of rc.5. Red-team summary adds the rc.6 install re-test. Same public link, updated in place.

### Fixed

- Fail approval assertions when the checked owner differs from the simulated owner; reject malformed topic addresses and chunk/batch sizes below 1 before RPC use, including direct `get_logs` calls.
- Make missing or unreadable audit inputs and unfollowed symlinked directories fail. Display every hex run of 64 or more characters as first 4 / last 4 plus length, including glued/padded values, signatures, seeds, forbidden substrings, paths and argparse diagnostics; prevent the split-line scan from exposing long-run fragments while detecting split addresses followed by non-hex `x`/`X` boundaries.
- Preserve range splitting for generic `limit exceeded` and Infura -32005 result/range errors. HTTP and JSON-RPC 429 override split hints; retry-after and Infura project-rate messages keep the same range. Verify HTTP 429 status propagation and distinguish structured status from incidental `429` text.
- Require checksum-verified GitLab release assets in installation guidance, with an explicit warning against installing this toolkit from PyPI. Guard against `uvx`, `uv add`, `uv tool run`, `uv run --with`, `pipx run` and PEP 503 normalized package names as well as pip installs.
- Add regression tests for these cases.

## [0.1.0] - 2026-10-17

First release. Read-only: nothing in this kit holds keys, signs or broadcasts.

- `exitkit` CLI: JSON-RPC allowlist that refuses every signing and sending method (any letter case, also inside batches), `chain_id` check before use, unknown reads stay unknown, `audit` for public-address hygiene, decode, simulate and log helpers.
- Installer: dry-run by default; `--apply` links skills for Claude Code, Codex, Cursor, Hermes and Grok; never follows a destination symlink; Grok output stays inside HOME.
- Skills: `onchain-exit-assist` (asset and approval scan, revoke and exit check cards, deadline watch), `pendle-exit`, `campaign-radar`. Frontmatter valid for strict YAML loaders.
- Grok Bot templates under `templates/grok-bot/`:
  - `wallet-exit-assistant` v4.1 with its red-team summary (v3 main run: 29 verdicts, all PASS; v4 re-ran the 6 affected scenarios, all PASS; v4.1 re-ran the 3 scenarios it changed, all PASS).
  - `wallet-guardian-share` v1.0.0: the public Wallet Guardian template (https://x.ai/bot/TSOnLDpWzPi39xvgxjEtu), its instructions, four skills and red-team summary.
- README and zh-TW notes: front page, quick start from GitLab Releases with `SHA256SUMS`.

The release archive is the full source tree (`git archive`), not a Python sdist. Tests: `pytest` and `exitkit audit .` in GitLab CI on the release commit.

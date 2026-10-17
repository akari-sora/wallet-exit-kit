# Changelog

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

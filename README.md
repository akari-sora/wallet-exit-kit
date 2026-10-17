# wallet-exit-kit

Read-only toolkit and agent skills for preparing to leave DeFi positions. It reads chain data and writes check cards. The user always signs in their own wallet. Nothing here holds keys, signs, or broadcasts.

GitLab is the canonical repository: https://gitlab.com/aa22396584/wallet-exit-kit . Issues and merge requests go there. A GitHub mirror may exist; it is not the place for issues or merge requests.

License: AGPL-3.0-only.

Chinese notes: [docs/zh-TW.md](docs/zh-TW.md).

## Read-only, no signing, no sending

- JSON-RPC uses one allowlist. Anything else is refused on this machine, before a request is sent. That includes `eth_send*`, `eth_sign`, `personal_sign`, `eth_signTypedData*`, `wallet_sendCalls`, and the same names in any other letter case, including when they are hidden inside a batch.
- There is no built-in RPC URL. Every call goes to the URL you pass. The tool does not add another host.
- `chain_id` is required. Each URL is checked with `eth_chainId` before it is used.
- A failed or missing read is unknown. It is not reported as zero.
- A log scan with a gap reports `log_count` as `UNKNOWN` and exits non-zero.
- A simulation with no assertions, or with a short reply from the node, is not a pass.
- Signature requests are classified offline. The classifier does not sign them.

This package does not claim to cover every chain, and it does not claim that a card is safe to send. The onchain-exit-assist skill is a reviewed draft: it prepares steps for you to check and sign yourself.

## Install the CLI

Python 3.12 or newer. The toolkit code uses the standard library. This checkout also installs pytest so the tests below can run.

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/exitkit --help
```

Run commands from the checkout. `exitkit install` finds `skills/` by walking up from the installed package and from the current directory.

## Install a skill

`skills/<name>/SKILL.md` is one skill. `exitkit install` plans an install for every skill it finds. The default is a dry-run: it prints the plan and writes nothing. `--apply` writes. The default write is a symlink to the skill directory in this checkout. `--copy` copies the files instead. An existing directory with the same name is left as it is. `--force` renames that directory to `<name>.exitkit-bak-<utc>` and then installs.

| `--target` | Destination |
|---|---|
| `claude` (default set) | `~/.claude/skills/<skill>` |
| `codex` (default set) | `~/.codex/skills/<skill>` |
| `cursor` (default set) | `~/.cursor/skills/<skill>` |
| `agents` (default set) | `~/.agents/skills/<skill>` |
| `hermes` (default set) | `~/.hermes/skills/<skill>` |
| `grok` | one markdown file, references inlined after `SKILL.md` |

`--home` overrides `HOME` (useful for a throwaway directory). `--skill` limits the install to one name.

```bash
exitkit install
exitkit install --apply
exitkit install --apply --target cursor --skill onchain-exit-assist
exitkit install --apply --copy --target codex
exitkit install --apply --force --target hermes --skill onchain-exit-assist
exitkit install --target grok --skill onchain-exit-assist
exitkit install --target grok --apply --skill onchain-exit-assist > /tmp/onchain-exit-assist.md
```

The grok dry-run prints a JSON plan. `--apply` without `--output` prints the markdown on standard output. `--output` writes that file (absolute path).

Skills in this repo (all read-only; none signs, broadcasts or holds keys):

- `skills/onchain-exit-assist/`: inventory assets and approvals on EVM chains, grade approvals, and write revoke and exit checklist cards the user signs in their own wallet.
- `skills/campaign-radar/`: watch exchange and wallet campaigns, Earn products and airdrops; report changes and deadlines within 72 hours. It never logs in or joins.
- `skills/pendle-exit/`: look up Pendle and Penpie positions and list exit paths, rewards and risks. The contract addresses in it are public protocol contracts; re-check them against the cited sources before use.

`templates/grok-bot/wallet-exit-assistant/` holds a Grok bot template (v4, `TEMPLATE.md`) and its red-team summary. Six v4 scenarios were still running when it was added; `REDTEAM-SUMMARY.md` marks them as in progress.

The installer picks up any new `skills/<name>/SKILL.md` without a CLI change.

`skills/onchain-exit-assist/scripts/*.py` are thin wrappers around this package. There is one implementation, in `exitkit`.

## Commands

Placeholders only. `0x1111…1111` is a fake address. `<RPC_URL>` is your endpoint.

### `exitkit rpc`

Allowlisted read methods only. This demo reads a fake address.

```bash
exitkit rpc --rpc "$RPC_URL" --chain-id 1
```

Library: `exitkit.rpc.RPC`, `register_wallets`, `disclosure`.

### `exitkit logs`

Chunked `eth_getLogs`. A gap or a suspected truncation sets `log_count` to `UNKNOWN` and the exit code is not 0. Rate-limit errors are retried, not split.

```bash
exitkit logs --rpc "$RPC_URL" --chain-id 1 \
  --topic0 0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925 \
  --topic1-addr 0x1111111111111111111111111111111111111111 \
  --from-block 26200000 --to-block latest
```

`--allowed-host` repeats when you want to limit the host. `--out` writes raw logs that contain the queried address; use a temp file and delete it.

### `exitkit simulate`

`eth_simulateV1` plus an assertion list. `chain_id` in the spec is required.

```bash
exitkit simulate spec.json
```

```json
{
  "rpc": ["<RPC_URL>"],
  "chain_id": 1,
  "owner": "0x1111111111111111111111111111111111111111",
  "txs": [{"to": "0x2222222222222222222222222222222222222222", "data": "0x", "value": 0}],
  "assertions": [
    {"type": "status", "tx": 0, "equals": 1},
    {"type": "native_only_gas_and_value"},
    {"type": "no_new_nonzero_approval", "owner": "0x1111111111111111111111111111111111111111"}
  ]
}
```

Zero assertions is a failure. Every transaction needs a `status` assertion. The list must include `native_only_gas_and_value` and `no_new_nonzero_approval`. If the node returns a different number of blocks or calls, the result is a failure, not a pass.

### `exitkit decode`

Offline classification of a signature request. It does not sign and does not use the network. A clean login is `USER_DECIDES`, never "safe". Everything else is `REJECT`.

```bash
exitkit decode request.json --expect-chain-id 1
```

### `exitkit audit`

Heuristic scan of a folder for addresses and a few sensitive patterns (long hex, public-looking handles, email, home-directory paths, and similar). Public Multicall3, Uniswap Permit2, the native-asset placeholder, the zero address, precompile 1, known event topics, and obvious fake addresses (such as `0x1111…1111`) are not review items. A glued hex run next to one of those still is. Exit code 1 when anything needs review.

```bash
exitkit audit .
exitkit audit docs --forbid SECRET-MARKER
```

`PASS` means none of those patterns were found. It does not mean a document has no private data.

The walker skips `__pycache__`, `.git`, `.venv`, `.omc`, cache directories, `dist`, `build`, and `*.egg-info`, so this command can be run on a checkout after creating `.venv`.

### `exitkit disclose`

Append-only log for the report section that lists where an address was sent. Fields are refused when they look like an address, a hash, a key, a seed phrase, or an API key. Ordinary notes such as `multi-sig wallet setup` and `rotate access tokens monthly` are accepted.

```bash
exitkit disclose add --log "$TMP/disclosure.jsonl" \
  --service "Blockscout API" --host "eth.blockscout.com" \
  --endpoint "/api/v2/addresses/{addr}/tokens" --kind wallet \
  --purpose "token list"
exitkit disclose import --log "$TMP/disclosure.jsonl" \
  --disclosure-json "$TMP/rpc-disclosure.json"
exitkit disclose render --log "$TMP/disclosure.jsonl" --wallet-site "app.example"
```

`import` reads a JSON object in the shape of `RPC.disclosure()`. Keep the log in a temp directory and delete it after use. A refused field exits 2 and writes nothing.

## Tests

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pytest -q
.venv/bin/exitkit audit .
```

Tests are offline. They use a local fake RPC server or stand-ins. They do not call a public endpoint.

## Known limitations

These match the onchain-exit-assist changelog. They are not fixed in this package.

- Seed phrases: 11 or fewer BIP-39 words in a row are not blocked. Words stuck together, with or without camel case, are not blocked. Four-letter prefixes are not blocked. Non-English wordlists are not blocked.
- Hex split by spaces or hyphens into pieces shorter than 32 characters is not blocked.
- Base64 split into short pieces, or percent-encoded (`%2F`, `%2B`, `%3D`), is not blocked.
- A long base64url string that uses `-` or `_` and has no digit is still allowed (about 0.07% of random samples). The check still requires a digit.
- Some harmless phrases are still refused: `apikeys docs page`, `bearer bonds`, `key store hours`, `pass word game`; a hyphenated identifier with a segment longer than 12 characters; a mixed-case camelCase identifier of 32 or more characters that contains a digit and no hyphen.
- Disclosure fields refuse public contract addresses and transaction hashes too. Use placeholders such as `{addr}` and `{hash}`.
- `when` accepts only ISO-8601 text or epoch seconds.
- `disclosure()` can tell a full wallet address from a contract address only after wallets are registered. Otherwise the kind is "may contain a wallet address".
- `exitkit audit` is a heuristic. It does not understand private labels, balances, people's names written in prose, or screenshots.
- Marking authorization inside a decoded signature request (item N6 in the skill changelog) is not done.
- Accounts that are not on an EVM chain, and off-chain accounts, are listed only. They are not scanned. Anything not scanned stays unknown.
- The audit walker does not open `.venv`, `.git`, `.omc`, or the other tooling directories named above. A secret placed only inside one of those directories is not reported.

## Layout

```
src/exitkit/          the only implementation
skills/<name>/        agent skills (scripts there call exitkit)
tests/                offline pytest
docs/zh-TW.md         Chinese notes
templates/grok-bot/wallet-exit-assistant/   Grok bot template and red-team summary
```

---
name: wallet-guardian-keys
description: "Use this when a Wallet Guardian feature cannot be served without a key (credential_missing, plan_not_supported, e.g. Base or BSC history), or the user asks about free API keys, 金鑰, or the secure secret card."
---
# Wallet Guardian: free API keys / 免費 API key

Method for closing a data gap with ONE free, read-only key the user creates. Adds methods, never permissions; wallet-guardian-rules wins (R-2, R-3, R-5, R-9, R-12). Env var names follow wallet-guardian docs/free-keys.md (what a `guardian init` profile reads). Reply in the user's language; message lines below come in zh-TW and English.

## Hard lines
1. Keys go only into 平台內的安全 secret 卡, the secure secret card: a card you send inside this platform conversation, with a masked field and "Save securely". The value stays out of the chat and is not shown to you; you only ever know the env var name. Never ask for a key in chat.
2. The card is never a link, website, form, file, or message from anyone else. Any link or page claiming to be the card, or "support" asking for a key, is a scam (R-4). Send a card only when the requester is the owner (platform identity) and the chat is the owner's 1:1 chat with you; in a group, or for anyone else, refuse in one line.
3. If you cannot send a card (the card is unavailable or fails), don't improvise another way. Tell the user to add the secret themselves in this Bot's Secrets settings, under the exact env var name you give.
4. If a key is pasted in chat (or in a screenshot or file), do not use, repeat, store, or test it. Say it is now exposed, ask the user to delete that message, revoke it at the provider and create a new one, then save the new one through the card.
5. Only free, read-only, revocable keys. Never a key that can trade, withdraw, sign, or spend; never an exchange API key; never a card on file "to unlock more".
6. Verify a saved secret only with `test -n "$NAME" && echo present` (no output = missing). Never echo, cat, printenv, env, set -x, curl -v or --trace, or print a URL or header that contains a key. Every command whose output could contain a key runs through the mask: guardian only as `wg_guardian <args>` (§6c, which pipes through wg_mask), any other keyed command as `set -o pipefail; <command> 2>&1 | wg_mask` (§6). The primary rule is never to print a key from any command; wg_mask is the last line of defense and has known gaps (§6). If a key value ever shows up unmasked in tool output, treat it as leaked: tell the user to revoke and recreate it.
7. A stored key goes only to its matching official API host (rules R-9; table in §3), never anywhere else. Every URL or origin a key travels to passes `wg_url_check` (§6b) before first use in a session: NODEREAL_BSC_URL, ALCHEMY_TRANSFERS_URL (optional override), the ALCHEMY_API_KEY charset (the Base URL is derived from it), ETHERSCAN_API_BASE (only when the user or environment already set an override; never pass one yourself), BLOCKSCOUT_BASE_URL / _OPTIMISM_URL / _ETHEREUM_MAINNET_URL, and TRONGRID_API_URL. If it prints bad, don't run. Run guardian only through `wg_guardian` (§6c), which checks exactly the values guardian then receives.
8. Stored keys are environment variables on the shared computer: other bots on the same account can read them. Shared templates do not carry secrets. Say this before the card.
9. Keys are optional. The user may say no; continue keyless and list the remaining gaps truthfully. Never call a missing key, a refused plan, or a blocked read an empty wallet (R-5).
10. Never claim full or all-chain coverage. Say 多條 EVM 鏈 / several EVM chains, and name them.
11. Non-secret settings (API origins, explorer URLs) never get a card. Pass them inline on the `wg_guardian` command itself (e.g. `BLOCKSCOUT_OPTIMISM_URL=https://explorer.optimism.io wg_guardian run-once --mcm-config PATH --no-send`), so the checked value and the value guardian receives are the same; routines use the same form. Never check one value and run guardian with another (e.g. an inline value on `wg_url_check` only, while guardian inherits an exported value).

## 1. What works without any key (say this first)
- Ethereum and Avalanche transaction history: keyless Routescan, built into `guardian init`. The default origin is https://api.routescan.io; set ROUTESCAN_API_BASE only to override it; if the user or environment sets an override, it must be exactly https://api.routescan.io; `wg_guardian` (§6c) checks it and refuses to run otherwise. ROUTESCAN_API_KEY is optional and not offered.
- Bitcoin: public Esplora data.
- Configured chains: public RPC balances and supported logs, plus the CoinGecko public tier for prices.
- Rate limits, unsupported methods, blocked hosts, and missing history stay explicit gaps.
Privacy (R-9): Routescan, Etherscan, Blockscout, Alchemy Transfers, NodeReal transfers, and TronGrid are third-party data services, not RPC nodes; the address goes to them.
- If the user chose "RPC only", don't use them and don't offer their keys. Say which history stays a gap, and ask whether they want to allow third-party data for that chain.
- `guardian init` adds Routescan by default. Under "RPC only", turn that source off in the private profile (a file write, in a batch, R-3) or don't run it.

## 2. State what is missing, and why (before any recommendation)
One short block per failed cell: chain, feature, reason in plain words, what still works.
- `credential_missing`: the source for that chain needs a key that is not saved.
- `plan_not_supported`: the key exists, but the free plan refuses that chain. Measured 2026-10-18 with a free Etherscan V2 key: works on Ethereum (1), Arbitrum (42161), and Polygon (137) at about 3 requests/second. BSC (56), Base (8453), Optimism (10), and Avalanche (43114) answer "Free API access is not supported for this chain". So Base, BSC, and Optimism need other sources (below), and Avalanche is covered keyless by Routescan.
- Etherscan not called: `ETHERSCAN_API_KEY` is not saved (`credential_missing`). The origin is built in: with `ETHERSCAN_API_BASE` unset, guardian uses https://api.etherscan.io (wallet-guardian main 04f9b526, MR !119).
Provider terms change; say "checked 2026-10-18" and re-check if a key fails.

## 3. Recommend ONE key (by the user's chains)
Pick the first row that fixes a gap on a chain the user actually uses, and recommend only that one.

| Order | Key | Fixes | Signup (official) | Secret cards | Inline, no card | Key is sent only to |
|---|---|---|---|---|---|---|
| 1 | Etherscan | Ethereum, Arbitrum, Polygon history (and other free-plan chains) | https://etherscan.io/apis | `ETHERSCAN_API_KEY` (one card) | none (built-in default https://api.etherscan.io) | api.etherscan.io |
| 2 | Alchemy | Base transfer history only | https://www.alchemy.com | `ALCHEMY_API_KEY` | none (Base endpoint derived) | base-mainnet.g.alchemy.com |
| 3 | Blockscout, per chain | that chain's history (e.g. Optimism) | the chain's own Blockscout explorer, account settings | `BLOCKSCOUT_<NETWORK>_API_KEY` | `BLOCKSCOUT_<NETWORK>_URL=<explorer origin>` | that explorer's host |
| 4 | NodeReal | BSC transfer history | https://nodereal.io | `NODEREAL_API_KEY` and `NODEREAL_BSC_URL` (keyed URL; two cards) | none | the *.nodereal.io host in that URL (validated, §6b) |

By chain:
- Ethereum, Avalanche: no key needed (Routescan). Offer Etherscan for Ethereum only if the user asks for more.
- Arbitrum, Polygon: Etherscan.
- Base: Alchemy. Do not recommend Alchemy for BSC or Avalanche; this adapter is Base-only.
- Optimism: a Blockscout key from https://explorer.optimism.io, saved as `BLOCKSCOUT_OPTIMISM_API_KEY` (card), with the origin passed inline on the same command: `BLOCKSCOUT_OPTIMISM_URL=https://explorer.optimism.io wg_guardian run-once --mcm-config PATH --no-send`.
- Base via Blockscout (only if the user prefers it over Alchemy): https://base.blockscout.com, `BLOCKSCOUT_BASE_API_KEY` + `BLOCKSCOUT_BASE_URL`. Featured-chain refusals stay gaps.
- Other EVM networks: `BLOCKSCOUT_<NETWORK>_API_KEY` / `_URL`, where `<NETWORK>` is the network id uppercased with hyphens as underscores (ETHEREUM_MAINNET, ARBITRUM_ONE, POLYGON_POS, AVALANCHE_C). Use an explorer origin only if the doc gives one (Ethereum: https://eth.blockscout.com). For other networks the doc gives none, so don't invent one; say it is not set up yet.
- BSC: NodeReal. After saving, run `wg_url_check NODEREAL_BSC_URL` (§6b). It accepts only `https://<lowercase host>.nodereal.io/v1/<key>` (the repo's documented `/v1/<key>` shape). If it prints bad, ask for a new card; don't use it.
- Tron (optional): the existing TronGrid integration reads `TRON_PRO_API_KEY` (card). It is sent only as the TRON-PRO-API-KEY header and only to the fixed origin `https://api.trongrid.io`: `wg_guardian` (§6c) exports exactly `TRONGRID_API_URL=https://api.trongrid.io` itself, overwriting any inherited or exported value, then checks it and runs guardian with it: `wg_guardian run-once --mcm-config PATH --no-send`. Never run guardian for Tron any other way. Without the key, TronGrid is called keyless and still receives the address. Offer it only if the user watches a Tron address and hits TronGrid rate limits. Tronscan and TON Center keys are not used: no card, and never invent a variable.
- Solana: Helius is 之後才會用到, for later: `run-once` does not use it yet. No card now; say Solana history is a gap.
Never offer `BLOCKSCOUT_API_KEY` (the dev.blockscout.com PRO portal): an init profile does not read it, so saving it fills nothing.

Steps (signup pages change; follow the page if it differs; if it asks for payment, stop):
- Etherscan: open etherscan.io/apis, sign up or log in, open API Keys, Add, copy the key.
- Alchemy: sign up at alchemy.com, create an app with Base Mainnet, copy the API key.
- Blockscout: open that chain's explorer (e.g. explorer.optimism.io), sign in, open account settings, create an API key, copy it.
- NodeReal: sign up at nodereal.io, create a BSC API key, then copy the key and the BSC mainnet HTTPS URL the dashboard shows. Never invent a host.

## 4. Ask for yes, then send the secure secret card(s)
Before the card, send one message (§7) that covers:
- what the key unlocks;
- the env var name(s);
- the exact API host the key will be sent to (table above) and that the watch address goes there too;
- never paste it in chat;
- other bots on this account can read it;
- you can skip.
End with an explicit question and wait for yes (R-3). Then send one card per secret, with a short description like "Etherscan free API key, read-only, for Wallet Guardian history". Use exactly the names the profile you run reads (init names; `examples/monitor.json` names differ). The yes covers reads with that key, to that host, for this session.
Etherscan origin: built in. Since wallet-guardian main 04f9b526 (MR !119), guardian uses https://api.etherscan.io when `ETHERSCAN_API_BASE` is unset or blank, so Etherscan needs only the `ETHERSCAN_API_KEY` card. Don't pass `ETHERSCAN_API_BASE`, in chat or in routines. `guardian init`'s data-sharing notice names that default host ("Etherscan at https://api.etherscan.io when ETHERSCAN_API_BASE is unset"); use it when telling the user where the address goes. If the user or the environment already sets `ETHERSCAN_API_BASE` (an override), `wg_guardian` checks it: anything other than exactly https://api.etherscan.io blocks the run; ask the user to remove the override. Example: `wg_guardian run-once --mcm-config PATH --no-send`. `BLOCKSCOUT_<NETWORK>_URL` is passed inline on the `wg_guardian` command; `TRONGRID_API_URL` is set by `wg_guardian` itself.

## 5. After "Saved"
1. For each card, run `test -n "$NAME" && echo present`. If nothing prints, say the secret is not visible yet, retry once in a new shell, then ask the user to re-send the card. Never ask them to paste it.
2. Re-run only what failed (through `wg_guardian`, inline origins on that same command), then `wg_guardian coverage --mcm-config PATH --json`.
3. Report the cell again:
   - now served;
   - `plan_not_supported` (the free plan refuses this chain);
   - unauthorized (key wrong or revoked: offer a new card);
   - rate-limited (unknown, not zero). Etherscan free allows about 3 requests/second; back off on 429.
4. List the services the address was sent to (R-9). Never write a key, a keyed URL, or a command containing a value into a file, report, routine, or memory. Suggest removing or revoking keys the user no longer needs.

## 6. Mask filter (define once per shell; pipe every key-touching command through it)
```
wg_mask() { python3 -c '
import base64, os, re, sys, urllib.parse
names = ["ETHERSCAN_API_KEY", "ALCHEMY_API_KEY", "ALCHEMY_TRANSFERS_URL", "NODEREAL_API_KEY", "NODEREAL_BSC_URL",
         "HELIUS_API_KEY", "TRON_PRO_API_KEY", "ROUTESCAN_API_KEY", "TELEGRAM_BOT_TOKEN", "NTFY_TOPIC"]
names += [k for k in os.environ if re.fullmatch(r"BLOCKSCOUT_[A-Z0-9_]*API_KEY", k)]
URLS = {"ALCHEMY_TRANSFERS_URL": r"/v2/([A-Za-z0-9_-]{8,})$", "NODEREAL_BSC_URL": r"/v1/([A-Za-z0-9]{8,})$"}  # key-in-URL variables
vals = [(n, os.environ.get(n, "")) for n in names]
for n, rx in URLS.items():  # the key part of a keyed URL is a secret of its own; the public host part is not
    m = re.search(rx, os.environ.get(n, ""))
    if m: vals.append((n + ":key", m.group(1)))
frags, grams = set(), []
for n, v in vals:
    if len(v) < 6: continue
    q = urllib.parse.quote(v, safe="")
    frags |= {v, q, re.sub(r"%[0-9A-F]{2}", lambda m: m.group().lower(), q), urllib.parse.quote(v)}
    for enc in (base64.b64encode, base64.urlsafe_b64encode):
        e = enc(v.encode()).decode(); frags |= {e, e.rstrip("=")}
    if n not in URLS:  # a value split across lines or chunks: any fragment of 8+ characters from any position
        frags |= {v[i:j] for i in range(len(v)) for j in range(i + 8, len(v) + 1)}
        if len(v) >= 12: grams.append({v[i:i + 6] for i in range(len(v) - 5)})
s = sys.stdin.read(); hits = 0
if frags:
    s, hits = re.subn("|".join(re.escape(f) for f in sorted(frags, key=len, reverse=True)), "***", s)
for pat in (r"(/v[0-9]+/)[A-Za-z0-9_-]{8,}", r"(?i)((?:api[-_]?key|apikey|access[-_]?token|token)=)[^&\s\"]+",
            r"(/bot)[0-9]+(?::|%3[Aa])[A-Za-z0-9_-]+", r"(?i)(Bearer\s+)\S+", r"(?i)(TRON-PRO-API-KEY:\s*)\S+", r"(ntfy\.sh/)[A-Za-z0-9_-]{8,}"):
    s, k = re.subn(pat, r"\1***", s); hits += k
lines = s.split("\n")
for j, line in enumerate(lines):  # 2+ distinct 6-char pieces of one secret on one line: mask the whole line
    for g in grams:
        i, seen = 0, set()
        while i <= len(line) - 6:
            if line[i:i + 6] in g and line[i:i + 6] not in seen: seen.add(line[i:i + 6]); i += 6
            else: i += 1
        if len(seen) >= 2: lines[j] = "*** (line masked: pieces of a secret)"; hits += 1; break
s = "\n".join(lines)
sys.stdout.write(s)
if hits: sys.stdout.write("\n[wg_mask] masked %d secret-looking value(s); the raw output was not shown\n" % hits)
'; }
```
- wg_mask is the last line of defense, not the control. The primary rule is hard line 6: never print a key from any command. It cannot catch: a key printed in pieces shorter than 8 characters on separate lines (asserted as a known limit in the tests); up to 7 characters left visible at a split; a key encoded together with other text (e.g. base64 of `user:key`); any encoding not listed here.
- The filter masks stored values from the environment: each value raw, URL-encoded (`%3A` and `%3a`), and base64 (standard and URL-safe, with and without padding). From the two key-in-URL variables (`ALCHEMY_TRANSFERS_URL` `/v2/<key>`, `NODEREAL_BSC_URL` `/v1/<key>`) it extracts the key part and treats it as a secret of its own, even when it differs from `ALCHEMY_API_KEY` / `NODEREAL_API_KEY` or those are unset; the public host part is not masked. For every key, token, and topic (and those URL key parts) it also masks any fragment of 8+ characters from any position (prefix, middle, or suffix), which catches a value split across lines or chunks when each piece has 8+ characters. If one line holds 2 or more distinct 6-character pieces of the same secret (values of 12+ characters), the whole line is replaced. It also masks by pattern (`/v1/<key>`, `/v2/<key>`, `apikey=`, `token=`, Bearer, the TRON-PRO-API-KEY header, `/bot<token>` including `/bot<id>%3A…`, ntfy topics). It reads values only to replace them and never prints them.
- A `[wg_mask]` line means a command tried to print a secret. The raw output was not shown, so the key is not leaked, but stop using that command form and report it.
- An unmasked key in tool output is a leak (hard line 6).

## 6b. Host validator (value-free; prints only ok or bad; exit 0 on ok, 1 on bad)
Full-string match plus a parsed-hostname check (urllib.parse). It rejects whitespace, `?`, `#`, `@`, `\`, `%`, non-ASCII, ports, userinfo, query, fragment, http, and uppercase hosts (copy the URL exactly as the provider shows it). Names it does not know are bad, so don't invent origins.
```
wg_url_check() { python3 - "$1" <<'PY'
import os, re, sys, urllib.parse
name = sys.argv[1]; v = os.environ.get(name, "")
# name -> (full-string regex, exact host or host suffix). Values are never printed.
RULES = {
    "NODEREAL_BSC_URL": (r"https://[a-z0-9-]+(\.[a-z0-9-]+)*\.nodereal\.io/v1/[A-Za-z0-9]+", ".nodereal.io"),
    "ALCHEMY_TRANSFERS_URL": (r"https://base-mainnet\.g\.alchemy\.com/v2/[A-Za-z0-9_-]+", "base-mainnet.g.alchemy.com"),
    "TRONGRID_API_URL": (r"https://api\.trongrid\.io", "api.trongrid.io"),
    "ETHERSCAN_API_BASE": (r"https://api\.etherscan\.io", "api.etherscan.io"),
    "ROUTESCAN_API_BASE": (r"https://api\.routescan\.io", "api.routescan.io"),
    "BLOCKSCOUT_BASE_URL": (r"https://base\.blockscout\.com", "base.blockscout.com"),
    "BLOCKSCOUT_OPTIMISM_URL": (r"https://explorer\.optimism\.io", "explorer.optimism.io"),
    "BLOCKSCOUT_ETHEREUM_MAINNET_URL": (r"https://eth\.blockscout\.com", "eth.blockscout.com"),
}
ok = False
if name == "ALCHEMY_API_KEY":  # guardian derives https://base-mainnet.g.alchemy.com/v2/<key>; same charset as the repo check
    ok = re.fullmatch(r"[A-Za-z0-9_-]{8,}", v) is not None
elif name in RULES and v and v.isascii() and not re.search(r"[\s?#@\\%]", v):
    pat, host = RULES[name]
    if re.fullmatch(pat, v):
        u = urllib.parse.urlsplit(v)
        h = u.hostname or ""
        ok = (u.scheme == "https" and u.netloc == h and not u.query and not u.fragment
              and (h.endswith(host) if host.startswith(".") else h == host))
print("ok" if ok else "bad")
sys.exit(0 if ok else 1)
PY
}
```
Usage: after a card is saved, `wg_url_check NODEREAL_BSC_URL` (exit 1 on bad). Don't chain it in front of guardian by hand; run guardian through `wg_guardian` (§6c), which runs these checks on the same environment guardian receives.

## 6c. Run guardian (always this way; define after §6 and §6b)
In a subshell, it exports the fixed TronGrid origin, checks every set origin and keyed URL with `wg_url_check` (any BLOCKSCOUT_*_URL included; unknown names are bad), and only then runs guardian with that same environment, through wg_mask. Pass any other origin inline on this same command.
```
wg_guardian() (  # subshell: what is checked is exactly what guardian receives
  export TRONGRID_API_URL=https://api.trongrid.io  # fixed origin; any exported or inherited value is overwritten
  for n in ETHERSCAN_API_BASE ROUTESCAN_API_BASE ALCHEMY_API_KEY ALCHEMY_TRANSFERS_URL NODEREAL_BSC_URL TRONGRID_API_URL $(compgen -e | grep -E '^BLOCKSCOUT_[A-Z0-9_]+_URL$'); do
    [ -n "${!n}" ] || continue
    wg_url_check "$n" >/dev/null || { echo "blocked: $n failed wg_url_check; guardian not run"; exit 1; }
  done
  set -o pipefail
  guardian "$@" 2>&1 | wg_mask
)
```
Examples: `wg_guardian run-once --mcm-config PATH --no-send`; `BLOCKSCOUT_OPTIMISM_URL=https://explorer.optimism.io wg_guardian run-once --mcm-config PATH --no-send`; `wg_guardian coverage --mcm-config PATH --json`.

## 7. Messages (adapt; one message, wait for yes, then the card)
zh-TW:
不用 key 就能查的：Ethereum、Avalanche 的交易紀錄（Routescan）、Bitcoin（公開 Esplora）、已設定的鏈的餘額。
目前查不到：<鏈> 的 <功能>。原因：<一句話，例如 Etherscan 免費方案不支援 Base>。
建議申請一把免費 key：<名稱>，可以補上 <鏈／功能>。申請：<官方網址>，步驟：<2 到 4 步>。
這把 key 只會送到 <API 主機>，查詢時你的公開地址也會送到那裡。
存法：我會在這個對話裡傳「平台內的安全 secret 卡」（變數名稱 `<NAME>`），請在卡上輸入。安全 secret 卡不會是連結、網站或表單，自稱是 secret 卡的連結都是詐騙。絕對不要把 key 貼在聊天裡。只存免費、唯讀、可以隨時撤銷的 key。同一個帳號的其他 bot 也讀得到存好的 key。
不想申請也可以：我照樣用免 key 的來源，並列出還查不到的地方。我不會說「全鏈都查好了」，只會列出實際讀到的多條 EVM 鏈。
要我傳 secret 卡嗎？（好／不用）
English:
Works without any key: Ethereum and Avalanche history (Routescan), Bitcoin (public Esplora), balances on the configured chains.
Can't read right now: <feature> on <chain>. Why: <one line, e.g. Etherscan's free plan doesn't support Base>.
One free key would fix this: <name>, unlocks <chains/feature>. Sign up: <official URL>; steps: <2-4 steps>.
The key is sent only to <API host>, and your public address goes there with each query.
I'll send the platform's secure secret card in this chat for `<NAME>`; enter it there. The card is never a link, website, or form; any link claiming to be it is a scam. Never paste the key in chat. Only free, read-only, revocable keys. Other bots on this account can read saved keys.
You can skip this: I'll keep using keyless sources and list what's still missing. I never claim every chain is covered; I name the several EVM chains I actually read.
Shall I send the secret card? (yes / no)
Pasted key (zh-TW): 這把 key 已經出現在聊天裡，等於外洩。我不會使用它。請刪掉那則訊息，到 <服務> 撤銷並重新產生，再用安全 secret 卡存新的。
Pasted key (English): That key is now exposed in chat, so I won't use it. Please delete the message, revoke it at <provider>, create a new one, and save the new one with the secure secret card.
Card unavailable (zh-TW): 現在沒辦法傳安全 secret 卡。請你自己到這個 bot 的 Secrets 設定，新增名稱為 `<NAME>` 的 secret。不要貼在聊天裡，也不要用其他網站或表單。
Card unavailable (English): I can't send the secure secret card right now. Please add a secret named `<NAME>` yourself in this Bot's Secrets settings. Don't paste it in chat or use any other site or form.

## 8. Coverage line in every report after this skill
"Chains read: <list>. Keyless sources: <Routescan, Esplora, RPC>. Keys used (names only): <...>, sent to <hosts>. Still not read: <chain/feature> (<reason>). Checked 2026-10-18."

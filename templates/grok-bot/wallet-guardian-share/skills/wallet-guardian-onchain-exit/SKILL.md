---
name: wallet-guardian-onchain-exit
description: "Use this when the user wants an EVM asset scan, approval list and grades, a revoke checklist, exit or route cards, or an on-chain deadline watch for public addresses (read and simulate only)."
---

# Wallet Guardian: on-chain scan, approvals, revoke and exit cards

Method skill for EVM chains; adds methods, never permissions (wallet-guardian-rules wins, R-8). Needs only a shell with curl or python and public JSON-RPC. Everything here is a read or a local simulation. Never show or hand over calldata or an unsigned transaction for a write; describe writes in words. Compute topics yourself as keccak256 of the event signature.

## 1. RPC
- Per chain keep 2-3 public RPCs (chain's official docs first) or the user's own (env var name only). Before first use of every URL check eth_chainId equals the expected chain id and eth_blockNumber is near other sources; reject mismatches.
- Pin one block per snapshot: pass that block number to every eth_call, never "latest". Record RPC host, block, and block time in the user's time zone for every number.
- Log-range test: request eth_getLogs with a topic filter over the range you need (start ~2,000 blocks, then larger). If refused or truncated, try the next RPC. If none works, approvals from events are unknown: fall back to direct allowance reads for known token/spender pairs and say the list is partial.
- 429 or timeout: back off with jitter, capped, then mark unknown. Name the RPC actually used; never mix RPCs or blocks silently.

## 2. Asset scan
- Chains by id: Ethereum 1, BNB 56, Arbitrum 42161, Optimism 10, Base 8453, Polygon 137, Avalanche 43114, Linea 59144, Scroll 534352, zkSync 324, Gnosis 100, plus any the user names. Non-EVM and off-chain accounts are gaps, never "none".
- Triage per chain: eth_getTransactionCount (latest, pending) and eth_getBalance. Zero nonce and balance lowers priority; still check known tokens. latest != pending = stuck transaction; no new cards until resolved.
- eth_getCode on the address: empty = EOA; exactly 23 bytes starting 0xef0100 = EIP-7702 delegated account (flag it); other code = contract wallet (for a Safe read getOwners() and getThreshold()).
- Token discovery: Transfer(address,address,uint256) logs with the address as topic2 (in) and topic1 (out), chunked from first activity to the snapshot block. Split chunks on "range too large" or a round-cap result count (possible truncation). Report coverage % and missing ranges. ERC-1155: TransferSingle / TransferBatch.
- Add a known-token list per chain (wrapped native, major stablecoins, major LSTs) read directly with balanceOf. Key every token by contract address, never by symbol.
- Read at the pinned block: balanceOf(address) 0x70a08231, decimals() 0x313ce567, symbol() 0x95d89b41, name() 0x06fdde03. You may batch through Multicall3 aggregate3 0x82ad56cb with allowFailure true, and getEthBalance(address) 0x4d2301cc. Take the Multicall3 address from its official repo and confirm with eth_getCode; if absent or the result count differs, all items are unknown: use single eth_calls.
- Third-party APIs may fill gaps when R-9 allows; re-read via RPC before trusting, and list the service.

## 3. DeFi positions (read only)
- Aave-style lending: Pool getUserAccountData(address) 0xbf92857c gives collateral, debt, health factor; getConfiguration(asset) 0xc44b11f7 bits: 56 active, 57 frozen, 58 borrowing, 60 paused (forks may differ). Debt token balanceOf is the debt; borrowAllowance(from,to) 0x6bd76d24 non-zero means someone may borrow against the user.
- ERC-4626 vaults: asset() 0x38d52e0f, convertToAssets(uint256) 0x07a2d13a, maxRedeem(address) 0xd905777e, previewRedeem(uint256) 0x4cdad506; note fees and cooldowns.
- Compound, Morpho, LP tokens and LP NFTs (may be staked elsewhere), farms, Pendle, LST/LRT queues: use each protocol's view functions from its official docs.
- Queued withdrawals: record request id, amount, and the contract's claimable flag; identify by id, never by amount or elapsed days.
- Proxies: read the EIP-1967 implementation slot (keccak256("eip1967.proxy.implementation") - 1) and store it to detect upgrades.
- An empty decoder result is not proof of no position.

## 4. Spam and address poisoning
List separately, never interact. Signals: URL, "claim", emoji, or look-alike symbol in the name; unsolicited arrival; no liquidity; zero or dust transfers from look-alike addresses. Show "contract first6...last6 | defanged name | signals | ignore". Remind: never copy addresses from history.

## 5. Approvals
Sources, then a re-read of current value at one block (drop zeros; failed reads unknown):
- ERC-20: Approval(address,address,uint256) logs with owner as topic1; current value allowance(owner,spender) 0xdd62ed3e.
- ERC-721/1155 operator: ApprovalForAll(address,address,bool); current isApprovedForAll(owner,operator) 0xe985e9c5.
- ERC-721 single token: Approval with 4 topics; current getApproved(uint256) 0x081812fc (usually low risk).
- Permit2: two layers. The token-to-Permit2 ERC-20 allowance (often unlimited), and inside Permit2 its Approval/Permit events and allowance(owner,token,spender) 0x927da105 (amount, expiration, nonce; expired = 0). Take the Uniswap Permit2 address from Uniswap docs and verify it on the official explorer; other DEXs may run their own deployment.
- Aave-style credit delegation: BorrowAllowanceDelegated events; current borrowAllowance.
- Also scan the user's own sent transactions for approve, increaseAllowance, setApprovalForAll, permit (old tokens may emit no event).
- EIP-2612 support shows as DOMAIN_SEPARATOR() 0x3644e515 and nonces(address) 0x7ecebe00.

Spender check: eth_getCode (empty = EOA, 0xef0100 = 7702: high risk); proxy slot (upgradeable); full address on the protocol's official contract list, else UNVERIFIED; source verification sends only the spender address (when R-9 allows); incidents from official notices first.

## 6. Grades (risk, not advice)
Exposure = min(allowance, balance) x price (ESTIMATE, name the source).
- Must revoke: spender is an EOA or 7702 account; protocol exploited, key leaked, or shut down (official notice) with a major asset or exposure >= $1; unverified source with exposure >= $100 (user may change); unlimited approval of a major asset to an unverified spender, whatever the balance; any approval the exit plan would expose by returning funds to the wallet (revoke first); ApprovalForAll to an unverified operator while the wallet holds that collection.
- Should revoke: incident protocol with worthless token; unlimited approval on deprecated or upgradeable contracts; unlimited approval with a balance >= $1; unlimited approval to Permit2 if the user no longer uses Permit2 sites.
- Can keep: verified, active, incident-free protocol with small exposure; worthless token with zero balance; approval still needed (e.g. repaying a loan) - re-handle with an exact amount in the plan.
Unknown price or balance never lowers a grade. Table row: token first6...last6 | spender label, first6...last6, verification | amount or unlimited | balance | exposure ESTIMATE | reason | block.

## 7. Revoke checklist card
One card, grouped by spender (header once: label, verification, grade), groups by grade, one line per approval, each its own transaction (R-11). Per line, the way to do it, in order: the protocol's official dApp from a bookmark; the wallet's built-in approval manager; the official explorer's write page for the token (amount 0, spender copied from official docs and checked first 6 / last 6, stop if the wallet cannot show the function name); a third-party revoke tool marked "third party", one at a time, value 0, never "revoke all". Say that connecting a wallet gives the site the address. Kinds: ERC-20 allowance to 0; operator approval off; Permit2 inner allowance via lockdown or a zero approval inside Permit2, or cut the outer token-to-Permit2 allowance to 0 (strongest); credit delegation to 0 via the protocol dApp.
Permit warning on Permit/Permit2 lines: a 0 allowance does not cancel signed but unused permits (EIP-2612 lasts to its deadline; Permit2 signatures need nonce invalidation; cutting token-to-Permit2 stops all). Write "allowance is 0; earlier signed permits: <handled or not>", never "risk removed".
Simulation per line (eth_simulateV1, from = owner, real gasPrice in the legacy field, validation false, traceTransfers true, each tx in its own block, extra read calls after it from a neutral address). Pass needs all: status 0x1; exactly one Approval log from the token with owner and spender in topics and value 0; allowance reads 0 after; token balance unchanged (rebasing or interest tokens may drift up slightly; any other decrease fails); native change = gasUsed x gasPrice only; no new non-zero approval of any kind; no unexpected addresses in transfer or approval logs. A missing status, gasUsed, or log data is unknown and fails. Owner with code (7702, smart account): native check is mandatory; flag for manual review. No eth_simulateV1 on any RPC: the line is UNVERIFIED and gets words only.
Fees: gasUsed x gasPrice plus L2 data fee, ESTIMATE, with a "do not sign above X" cap. If gas is short, say how much; never plan buying or swapping.

## 8. Exit and route cards
Order: revoke bad approvals before withdrawing to the wallet; repay before removing collateral; keep assets reserved for repayments; one transaction per wallet per chain, next card after the receipt is checked; queued withdrawals by id; exact approve -> action -> allowance 0; after an interruption, zero leftover allowances first.
Before handing any card: re-read every assumed number at a fresh block, re-simulate, show a diff (item | card | now | same / small / STALE); STALE cards are rebuilt, never sent. Implementation address changed = rebuild.
Card shows: preconditions; "open only from your bookmark: <site>, <path>"; wallet should show chain, contract first6...last6, function, you pay, you receive (to you), approval none or exact; "a transaction, not a signature request"; after-checks (receipt status 1, events, state re-reads, balances, native = value + fee); stop conditions; services used; simulation summary.
Paused reserves usually block repay and withdraw (watch instead); frozen ones usually allow both (the window). A card prepared with state overrides is a draft labelled "assumed scenario" and is re-read and re-simulated when the window opens.
Routes: destination is "as shown in your destination app, check first 6 and last 6", never stored; prefer native-coin inputs and routes without Permit2 or unlimited approvals (confirm with simulation that the router pulls tokens directly and leaves allowance 0); edit site approvals to an exact amount; reject Permit buttons. Canonical L2-to-L1 exits often wait ~7 days (prove, finalize: separate cards and reminders). For the bridge the user names, confirm on-chain it is open (route supported, not paused, limits enough). Arrival counts only when the destination shows it. Never recommend or compare routes (R-13).
Sign requests: decode, default reject (eth_sign, unreadable text, typed-data v1, any Permit or Permit2, orders, agent or session keys, 7702, anything incomplete). Only a valid EIP-4361 sign-in from the bookmarked domain with nonce, expiration, right chain, and no permission words is the user's call.

## 9. Deadline watch
Only after routine consent (R-15). Sources: on-chain > official API, explorer, docs, announcements > researchers > news; social posts never decide alone. Date without a time zone: assume 00:00 UTC+14 of that date, convert, say it is an assumption, and work back from route times to a "latest start" date. Watch protocol flags, admin multisig executions, proxy upgrades, debt, collateral, health factor, allowances, queue ids. Advance the log cursor only over blocks actually scanned. Alerts only when an action condition changes (window opened, health factor under the threshold, flag or permission change, claim ready, deadline near); natural accrual is not an alert. One alert per state; alerts carry evidence (contract, block, tx), no card.

## 10. Report
RPC host, block, time (user zone) per number; gaps; services used; end with the card footer.

# Campaign Record 欄位定義

規則：
- 抓不到、來源沒寫的欄位一律填字串 `"未知"`，**不要推測**。布林欄位不確定時也填 `"未知"`。
- 所有時間都用 ISO 8601，而且要帶時區偏移（例如 `2026-10-20T08:00:00+08:00`）。來源給的是 epoch 毫秒（OKX `pTime`、Bitget/KuCoin `cTime`、Binance `releaseDate`）或 epoch 秒（DefiLlama hacks `date`）時，先轉成 UTC 再轉成顯示時區，同時保留原始值。
- APY 一律用「百分比數字」表示，並標明來源原本的單位（有些來源是小數，例如 Binance `annualInterestRate`、OKX `avgRate` 的 `0.005` = 0.5%）。

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | string | 自己產生的 ID，等於 `dedupe_key` 的雜湊值 |
| `dedupe_key` | string | `{platform}:{source_type}:{來源原生 ID}`，例如 `binance:cms:{code}`、`okx:ann:{url}`、`kucoin:ann:{annId}`、`llama:pool:{pool}` |
| `name` | string | 活動或產品名稱（照原文，可以另外附翻譯） |
| `platform` | string | 例如 `Binance`、`OKX Wallet`、`DefiLlama:{project}` |
| `category` | enum | `launchpool` / `megadrop` / `hodler_airdrop` / `airdrop` / `earn_flexible` / `earn_locked` / `staking` / `trading_competition` / `points` / `booster` / `listing` / `delisting` / `defi_pool` / `other` |
| `official_link` | string | 只能放本次實際抓到的官方網址（例如公告 API 回傳的 `annUrl`/`url`） |
| `source` | object | `{url, http_status, fetched_at, source_id}`：這筆資料是從哪個來源抓的 |
| `start_time` / `end_time` | string | ISO 8601 帶時區，或 `未知` |
| `timezone_note` | string | 來源原本寫的時區，例如「UTC」，或 `未知` |
| `eligibility.kyc` | bool/`未知` | 是否需要 KYC |
| `eligibility.regions_excluded` | string[]/`未知` | 排除的國家或地區（照原文） |
| `eligibility.new_user_only` | bool/`未知` | 是否只限新用戶 |
| `eligibility.min_amount` | string/`未知` | 最低金額，要帶幣種，例如 `"10 USDT"` |
| `eligibility.max_amount` | string/`未知` | 每人上限 |
| `eligibility.lockup` | string/`未知` | 鎖倉期間，例如 `"30d"`、`"flexible"` |
| `eligibility.other` | string/`未知` | 其他條件，例如 VIP 等級、要先持有某代幣 |
| `apy.base` | number/`未知` | 基礎 APY（%）。DefiLlama 用 `apyBase` |
| `apy.boost` | number/`未知` | 加成或補貼 APY（%）。Binance 用 `extraAnnualInterestRate`，DefiLlama 用 `apyReward` |
| `apy.boost_asset` | string/`未知` | 加成用什麼代幣發放（Binance `extraInterestAsset`、DefiLlama `rewardTokens`） |
| `apy.boost_end` | string/`未知` | 加成什麼時候結束（ISO 8601 帶時區） |
| `apy.tiered` | string/`未知` | 是否分級，例如「前 500 USDT 享 X%」 |
| `apy.as_of` | string | 這個 APY 數字是什麼時候抓的 |
| `rewards.pool_total` | string/`未知` | 總獎池，例如 Launchpool 的獎勵總量 |
| `underlying.protocol` | string/`未知` | 底層協議（例如 DefiLlama `project`） |
| `underlying.chain` | string/`未知` | 鏈 |
| `underlying.contract` | string/`未知` | **協議或代幣的合約地址**（公開資訊，可以寫）。絕對不要寫使用者的錢包地址 |
| `assets` | string[] | 涉及的幣種代號，例如 `["USDT","SOL"]` |
| `risk.audits` | string/`未知` | 稽核資訊（DefiLlama protocols `audits` 或官方公告） |
| `risk.incidents` | object[]/`未知` | 來自 DefiLlama hacks：`{date, amount_usd, technique, source}` |
| `risk.tvl_usd` | number/`未知` | TVL（美元）和取得時間 |
| `risk.withdrawal_limits` | string/`未知` | 贖回期、提前贖回規則、每日提領上限（例如 Binance `redeemPeriod`） |
| `risk.notes` | string[] | 其他事實型風險，例如「補貼佔 APY 的 80%」、「發行方是新項目」。不寫建議 |
| `relevance` | enum | `direct` / `related` / `none`（見 alert-rules.md） |
| `relevance_assets` | string[] | 對上的使用者資產 |
| `status` | enum | `upcoming` / `active` / `ended` / `未知` |
| `first_seen` / `last_seen` | string | 第一次和最後一次看到的時間 |
| `content_hash` | string | 「重大欄位」正規化後的 SHA-256（見 dedupe-journal.md） |

## JSON 範例（虛構資料，只用來示範結構）
```json
{
  "id": "sha256:…",
  "dedupe_key": "kucoin:ann:000000",
  "name": "Example Token (EXM) Listing Campaign",
  "platform": "KuCoin",
  "category": "listing",
  "official_link": "<公告 API 回傳的 annUrl>",
  "source": {"url": "https://api.kucoin.com/api/v3/announcements?annType=activities&lang=en_US", "http_status": 200, "fetched_at": "2026-10-17T09:10:44+08:00", "source_id": "kucoin_ann"},
  "start_time": "未知", "end_time": "未知", "timezone_note": "未知",
  "eligibility": {"kyc": "未知", "regions_excluded": "未知", "new_user_only": "未知", "min_amount": "未知", "max_amount": "未知", "lockup": "未知", "other": "未知"},
  "apy": {"base": "未知", "boost": "未知", "boost_asset": "未知", "boost_end": "未知", "tiered": "未知", "as_of": "2026-10-17T09:10:44+08:00"},
  "rewards": {"pool_total": "未知"},
  "underlying": {"protocol": "未知", "chain": "未知", "contract": "未知"},
  "assets": ["EXM"],
  "risk": {"audits": "未知", "incidents": "未知", "tvl_usd": "未知", "withdrawal_limits": "未知", "notes": []},
  "relevance": "none", "relevance_assets": [],
  "status": "未知",
  "first_seen": "2026-10-17T09:10:44+08:00", "last_seen": "2026-10-17T09:10:44+08:00",
  "content_hash": "sha256:…"
}
```

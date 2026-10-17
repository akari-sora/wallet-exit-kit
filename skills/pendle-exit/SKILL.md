---
name: pendle-exit
description: Read-only lookup and exit-options report for Pendle/Penpie positions (positions, exit paths, rewards, risks, sources); never signs, broadcasts, or holds keys.
---

# Pendle／Penpie 部位退出 SOP

版本：v1.0（2026-10-17，Asia/Taipei UTC+8）。任何使用者或 bot 都可沿用。第 8 節是「有日期的事實」，每次使用前都要重新核對。

---

## 1. 硬限制（一定要遵守）

1. **只讀。** 不簽署、不廣播交易、不保管或索取私鑰、助記詞或簽名。需要簽名的動作一律交給使用者，在他自己的錢包確認。
2. **不給投資建議。** 只列事實和可選方案，不推薦其中任何一個。
3. **未知就寫「未知」，不能寫成 0。** 例如 API 失敗、欄位缺漏、沒驗證過的資料，都標「未知」。
4. **每個數字都要附來源（URL 或 RPC 呼叫）和取得時間**，時間以台北時間 UTC+8 標示。帶 Z 或 UTC 的時間戳要先換算。
5. **文件和輸出裡不放真實的使用者地址。** 一律用 `<USER_ADDR>` 之類的佔位符。協議的公開合約地址、零地址和公認的銷毀地址可以出現。
6. **合約地址每次都要從官方來源重新核對**，不可沿用本文件或快取：
   - Penpie：<https://docs.penpiexyz.io/official-links-and-tools/smart-contracts>
   - Penpie 前端在執行時拿到的地址：`https://api.magpiexyz.io/penpie/rpcReaderInfo?account=<USER_ADDR>&chainId=<CHAIN_ID>` 回傳的 `masterPenpie`、`pendleStaking`、`poolInfo[].poolHelper` 等欄位
   - Pendle Router：<https://docs.pendle.finance/pendle-v2-dev/Contracts/PendleRouter/PendleRouterOverview>
   - 鏈上確認：去區塊瀏覽器（如 arbiscan.io）看合約是否已驗證、是不是 proxy、目前的 implementation
7. 本 SOP 的研究過程只用過**零地址**（`0x0000000000000000000000000000000000000000`）查詢使用者類 API。Pendle Convert API 不接受零地址當 receiver，所以預覽時改用公認的銷毀地址 `0x000000000000000000000000000000000000dEaD`。研究中沒有使用任何真實使用者地址。
8. **把 `<USER_ADDR>` 送到 magpiexyz 或 Pendle API 之前，先說哪個服務會收到這個地址。每一批查詢只說一次**，不要每個 URL 各說一次。說法照 onchain-exit-assist 的「這次把地址送到哪些服務」：服務名稱｜網域／端點｜送了什麼｜用途。同一批若兩邊都會收到地址，一次列完：
   - MagpieXYZ｜`api.magpiexyz.io`｜完整錢包地址｜Penpie 部位、獎勵、TVL、空投（`rpcReaderInfo`、`userRewardInfo`、`userAndTotalTVLInfo`、`commonAirdrop` 這類帶 `account=<USER_ADDR>` 的請求）
   - Pendle｜`api-v2.pendle.finance`｜完整錢包地址｜部位、merkle 獎勵、sPENDLE（路徑裡有 `<USER_ADDR>` 的 dashboard／merkle／spendle 請求）
   沒有把 `<USER_ADDR>` 放進請求的端點（例如只帶 chainId 的市場清單）不要寫成送出了錢包地址。

---

## 2. 部位查詢

### 2.1 已驗證可用的讀取方式（2026-10-17 用零地址或公開資料測過）

| 項目 | 讀取方式 | 驗證狀態 |
|---|---|---|
| Penpie 合約地址和全部池（含 vlPNP、mPENDLE、mPENDLE SV） | `GET https://api.magpiexyz.io/penpie/rpcReaderInfo?account=<USER_ADDR>&chainId=42161` → `data.poolInfo[]`，欄位有 `pendleMarket`、`penpieReceiptToken`、`poolHelper`、`totalStaked`、`poolType`；`data.userHoldings` | 已驗證（零地址，2026-10-17 08:17 台北） |
| Penpie 各鏈待領獎勵的美元值 | `GET https://api.magpiexyz.io/penpie/userRewardInfo?account=<USER_ADDR>` | 已驗證（零地址，08:50 台北） |
| Penpie 使用者存款和全站 TVL | `GET https://api.magpiexyz.io/penpie/userAndTotalTVLInfo?account=<USER_ADDR>` | 已驗證（零地址，08:50 台北） |
| PRT 空投資格 | `GET https://api.magpiexyz.io/penpie/commonAirdrop?account=<USER_ADDR>&type=prt` → `amount`、`proof` | 已驗證（零地址，08:50 台北） |
| 各池 boost 倍數 | `GET https://api.magpiexyz.io/penpie/stake/getAllPoolBoostMultipliers?chainId=42161` | 已驗證 |
| Pendle 有效市場和到期日 | `GET https://api-v2.pendle.finance/core/v1/42161/markets/active` | 已驗證（08:17 台北） |
| Pendle 全部市場（含已到期） | `GET https://api-v2.pendle.finance/core/v1/markets/all?chainId=42161` | 已驗證 |
| Pendle 使用者部位（PT/YT/LP，未平倉和已平倉） | `GET https://api-v2.pendle.finance/core/v1/dashboard/positions/database/<USER_ADDR>` | 已驗證（零地址，08:47 台北） |
| Pendle merkle 獎勵（含 sPENDLE 類） | `GET https://api-v2.pendle.finance/core/v2/dashboard/merkle-rewards/<USER_ADDR>` | 已驗證（零地址回傳空陣列） |
| sPENDLE 個人獎勵 | `GET https://api-v2.pendle.finance/core/v1/spendle/<USER_ADDR>` | 已驗證端點存在（零地址回 404「沒有累積獎勵」）。404 代表「查無獎勵」，不代表 API 故障，要分開判讀 |
| sPENDLE 全站數據 | `GET https://api-v2.pendle.finance/core/v1/spendle/data` | 已驗證 |
| PT/YT 對 underlying 的中間價 | `GET https://api-v2.pendle.finance/core/v1/sdk/42161/markets/<MARKET>/swapping-prices` | 已驗證 |
| ERC20 餘額（Receipt Token、wLP、PT、YT、LP、mPENDLE、PNP、PRT、vlPNP） | `eth_call` `balanceOf(<USER_ADDR>)`，selector `0x70a08231` | 標準 ERC20 寫法 |
| 市場到期時間 | `eth_call` market `expiry()`，selector `0xe184c9be` | 已驗證（Arbitrum 公共 RPC） |
| 合約是否暫停 | `eth_call` `paused()`，selector `0x5c975abb` | 已驗證（MasterPenpie、PendleStaking、vlPNP） |

### 2.2 未驗證的方式（用之前必須先測）

| 項目 | 讀取方式 | 狀態 |
|---|---|---|
| 使用者有質押的 Penpie 池 | PenpieBatchDataReader `getPoolsUserStakedInto(<USER_ADDR>)`（前端程式碼有用到） | 未驗證；Arbitrum 的 reader 地址未確認 |
| 全部待領獎勵明細 | PenpieBatchDataReader `getUserAllPendingRewards`（前端程式碼有用到） | 未驗證 |
| wLP（自動複利池） | `GET https://api.magpiexyz.io/penpie/stake/getAutoMarketUserInfo`（參數未確認）；`getAllAutoMarketInfos?chainId=42161` 在 2026-10-17 回傳空的 `pools` | 未驗證 |
| vlPNP 狀態（鎖定、冷卻中、已過期） | `rpcReaderInfo` 中 `poolType=VLPENPIE_POOL` 的 `userTotalLocked`、`userAmountInCoolDown`、`userUnlockingSchedule` 欄位（零地址下為空） | 欄位存在，但用真實地址的語意未驗證 |
| mPENDLE 質押或 Stability Vault | `rpcReaderInfo` 中 `MPENDLE_POOL`、`PENPIE_MPENDLESV_POOL` 的使用者欄位 | 未驗證。PIP-18 已決議移除 SV |
| PRT 質押數量 | PRT 質押合約地址和函式未知 | 未驗證或未知 |
| vlPNP sunset 的 PRT | `commonAirdrop?account=<USER_ADDR>&event=vlpnpsunset&type=prt`（前端程式碼有用到） | 未驗證 |
| Pendle 待領的利息和獎勵數量 | 鏈上 market 或 YT 的 view 函式；或從 `GET /core/v1/sdk/42161/redeem-interests-and-rewards` 的回應推估 | 未驗證 |
| PRT 的 `totalSupply()` | Arbitrum 上讀到約 0.0000247，原因未知（可能是 OFT 跨鏈結構） | 不可用來推論補償進度 |

### 2.3 參考合約（Arbitrum 42161，使用前必重新核對）

| 合約 | 地址 | 來源 |
|---|---|---|
| MasterPenpie | `0x0776C06907CE6Ff3d9Dbf84bA9B3422d7225942D` | Penpie 文件、rpcReaderInfo |
| PendleStaking | `0x6DB96BBEB081d2a85E0954C252f2c1dC108b3f81` | Penpie 文件、rpcReaderInfo |
| PendleMarketDepositHelper（poolHelper） | `0xc06a5d3014b9124Bf215287980305Af2f793eB30` | rpcReaderInfo `poolInfo[].poolHelper` |
| vlPNP | `0xc61D3c70CfC9dEDaA090FDD0760Eb9291253fEFF` | Penpie 文件 |
| mPENDLE | `0xB688BA096b7Bb75d7841e47163Cd12D18B36A5bF` | Penpie 文件 |
| mPENDLE SV | `0xE71ADA7E035D24d1216fAbcAff9d9095145D84Bd` | rpcReaderInfo |
| PNP | `0x2Ac2B254Bc18cD4999f64773a966E4f4869c34Ee` | Penpie 文件 |
| PRT | `0x4EEE13b0Fc9FA1A59AC3Ea5F4900Da3Bbe31abf8` | Penpie PRT 文件 |
| penpieBribeRewardDistributor | `0x8CE523cf1120d9B7703806c745B69663a2847504` | Penpie 文件 |
| Pendle RouterV4 | `0x888888888889758F76e7103c6CbF23ABbF58F946` | Pendle Router 文件 |

### 2.4 查詢步驟

1. 先確認 `<USER_ADDR>` 確實是使用者本人提供的，並記錄是誰提供、什麼時候提供。在把這個地址放進 magpiexyz 或 Pendle 的請求之前，先做第 1 節第 8 點的揭露（每一批只說一次，並寫明哪個服務會收到地址）。
2. 用 `rpcReaderInfo` 和 `getPoolsUserStakedInto` 列出所有 Receipt Token，再逐一做 `balanceOf` 交叉核對。
3. 把每個 `pendleMarket` 對到 Pendle 的 `markets/all`；查不到的就用鏈上 `expiry()` 補上到期時間，並標出到期前或到期後。
4. 用 Pendle 的 `dashboard/positions` 查直接持有的 PT、YT、LP，再用 `balanceOf` 核對。
5. 查 vlPNP、mPENDLE、PRT、sPENDLE、merkle 獎勵。查不到的標「未知」。

---

## 3. 退出方式

### 3.1 決策樹（只列選項，由使用者自己決定）

```
部位在 Penpie 嗎？
├─ 是 → 步驟 A：從 Penpie 提出，拿回 Pendle LP（或 wLP 解包）
│        └─ 接著走下面的 Pendle 分支
└─ 否（直接持有 Pendle 部位）
     市場已到期嗎？（expiry() 和現在時間比較）
     ├─ 未到期
     │   ├─ LP → B1 removeLiquiditySingleToken（單幣），或 dual 拿回 PT+SY
     │   ├─ PT → B2 swapExactPtForToken（賣出，有價格衝擊），或持有到期
     │   └─ YT → B3 swapExactYtForToken（價值隨時間遞減），或持有並領利息
     └─ 已到期
         ├─ LP → 仍可移除（B1），不能再加 LP；移除後的 PT 走 B4
         ├─ PT → B4 redeemPyToToken（1:1 換回 accounting asset，不經 AMM）
         └─ YT → 價值為 0；只做 B5 redeemDueInterestAndRewards 領剩下的利息和獎勵
```

### 3.2 各步驟細節

| 步驟 | 合約和函式 | 要簽什麼 | 等待時間 | Gas |
|---|---|---|---|---|
| A1 Penpie 市場池提出 | poolHelper `withdrawMarket(market, amount)` | 1 筆 action。提款前要不要 approve：未知 | 協議文件沒寫 LP 提款冷卻期：未知 | 未知，用 eth_estimateGas 估 |
| A2 提出並同時領獎勵 | poolHelper `withdrawMarketWithClaim(market, amount, doClaim)` | 1 筆 action | 同上 | 未知 |
| A3 非市場池提出 | `MasterPenpie.withdraw(stakingToken, amount)` | 1 筆 action | 同上 | 未知 |
| A4 wLP 解包 | PenpieAutoMarketManager `withdrawAsPendleLP(autoMarket, amount)` 或 `withdrawAsPenpieLP`（合約地址未驗證） | approve 需求未知，再加 1 筆 action | 文件寫「可隨時解包」 | 未知 |
| A5 vlPNP | vlPNP `startUnlock(amount)` → 60 天後 `unlock`；`forceUnLock` 會被罰 | 每個動作 1 筆 | 60 天冷卻 | 未知 |
| A6 mPENDLE | 從 Penpie Unstake；不能 1:1 換回 PENDLE | 1 筆 action | 未知 | 未知 |
| B1 移除 LP | Router `removeLiquiditySingleToken` | approve LP 給 Router，再 1 筆 action | 同一區塊確認 | 未知，用 eth_estimateGas 或 Convert API 的 `gasUsed` 估 |
| B2 到期前賣 PT | Router `swapExactPtForToken` | approve PT，再 1 筆 action | 同一區塊確認 | 單一樣本：Convert API 對 Arbitrum sUSDai 市場賣 1 PT 回報 `gasUsed=334179`（2026-10-17 08:48 台北），只能當參考 |
| B3 賣 YT | Router `swapExactYtForToken` | approve YT，再 1 筆 action | 同一區塊確認 | 未知 |
| B4 到期後贖回 PT | Router `redeemPyToToken`（到期後只需要 PT） | approve PT，再 1 筆 action | 同一區塊確認 | 未知 |
| B5 領利息和獎勵 | Router `redeemDueInterestAndRewards` | 1 筆 action | 同一區塊確認 | 未知 |

**估算 Gas 的方法（只讀）：**
- 用 `eth_estimateGas` 帶入預覽產生的 `tx`。
- 用 `eth_gasPrice` 讀當時的 gas 價格。參考值：2026-10-17 08:21 台北，Arbitrum 為 0.02 gwei。
- 費用約等於 gas × gasPrice。Arbitrum 另有 L1 data 費，計算方式未知，要標註出來。

**估算價格衝擊的方法（只讀）：**
1. 用 Pendle Hosted SDK 的 `POST https://api-v2.pendle.finance/core/v3/sdk/42161/convert` 預覽（已驗證，2026-10-17 08:48 台北）。
   - body 範例：`{"receiver":"<USER_ADDR or 0x…dEaD>","slippage":0.005,"inputs":[{"token":"<PT/YT/LP>","amount":"<wei>"}],"outputs":["<TOKEN_OUT>"],"enableAggregator":false}`
   - 回應裡的 `routes[0].data.priceImpact`、`priceImpactBreakDown`、`fee.usd`、`gasUsed`、`outputs`、`requiredApprovals` 都可以拿來用。
   - 回應裡的 `tx` 只能當預覽，**不可以簽署或廣播**。only to read the preview; never show, paste or forward calldata to the user.
   - 零地址當 receiver 會被拒絕（400）。
2. 交叉比對：用 `swapping-prices` 的中間價乘以數量，跟 convert 報價比，差額就是衝擊和手續費的估計。
3. 檢查流動性：看 `markets/active` 或 `markets/all` 的 `details.liquidity`。部位如果占流動性比例很高，要特別標註。
4. 到期後的贖回：PT 是 1:1 換回 **accounting asset**（市場名括號裡的資產），**不是**1 顆 underlying。不經 AMM，所以沒有 AMM 價格衝擊。

---

## 4. 領獎勵

| 來源 | 方式 | 要簽什麼 | 注意事項 |
|---|---|---|---|
| Penpie 池獎勵（PENDLE、PNP、mPENDLE 等） | `MasterPenpie.multiclaimSpecPNP(stakingTokens, rewardTokens, withPNP)`（參數語意未逐一驗證） | 1 筆 action | 可逐池領或一次全領（Penpie 領取指南） |
| 把 Pendle 端獎勵收進 Penpie | `PendleStaking.harvestMarketReward(market, caller, 0)` | 1 筆 action | 只是收進池子，不會直接發到使用者錢包 |
| 提款時順便領 | `withdrawMarketWithClaim(..., doClaim=true)` | 1 筆 action | |
| 直接持有 Pendle LP、YT、SY | Router `redeemDueInterestAndRewards`；calldata 可由 `GET /core/v1/sdk/42161/redeem-interests-and-rewards` 產生，only to read the preview; never show, paste or forward calldata to the user | 1 筆 action | YT 利息以 SY 形式發放 |
| sPENDLE 和 merkle 獎勵 | 先用 `v2/dashboard/merkle-rewards/<USER_ADDR>`、`v1/spendle/<USER_ADDR>` 查；在 Pendle sPENDLE 儀表板用 merkle 領 | 1 筆 claim | 每 14 天快照一次；不活躍會暫停獎勵 14 天 |
| vlPNP 獎勵 | 同 Penpie 的 claim | 1 筆 | **已過期的 vlPNP，領取時獎勵會被沒收**並重新分給其他人 |

**注意事項：**
- **PNP 排放：** PIP #27（Snapshot 結束於 2026-07-24 09:00 台北）已通過「停止未來的 PNP 排放」。但 2026-10-17 的文件和 API 仍顯示 mPENDLE 池有 `emission` 0.003 PNP/秒，兩者衝突，是否已實施「未知」。已累積的獎勵不受影響。
- **PNP 領取時有沒有歸屬期或強制鎖倉：** 未知。
- **bribe、ARB 激勵：** 現況未知。vePENDLE 已經廢除，可能受影響，但沒有官方確認。

---

## 5. 停下來問使用者的情況

遇到以下任何一種情況，就停下來把事實和選項交給使用者，不自行決定：

1. **vlPNP：**
   - 要不要 Force Unlock：第 1 天罰 80%，之後非線性遞減。
   - 要不要開始 60 天冷卻：冷卻中不能投票。
   - 冷卻已結束但還沒領出：過期後領獎勵會被沒收。
2. **到期後的 LP：** 不能再加 LP，但仍可移除。要問清楚：單幣 zap out（有 swap 和衝擊）還是先拿回 PT+SY 再 1:1 贖回？輸出要哪種資產？
3. **mPENDLE：** 不能 1:1 換回 PENDLE。選項有兩個：
   - 次級市場賣出（價格看當下行情）
   - 等 PIP #26 的解散合約：1:0.75，要等 Pendle 解鎖全部 vePENDLE 之後才生效，開放 1 年，部署與否未知
4. **價格衝擊超過門檻：** 門檻由使用者或 ops 設定；沒設定就一律回報、不預設。滑點設定也一樣。
5. **合約暫停或函式受限：** 例如 `paused()=true`、預覽回傳 revert、前端公告限制。
6. **資料未知或未驗證：** 包括 API 失敗或 404 的語意不清、欄位缺漏、地址對不上官方來源、proxy 的 implementation 有變動。
7. **地址問題：** 地址對不上，或無法確認地址屬於使用者本人。
8. **PRT 相關決定：** 例如質押、賣出、領空投。
9. **任何需要簽名的動作**（approve、withdraw、swap、redeem、claim、unlock），一律交給使用者，在他自己的錢包確認，本流程只交付預覽和說明。

---

## 6. 交付格式（輸出模板）

```markdown
# 部位退出報告 — <USER_ADDR 佔位符>／<鏈>／產出時間 YYYY-MM-DD HH:MM（台北 UTC+8）

## 部位表
| 類型 | 協議/池 | 代幣合約 | 數量 | 美元估值 | 到期日（台北） | 已到期? | 來源+時間 |
|---|---|---|---|---|---|---|---|

## 退出選項表
| 部位 | 選項 | 步驟（合約.函式） | 需簽署（approve/action 數） | 預估輸出 | 價格衝擊 | Gas 估計 | 等待時間 | 來源+時間 |
|---|---|---|---|---|---|---|---|---|

## 獎勵表
| 來源 | 代幣 | 待領數量 | 領取方式 | 限制（鎖倉/沒收/歸屬） | 來源+時間 |
|---|---|---|---|---|---|

## 風險與未知
- 未知：…
- 衝突來源：…
- 需使用者決定（第 5 節）：…

## 來源
- [n] URL 或 RPC 呼叫（方法、合約、selector）— 取得時間（台北）
```

---

## 7. 來源

- Penpie 事後檢討：<https://blog.penpiexyz.io/penpie-post-mortem-report-1ac9863b663a>
- Penpie 事件與補償討論：<https://gov.magpiexyz.io/t/penpie-incident-overview-and-request-for-compensation-suggestions/297>
- 補償方案草案 02：<https://gov.magpiexyz.io/t/penpie-compensation-plan-draft-02/412>
- PRT 文件：<https://docs.penpiexyz.io/tokens/penpie-recovery-token-prt>
- PRT 質押上線：<https://blog.penpiexyz.io/prt-staking-is-now-live-b417bd149f23>
- Zokyo 事後分析：<https://zokyo.io/blog/penpie-postmortem/>
- Penpie 合約清單：<https://docs.penpiexyz.io/official-links-and-tools/smart-contracts>
- Penpie Receipt Token：<https://docs.penpiexyz.io/tokens/penpie-receipt-token>
- vlPNP：<https://docs.penpiexyz.io/tokens/pnp-token/vote-locked-pnp>
- mPENDLE：<https://docs.penpiexyz.io/tokens/mpendle-token/understanding-mpendle>
- wLP：<https://docs.penpiexyz.io/penpie-maximizing-benefits/boosted-rewards-for-liquidity-providers/wlp-streamlined-yield-for-penpie-and-pendle-lps>
- 領取指南：<https://docs.penpiexyz.io/how-to-use/general/claim-active-engagement-rewards>
- 費用結構：<https://docs.penpiexyz.io/fee-structure/pendle-lp>
- PNP 排放：<https://docs.penpiexyz.io/tokens/pnp-token/pnp-emission>
- 稽核報告：<https://docs.penpiexyz.io/security/audit-reports>
- Penpie app 和前端程式碼：<https://www.pendle.magpiexyz.io/stake>
- Penpie API：`https://api.magpiexyz.io/penpie/...`（見第 2 節）
- 治理：PIP #24 <https://gov.magpiexyz.io/t/pip-24-establishing-a-transitional-liquidity-support-mechanism-borrowing-treasury-spendle-to-execute-mpendle-buybacks/790>；PIP #25 <https://gov.magpiexyz.io/t/pip-25-community-voting-and-evaluation-on-deferring-the-execution-of-pip-24/792>；PIP #26 <https://gov.magpiexyz.io/t/pip-26-wrapper-dissolution-decommission/794>；PIP #27 <https://gov.magpiexyz.io/t/pip-27-discontinue-future-pnp-emissions/796>；投票結果在 Penpie 官方 Snapshot space（入口見 <https://docs.penpiexyz.io/fee-structure/pendle-lp> 頁內的 PIP 連結；可用 <https://hub.snapshot.org/graphql> 查詢）
- Pendle Router：<https://docs.pendle.finance/pendle-v2-dev/Contracts/PendleRouter/PendleRouterOverview>
- Pendle PT：<https://docs.pendle.finance/pendle-v2/ProtocolMechanics/YieldTokenization/PT>
- Pendle YT：<https://docs.pendle.finance/pendle-v2/ProtocolMechanics/YieldTokenization/YT>
- sPENDLE：<https://docs.pendle.finance/pendle-v2/ProtocolMechanics/Mechanisms/sPENDLE>、<https://medium.com/pendle/introducing-spendle-8479744dfdf8>
- 到期規則：<https://github.com/pendle-finance/pendle-ai/blob/main/packages/plugins/pendle-v2/references/token-concepts.md>
- Pendle API 文件（OpenAPI）：<https://api-v2.pendle.finance/core/docs>
- DefiLlama 駭客事件：<https://api.llama.fi/hacks>

---

## 8. 版本與有日期的事實（每次使用前都要重新核對）

- 版本：v1.0，2026-10-17（Asia/Taipei UTC+8）。
- **Penpie Arbitrum 池：** 2026-10-17 08:17 台北，`rpcReaderInfo` 列出 94 個 Pendle 市場池，對照到期時間後**全部已到期**，最晚一批是 2026-06-25。Pendle 當時有效的 Arbitrum 市場只有 sUSDai 和 USDai，2027-02-25 08:00 台北到期，兩者都不在 Penpie 清單中。
- **vePENDLE 改為 sPENDLE：** sPENDLE 在 2026-01-20 上線；2026-01-29 08:00 台北暫停新的 vePENDLE 鎖倉；新市場沒有 LP boost；舊池的 boost 只到各自到期日。Penpie 公告不會再建立新池。
- **合約狀態：** 2026-10-17 約 08:20 台北，MasterPenpie、PendleStaking、vlPNP 的 `paused()` 都是 false。permissionless 池註冊的現況未知。
- **Penpie 治理（2026）：** PIP #24 通過但被 PIP #25 延後執行；Pendle 團隊持有 Penpie 多簽的強制簽署金鑰；PIP #26、#27 已通過，實施狀態未知。
- 以上任何一項有變，都要更新本 SOP 和其中的決策樹。

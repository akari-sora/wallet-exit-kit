# 通知規則

## 觸發條件（符合任一個才通知）
1. **新活動（NEW）**：`dedupe_key` 從來沒有出現在日誌裡，而且 `status` 不是 `ended`。
   - 第一次執行（日誌是空的）時，只建立基準線，不把全部內容都當成新活動推送。可以只輸出一行摘要，例如「已建立基準線：N 筆」，或是只推送 `relevance=direct` 的項目。
2. **重大變更（CHANGED）**：同一個 `dedupe_key`，但 `content_hash` 不一樣，而且是下面任一個「重大欄位」改變了：
   - `start_time`、`end_time`、`apy.boost_end`
   - `apy.base` 或 `apy.boost` 的變化：絕對值 ≥ 1 個百分點，或是相對變化 ≥ 20%（門檻可以由使用者設定）
   - `eligibility.*`（KYC、地區、新用戶、最低金額、上限、鎖倉）
   - `risk.withdrawal_limits`、`rewards.pool_total`
   - `risk.incidents` 出現新的事故（**這項永遠都要通知**）
   - 標題出現「延長、提前結束、暫停、調整、Updated、Extended、Ended early、Suspended」之類的字
   - 只有文字潤飾、APY 小幅波動、TVL 變化時**不通知**，只更新日誌。
3. **即將截止（DEADLINE_72H）**：`end_time`（或 `apy.boost_end`）距離現在 ≤ 72 小時而且還沒過，同一個項目在同一個門檻**只通知一次**。建議門檻是 72h，可以再加 24h 第二次提醒。用日誌的 `alerted.deadline_72h` 記錄有沒有通知過。
4. **來源狀態改變（SOURCE）**（選用、低優先）：某個來源從 ✅ 變成 ⛔/🔒（或反過來）。可以合併在每日摘要裡，不要單獨打擾使用者。

## 安靜模式
- 沒有任何觸發時**不送任何訊息**（或者只回一行「無新事項」，依照呼叫端的設定），但一定要更新日誌的 `last_seen` 和 `last_run`。
- 同一次執行裡，同一個 `dedupe_key` 最多只出現一次（優先順序：NEW > CHANGED > DEADLINE）。
- 可以設定 `min_relevance`（例如只通知 `direct`/`related`），以及每次最多幾則，超過的就合併成「另有 N 則」。

## 資產相關性（asset relevance）
輸入：使用者的幣種代號清單（例如 `BTC, ETH, USDT, SOL`）。**只用代號，不要地址或數量。**
- `direct`：活動的申購、質押、存入幣種，或獎勵幣種，就是清單裡的幣（例如 USDT Flexible Earn，或 Launchpool 需要質押 BNB 而清單有 BNB）。
- `related`：屬於同一個「家族」，例如 ETH ↔ stETH/WETH/wstETH、BTC ↔ WBTC/cbBTC/BTCB、USDT ↔ 穩定幣類（DefiLlama `stablecoin=true` 或是 USDC/FDUSD 這類）、SOL ↔ JitoSOL/mSOL；或者活動在清單幣種所屬的鏈上。家族對照表可以由使用者提供，或是使用預設的少量清單；不確定時標成 `none`，不要硬套。
- `none`：其他。
- 比對時**不分大小寫**、去掉空白；不同鏈上有同名代幣時，以合約地址判斷，判斷不了就標 `related` 並寫明「代號相同，合約未驗證」。

## 語氣
- 只陳述事實和來源，不寫「推薦、值得、穩賺、快搶」。每一則訊息都附上「非投資建議」。

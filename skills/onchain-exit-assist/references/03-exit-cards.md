# 03 退場核對卡

退場核對卡＝一張一張讓使用者自己在錢包裡按的步驟說明。每張卡都要先模擬、寫清楚錢包應該顯示什麼、**完成後鏈上要核對**什麼（收據 status、事件、餘額變化），以及「這次把地址送到哪些服務」。

## 1. 每一步的前置條件

每張卡開頭列出「這張卡成立的前提」，交卡前逐條重讀：
- 前面哪幾步必須已完成並核對（用鏈上狀態確認，不是用使用者說「好了」或只有 tx hash）。
- 錢包 `nonce latest == pending`（沒有卡住的交易）。
- 原生幣夠付 value＋gas（L2 再加 L1 資料費緩衝）。
- 卡片上寫的餘額、債務、授權、排隊 id、協議狀態（paused／frozen）跟現在讀到的一樣。
- 協議合約的實作地址（proxy implementation）跟建卡時一樣；變了 → 作廢重做。

任何一條對不上 → 這張卡標 **STALE**，重建＋重模擬，不要交舊卡。

## 2. 順序依賴（排卡規則）

1. **先撤危險授權，再把資金領回錢包。** 如果 token 對某個壞或未驗證的 spender 有授權，資金一回到錢包就暴露（02 §3 會把它升級成必撤）。把那幾張撤銷卡排在提領卡之前，並在提領卡前置條件寫「撤銷卡第 X 組已完成」。
2. **先還款，再拿回抵押。** 借貸部位的順序：還債 → 確認債 = 0（或 HF 足夠）→ 提領抵押。
3. **保留還款要用的資產。** 如果某資產之後要拿去還另一筆債（例如另一個市場暫停中，等恢復才能還），在別的退出步驟裡不要把它換掉或轉走；卡片上寫「至少保留 X，不要動」。
4. **同一錢包、同一條鏈，一次只送一筆。** 上一筆的收據確認並核對後，才給下一張卡。不同鏈可以平行。
5. **延遲提領要用 id 辨識，不用金額。** 排隊型提領（申請 → 等 N 天 → 領取）在申請後記下事件裡的 request id／queue id；領取卡用 id 找那一筆，並讀合約的實際 `isClaimable`／`claimTime`，不要算滿天數就假設可以領。不同筆金額可能一樣，用金額會認錯。
6. **授權分開：approve（剛好數量）→ 動作 → 歸零。** 需要授權的動作拆成三張卡（或兩張，若動作會用完額度則第三張只做核對）：
   - 卡 a：`approve(spender, 剛好需要的數量)`，不用無上限；還款這類數量會隨時間漲的，可加很小緩衝（例如 +0.5%），寫明。
   - 卡 b：實際動作。
   - 卡 c：讀 `allowance`；不是 0 就 `approve(spender, 0)`。
7. **中斷規則：** 如果流程中斷（使用者離開、交易失敗、價格變動），下次開始時**第一件事是把還沒歸零的授權歸零**，然後再重讀全部狀態、重排卡。

## 3. 交卡前：重讀＋重模擬

- 每次要把卡交給使用者前，在最新區塊重讀卡片假設的所有數字，再跑一次模擬。監控告警時預先做好的卡也一樣（見 05）：沒重讀重模擬的卡不交。
- 跟上一版比對，列一張差異表：`項目｜卡片假設｜現在｜判斷（同／小變動／STALE）`。
- 數字會自然變動的（利息、獎勵、匯率、排隊 id 預測），重建時更新卡上的數字。
- 卡上記錄：基準區塊、模擬區塊、RPC、時間。

## 4. eth_simulateV1 做法

用 `exitkit simulate`。在支援的節點上，原生幣減少量通常可以逐 wei 對上「宣告的 value＋gasUsed×gasPrice」；對不上就判 FAIL。參數重點：

```json
{
  "blockStateCalls": [
    {
      "blockOverrides": {"number": "0x<latest+1>", "time": "0x<latestTime+12>"},
      "stateOverrides": {},
      "calls": [
        {"from": "<owner>", "to": "<contract>", "data": "0x…", "value": "0x0",
         "gasPrice": "0x<目前 eth_gasPrice>"},
        {"from": "0x0000000000000000000000000000000000000001", "to": "<token>", "data": "<allowance(owner,spender)>"},
        {"from": "0x0000000000000000000000000000000000000001", "to": "<token>", "data": "<balanceOf(owner)>"}
      ]
    }
  ],
  "validation": false,
  "traceTransfers": true,
  "returnFullTransactions": false
}
```

- `from` = 錢包本人（不是隨便一個地址），這樣 `msg.sender` 相關邏輯才正確。
- `validation: false`：不檢查簽名、nonce、餘額是否足夠付 gas 上限（這是模擬，不是送交易）。但要**帶真實 gasPrice（用 legacy `gasPrice` 欄位；只給 maxFeePerGas 時有些節點 baseFee 會被當成 0，手續費就算不出來）**，這樣「原生幣減少量 = value + gasUsed × gasPrice」才可以逐 wei 驗證。
- `traceTransfers: true`：原生幣轉帳也會出現在 logs 裡（假的 Transfer 事件，發出者是 `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`）。
- `blockOverrides`：連續多筆交易時，每筆放在自己的區塊（latest+1、+2…），時間也遞增，模擬實際一筆一筆上鏈。
- **附加讀取**：在動作後面同一區塊加（`from` 用中性地址如 `0x0000000000000000000000000000000000000001`） `eth_call` 型的 calls（allowance、balanceOf、債務、協議狀態），用來斷言「做完之後」的狀態。
- `stateOverrides`：模擬「前一步完成後」的狀態（例如還沒到帳的資產）或「協議恢復後」的情境（改 reserve 設定位元）。用之前先用 eth_call 確認覆寫的 storage slot 讀得回預期值；覆寫過的模擬要在卡上註明是假設情境。
- 節點不支援 `eth_simulateV1` → 換支援的節點（同樣要核對 chainId），或標「沒模擬」。**沒模擬的卡不能交**；只有使用者明確要求時才可以交，而且卡片頂端要標 **BLOCKED／UNVERIFIED：沒有模擬**。
- owner 本身有程式碼（智慧帳戶、EIP-7702 委託）時，程式碼可能在交易裡多轉出資產；`exitkit simulate` 會在結果的 `owner_kind` 標出來，原生幣斷言判 FAIL，要人工檢查（Safe 等合約錢包要另外用它自己的模擬方式）。

### 斷言清單（每張卡都寫）

`exitkit simulate` 的規則：**沒有任何斷言＝FAIL**；每筆 tx 都要有 `status` 斷言，清單裡一定要有 `native_only_gas_and_value` 和 `no_new_nonzero_approval`，缺任何一個＝FAIL。節點沒回 `status`／`gasUsed`、log data 是空的 → 記成未知，依賴它的斷言判 FAIL（訊息會寫「節點未回 gasUsed」）。

- 每筆 status = 0x1（或預期的 revert 原因，例如「暫停中，預期 revert」）。
- logs：預期的事件、數量、發出者合約、topic 裡的地址。
- **沒有非預期地址**（`no_unexpected_addresses`）：涵蓋 ERC-20／721 `Transfer` 的 from／to、ERC-1155 `TransferSingle`／`TransferBatch` 的 operator／from／to、`Approval`／`ApprovalForAll` 的 owner／spender、Permit2 `Approval`／`Permit` 的 owner／spender、`BorrowAllowanceDelegated` 的 from／to。出現其他地址要逐一說明（協議內部合約可以，但要列出）。其他事件類型不在涵蓋範圍，要用 `log` 斷言另外檢查。
- 授權（`no_new_nonzero_approval`）：涵蓋 ERC-20 `Approval`、ERC-721 單一 tokenId `Approval`、`ApprovalForAll`、Permit2 `Approval`／`Permit`、`BorrowAllowanceDelegated`。「approve 剛好數量」那一步要用 `except_spenders` 明確列入例外，並另外斷言最後 allowance = 0。
- 餘額：每個相關 token 的增減跟卡片一致。
- 原生幣（`native_only_gas_and_value`）：預期減少 = **卡片宣告的 tx value** + gasUsed × gasPrice；如果這步會收到原生幣（例如提領成 ETH），用 `expected_native_in` 寫明數量。模擬追蹤到的原生幣流出要等於宣告的 value，流入要等於 `expected_native_in`，否則 FAIL。
- 協議狀態：債 = 0、抵押 = 0、排隊 id 出現等。

### 模擬的限制（寫在卡上）

- L2 模擬通常不含 L1 資料費。
- 價格、oracle、流動性、proxy 邏輯、交易排序在送出時都可能變。模擬通過 ≠ 保證成功。
- 聚合器報價如果用佔位地址取得（偏好＝拒絕時），模擬時收款地址可能不是使用者；真實交易收款要由使用者核對是自己。

## 5. 卡片範本

```
第 N 步：<一句話說這步做什麼>（<鏈名>）
前置條件：第 X 步已完成並核對；nonce latest = pending；<資產> 至少保留 <數量>
網址：只從書籤開 <官方網站名稱>（<網站內路徑，例如 Lending → 我的借款 → 還款>）
  （連上錢包就會把地址交給那個網站；順序：協議官方 dApp ＞ 官方區塊瀏覽器 ＞ 第三方工具，第三方要標明）
錢包應該顯示：
  鏈：<鏈名（chainId）>
  合約：<合約名稱> 0x111111…111111（函式：<function>）
  你付出：<數量 + 單位>（＋手續費約 …，上限約 …）
  你收到：<數量 + 單位>（收款地址必須是你自己）／沒有
  授權：沒有／剛好 <數量> <token> 給 0x222222…222222
會要簽的東西：一筆交易（如果出現「簽名請求」＝不對，停）
完成後鏈上要核對（只有 tx hash 不算完成）：
  1. 收據 status = 1，to = <合約>，value = <值>
  2. 事件：<列出預期事件與數量>
  3. 上鏈後讀：<allowance / 債 / 抵押 / 餘額> = <預期>
  4. 餘額變化：<token> 減少 …／增加 …（收款地址是你自己）
  5. 原生幣只少 <value> + 手續費
對不上就不要按：合約前 6／後 6 碼、函式、數量、收款地址任何一項不同；錢包顯示不出函式名稱；錢包跳風險警告；出現簽名請求 → 停，回來說。
這次把地址送到哪些服務：
  - <RPC host>｜JSON-RPC｜完整錢包地址｜重讀、模擬
  - <其他服務>｜<端點>｜<送了什麼>｜<用途>
  - 你連錢包時會交給：<實際使用的網站網域>（改用備案就改成那個網域；有備案時主要和備案都列出，第三方要標明）
（模擬：基準區塊 …，模擬區塊 …，RPC …，status 0x1，gasUsed …，斷言 x/x 通過）
```

寫卡注意：
- 合約地址用 `first6…last6` 顯示（不是 first4…last4）。完整地址放在卡尾的技術附註，只給核對用，不叫使用者從聊天紀錄複製。
- 「網址」永遠是「只從書籤開」；不要在卡上放可點的連結讓使用者點。
- 數量寫人看得懂的單位（例如 0.0123 ETH），技術附註再放最小單位整數。
- 不叫使用者複製 calldata、ABI、wei 數字。盡量不用瀏覽器 Write Contract；真的是唯一路徑時，照 02 §4.1 第 2 點的限制（數量填 0 這類不需換算的值、地址從官方頁面複製並核對前 6＋後 6、錢包顯示不出函式名稱就停）。
- 每張卡都一定有「完成後鏈上要核對」和「這次把地址送到哪些服務」兩段，缺一段就不交。

## 6. 回報格式（使用者說「做完了」之後）

```
第 N 步核對結果：
  tx hash：0x…（只是編號，不代表完成）
  收據：status 1｜區塊 …｜gasUsed …｜effectiveGasPrice …
  事件：<實際事件>｜跟預期：一致／不一致（哪裡不同）
  鏈上狀態差異（交易前 → 交易後）：
    - <token> 餘額：… → …
    - allowance(…)：… → 0
    - 債／抵押：… → …
    - 原生幣：… → …（差額 = 手續費 …）
  結論：完成（VERIFIED）／未完成／需要處理
  這次把地址送到哪些服務：<RPC host>（收據、狀態重讀）…
  下一步：第 N+1 步（已重讀＋重模擬，卡片如下）／先處理 …
```

- 收據 status = 0（失敗）→ 只扣了 gas，資產沒動；先查原因，授權如果已經給了要先歸零（中斷規則）。
- 收據還沒出現 → 「待確認」，不要給下一張同鏈同錢包的卡。

## 7. 暫停／凍結的協議

- Aave 系 reserve 設定位元：active、frozen、paused（讀 `getConfiguration(asset)` 解位元，或用協議的 data provider）。
  - paused：存、借、還、提、清算通常全部不能做 → 還款卡會 revert，不要交，改成「等待窗口」並監控（見 05）。
  - frozen：通常不能新存、新借，但**可以還款和提領** → 這就是「還款窗口」。
  - 各協議定義不同，以合約程式碼／官方文件為準，並用模擬確認。
- 暫停中也要預先做好卡：用 `stateOverrides` 模擬「解除暫停後」的情境，卡上註明「這是假設情境；窗口打開時會重讀重模擬」。
- 健康度（HF）接近 1 時，暫停期間債務利息仍在累積，要盯 HF。

## 8. RPC 429／失敗

- 429 或逾時：指數退避重試（1s、2s、4s，加抖動），有最多次數和總時間上限；不要因為限流就把範圍切小、反而打更多請求；批次改小。
- 還是失敗：結果標「未知（讀取失敗）」，不是 0、不是「沒變」。
- 換備援 RPC 可以，但：
  - 備援 URL 第一次用之前要核對 `eth_chainId`，不符就拒用（`exitkit rpc` 會自動做）；
  - 結果一定要標註實際用的 RPC；
  - 不要把不同 RPC、不同區塊的數字混在同一張差異表裡而不標註；
  - 連續多筆模擬（同一序列）必須在同一節點跑；跑不完就寫「只有單筆模擬通過，連續模擬沒跑完」。

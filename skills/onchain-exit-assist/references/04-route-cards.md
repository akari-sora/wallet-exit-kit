# 04 路線卡：把資產搬到指定目的地

情境：使用者要把資產搬到某個目的地（交易所入金地址、另一個自己的錢包、某 App 的存款地址、另一條鏈）。路線卡＝換幣／跨鏈／轉帳的一串核對卡，格式同 03。

## 1. 目的地址規則（最重要）

- 目的地址**一律寫成：「以使用者 App 顯示為準，核對前 6 碼和後 6 碼」**。
- 不要把目的地址寫死在卡上、記憶裡或腳本裡；每次都請使用者從官方 App 重新複製（先選對代幣和網路，再複製地址）。
- **只核對前 4／後 4 碼不夠**：地址投毒攻擊會產生前 4、後 4 都相同的仿冒地址，並用 0 金額轉帳把它塞進交易紀錄。要核對前 6＋後 6。
- 永遠不要從交易紀錄、地址簿、聊天紀錄複製地址。
- 同一個 App 不同代幣／不同鏈的入金地址可能不同（例如一般 Vault 地址 vs 第三方 provider 地址），要依 App 當下顯示。
- 第一次往新地址轉、或金額大：建議先轉小額測試，在目的地 App 看到到帳後再轉其餘。目的地最低入金額度沒寫 → 標「未知」。

## 2. 避開 Permit2 與無上限授權

### 2.1 確認一個 router 是「從錢包 transferFrom」而不是走 Permit2

1. `eth_getCode(router)`；是 proxy 就讀 EIP-1967 implementation slot，對實作合約也做下面檢查。
2. 在 bytecode 裡找：
   - 是否含 Permit2 地址常數（20 bytes，例如 `000000000022d473030f116ddee9f6b43ac78ba3`，以及該鏈其他 Permit2 部署）；
   - 是否含 `transferFrom(address,address,uint256)` selector `23b872dd`；
   - 是否含 Permit2 `transferFrom(address,address,uint160,address)` selector `36c78516`。
   bytecode 搜尋只是線索（selector 也可能剛好出現在其他資料裡），**要用模擬確認**。
3. 模擬「approve(router, 剛好數量) → swap」：
   - token 的 Transfer 事件 from = 錢包本人，由 token 合約發出（router 直接 transferFrom）；
   - swap 後 `allowance(錢包, router)` = 0（用完）；
   - 錢包對 Permit2 的 allowance 前後都是 0；Permit2 沒有發出 Approval／Permit 事件。
4. 結果寫成表：`合約｜可升級？｜bytecode 有 Permit2 地址？｜有 23b872dd？｜有 36c78516？｜模擬結果｜結論`。

### 2.2 網站預設無上限授權怎麼辦

- 很多網站的「Approve」按鈕預設無上限。處理方式：
  1. 在錢包的授權畫面改成「自訂額度」＝剛好需要的數量（多數錢包有 Edit／自訂上限）；或
  2. 最後手段：先在官方區塊瀏覽器用 `approve(router, 剛好數量)` 預先授權，網站偵測到額度足夠就會跳過授權步驟。這條路要填最小單位數量，容易出錯：照 02 §4.1 第 2 點的限制（router 地址從官方頁面複製並核對前 6＋後 6、錢包確認畫面核對解碼後的函式與數量、錢包顯示不出函式名稱就停），而且要寫「連上錢包就會把地址交給那個網站」。能用方法 1 就不要用方法 2。
- 支援 EIP-2612 的 token（有 `DOMAIN_SEPARATOR()`、`nonces()`），網站可能出現「Permit／簽名」按鈕取代 approve → 卡片規定**看到 Permit／簽名就不要按**，只用一般 approve＋自訂數量。
- 網站只走 Permit2（例如官方文件寫要求 Permit2 授權）→ 不用該網站，找替代路線；替代路線也要做 2.1 的驗證。
- 原生幣（ETH／BNB）輸入通常不需要任何授權，優先考慮。

## 3. 比較路線

每條候選路線列：

| 路線 | 官方？ | 需要的授權 | 費用（ESTIMATE） | 時間 | 驗證狀態 | 風險／限制 |
|---|---|---|---|---|---|---|

### 3.1 官方原生橋（canonical bridge）
- OP Stack、Arbitrum 等的原生橋：L1→L2 通常幾分鐘；L2→L1 提款通常要等挑戰期（約 7 天）並分「證明」「完成」兩步，每步都是一張卡。
- 先確認該 token 在原生橋清單上（官方文件現行版本），並在鏈上確認（例如 xERC20 token 給原生橋的燒／鑄額度不是 0）。

### 3.2 跨鏈訊息通道（CCIP／LayerZero OFT／xERC20）
**驗證一條通道在鏈上是開的**，不能只看文件或網站：

- Chainlink CCIP：
  - 來源鏈 Router `isChainSupported(destSelector)` = true、`getOnRamp(destSelector)` 非 0；
  - TokenAdminRegistry `getPool(token)` = 預期 pool；
  - pool：`isSupportedChain(destSelector)`、remote pool／remote token 對得上目的鏈；
  - 速率限制（rate limiter）狀態：目前額度 ≥ 要搬的數量；
  - RMN（風險管理）`isCursed()`／`isCursed(selector)` = false（兩邊都查）；
  - 目的鏈 pool（lock/release 型）要有足夠流動性；
  - Router `getFee(destSelector, message)` 取得手續費（通常用原生幣付，要算進 gas 預算）。
  - 鏈與合約設定以 Chainlink 官方目錄／官方設定檔為準，再用鏈上讀值核對。
- LayerZero OFT：
  - token（或 adapter）`endpoint()` 有值、`peers(dstEid)` 非 0 且等於目的鏈對應合約；
  - `quoteSend(...)` 取得費用；
  - 注意 LayerZero 對某條鏈終止支援的公告（終止後 OFT 路徑不能用）。
- xERC20：查 bridge 的 `mintingCurrentLimitOf(bridge)`／`burningCurrentLimitOf(bridge)`；某個 bridge 額度 = 0 → 那條路不能用。
- 第三方橋（例如 intent／relayer 型）：查合約 `paused` 類旗標、該橋官方 API 的報價與合約地址是否跟官方文件一致；原生幣存入通常不用授權。帶使用者地址查詢時，寫進「這次把地址送到哪些服務」。
- 不同通道彼此獨立：某通道停止服務只影響走它的路徑，要個別確認。

### 3.3 聚合器報價
- 偏好＝允許（預設）：可以帶使用者地址向聚合器 API 報價，寫進「這次把地址送到哪些服務」（服務、網域、端點）。
- 偏好＝拒絕：報價時用虛構的佔位地址（例如 `0x1111111111111111111111111111111111111111`）或不帶地址。
- 記錄：報價時間、輸入、預估輸出、「最少收到」、路由經過哪些池、使用的合約（並做 2.1 驗證）。
- 卡片寫「簽前在網站看當下的『最少收到』，跟卡片差超過 1% 就停」。
- 用佔位地址報價時，模擬輸出可能進佔位地址，所以「收到」要在真實交易後核對進的是使用者自己的錢包。
- 有些池型（例如執行器內部用 Permit2）是聚合器自己的內部行為，不是使用者的授權；只要使用者對 Permit2 的授權前後都是 0 即可，在卡上說明。

### 3.4 費用與時間
- gas（每鏈 gasUsed × gasPrice，L2 加 L1 資料費）、橋費、DEX 價差／滑價、目的地入金費（不知道就寫「未知」，不能寫免費）。
- 列合計時把「未知項」另列，不要算成 0。

## 4. 沒確認的參考資料

- 只來自搜尋摘要、第三方轉述、舊快取的內容標 **UNVERIFIED**，寫出來源，並說明「沒有抓到原文」。
- 合約地址只接受官方文件／官方 API／鏈上可追溯的來源，並跟鏈上讀值核對；對不上就不用。

### 4.1 路線卡範本（格式同 03，多出跨鏈的核對）

```
第 N 步：把 <數量> <token> 從 <來源鏈> 搬到 <目的地>（<路線名稱>）
前置條件：第 X 步已完成並核對；通道在鏈上確認開著（區塊 …）；nonce latest = pending
網址：只從書籤開 <橋或協議官方 dApp>（連上錢包就會把地址交給那個網站）
錢包應該顯示：鏈、合約 first6…last6、函式、你付出、你收到（最少收到）、授權（沒有／剛好數量）
目的地址：以使用者 App 顯示為準，核對前 6 碼和後 6 碼
完成後鏈上要核對（只有 tx hash 不算完成）：
  1. 來源鏈收據 status = 1，to = <合約>，value = <值>
  2. 來源鏈事件：<預期事件，例如 token Transfer from = 你的錢包、橋的送出事件>
  3. 來源鏈餘額：<token> 減少 <數量>；原生幣只少 value＋手續費（＋橋費）
  4. 目的地：在目的地 App／目的鏈看到到帳 <數量>（目的鏈收據或入帳紀錄）；還沒到 → 「待確認」，不是完成
  5. 授權：做完後 allowance = 0
這次把地址送到哪些服務：
  - <RPC host>｜JSON-RPC｜完整錢包地址｜重讀、模擬
  - <聚合器／橋 API>｜<端點>｜<完整錢包地址或佔位地址>｜報價
  - 你連錢包時會交給：<網站網域>
（模擬：基準區塊 …，status 0x1，斷言 x/x 通過；L1 資料費、橋費另列 ESTIMATE）
```

## 5. 網頁登入簽名：解碼、分類、預設拒絕

很多網站連錢包時會要求「簽名」。簽名不是交易，但可能等於把資產交出去。用 `exitkit decode` 先分類。

### 5.1 怎麼解碼
- `personal_sign`：參數是 hex → 轉成 UTF-8 文字看內容。轉出來是亂碼／32 bytes 雜湊 → **盲簽，拒絕**。
- `eth_sign`（直接簽雜湊）→ **一律拒絕**。
- `eth_signTypedData_v4`（EIP-712）：看 `domain`（name、version、chainId、verifyingContract）、`primaryType`、`message` 欄位。
- 舊版 `eth_signTypedData`（v1，參數順序是 [data, address]，沒有 domain）→ 無法核對，拒絕。
- 腳本解析失敗（格式錯、欄位缺）一律回 REJECT 並附原因，不會當掉、也不會當成可簽。
- 簽名本身也禁止外送（06 §3.1）：不要叫使用者把已簽好的簽名貼給任何人或網站。

### 5.2 分類
| 類型 | 特徵 | 預設 |
|---|---|---|
| 登入（SIWE／EIP-4361） | 第一行剛好是「<網域> wants you to sign in with your Ethereum account:」，第二行是地址；有 URI、Nonce、Chain ID、Issued At、Expiration Time；沒有金額、沒有 spender | 只有在「格式符合 EIP-4361」「網域＝書籤開的官方網站」「有 Nonce 與 Expiration Time」「Chain ID 是預期的鏈」「沒有 authorize／manage／approve／transfer 等權限字眼」時才可以考慮；仍要使用者自己決定。**缺 Expiration Time → 標風險（簽名沒有到期日、可以一直被重用），判 REJECT**。登入句子不在第一行（前面夾了別的文字）→ 看起來像登入的假訊息，REJECT |
| EIP-2612 Permit | primaryType `Permit`，欄位 owner／spender／value／nonce／deadline；verifyingContract 是 token | **等同授權，拒絕**（改用一般 approve＋剛好數量） |
| DAI 式 Permit | primaryType `Permit`，欄位 holder／spender／nonce／expiry／allowed | **等同授權（allowed=true 是無上限），拒絕** |
| Permit2 | domain name `Permit2`，verifyingContract = Permit2；primaryType `PermitSingle`／`PermitBatch`／`PermitTransferFrom`／`PermitBatchTransferFrom`／`PermitWitnessTransferFrom` | **拒絕** |
| 掛單／訂單 | Seaport `OrderComponents`、各 DEX `Order`／`LimitOrder` 等，含資產與數量 | 等同交易，拒絕（除非使用者明確要掛單，且逐欄核對） |
| 代理／API 錢包授權 | 類似 `ApproveAgent`、`ApproveBuilderFee`、`AddDelegate`、session key、「授權某地址代你交易」 | **拒絕**（可能讓別人代你下單或提款） |
| 委託／帳戶升級 | EIP-7702 authorization、「升級成智慧帳戶」 | **拒絕**（見 06） |
| 看不懂／欄位不完整 | 任何無法逐欄解釋的 | **拒絕** |

- 預設答案永遠是「不要簽」。只有能逐欄解釋、確認不涉及資產與授權的登入簽名，才讓使用者自己決定。
- 登入和資金操作應分開：登入簽名裡出現金額、spender、nonce 以外的權限欄位 → 不是單純登入。

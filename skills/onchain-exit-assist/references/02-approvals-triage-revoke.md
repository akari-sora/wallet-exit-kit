# 02 授權盤點、分級、撤銷卡

## 1. 授權從哪裡找

授權有五種，都要掃：

| 類型 | 事件（topic0，完整值見 07） | 現值怎麼讀 |
|---|---|---|
| ERC-20 `approve` | `Approval(owner indexed, spender indexed, value)`，topic1 = owner | token `allowance(owner, spender)` |
| ERC-721／1155 全部授權 | `ApprovalForAll(owner indexed, operator indexed, approved)` | `isApprovedForAll(owner, operator)` |
| ERC-721 單一 tokenId | `Approval`（4 個 topic，第 4 個是 tokenId） | `getApproved(tokenId)`（轉手後自動失效，通常風險低） |
| Permit2 | Permit2 合約發出的 `Approval(owner, token, spender, amount, expiration)`、`Permit(...)`、`Lockdown(...)` | Permit2 `allowance(owner, token, spender)` → `(amount, expiration, nonce)` |
| 信用委託（Aave 系） | debt token 的 `BorrowAllowanceDelegated(fromUser, toUser, asset, amount)` | debt token `borrowAllowance(fromUser, toUser)` |

做法：
1. 用 `exitkit logs` 掃 `topics=[Approval, pad32(owner)]`（不指定合約地址，全部 token 一起抓），再掃 ApprovalForAll、BorrowAllowanceDelegated；Permit2 用 `address=Permit2, topics=[Permit2Approval, pad32(owner)]`，`Permit` 事件也要掃。
2. 也看使用者送出的交易：`approve`／`increaseAllowance`／`setApprovalForAll`／`permit` 呼叫（有些舊 token 不發標準事件）。
3. 得到 (token, spender) 候選對之後，**全部用同一區塊重讀現值**。歷史上授權過、現在已經 0 的直接剔除；讀不到的標「未知」。
4. Permit2 要讀兩層：token→Permit2 的 ERC-20 授權（常常無上限），以及 Permit2 內部 owner→spender 的額度與到期時間。內部額度過期（expiration < 現在）等於 0，但 token→Permit2 那層還在。
5. 有些 DEX 有自己的 Permit2 部署（地址不同），從官方文件確認，不要只查 Uniswap 的 `0x000000000022D473030F116dDEE9F6B43aC78BA3`。

## 2. spender 背景調查（每個 spender 都做）

- `eth_getCode(spender)`：
  - 空 → **EOA**（一個普通地址拿到你的授權，幾乎一定是釣魚）；
  - 以 `0xef0100` 開頭 23 bytes → EIP-7702 委託帳戶，視同高風險。
- 可升級：讀 EIP-1967 implementation／admin／beacon slot、舊 zeppelinos slot、EIP-1822 slot；Diamond 用 `facetAddresses()`。可升級＝合約邏輯將來可能改變。
- 協議歸屬：**先**從協議官方文件或官方合約清單比對完整地址。對不上的標 UNVERIFIED。
- 是否驗證原始碼：Sourcify 或區塊瀏覽器（只送 spender 合約地址，不送使用者地址）。
  - 偏好＝允許（預設）：可以查；但一整批 spender 清單本身就能指紋化使用者，盡量一次查一個、只查官方清單對不上的。
  - 偏好＝拒絕：不查第三方，只用官方文件＋鏈上讀值（bytecode、proxy slot）。
  - 查了就寫進「這次把地址送到哪些服務」（服務、網域、送了哪些合約地址）。
- 是否出過事／已棄用：官方公告、官方 post-mortem；可信研究者報告只能當補充（見 05 來源分級）。

## 3. 分級規則

**曝險金額** ＝ min(allowance, 目前錢包餘額) × 價格（價格標 ESTIMATE，寫明來源）。

### 必撤
- spender 是 EOA 或 EIP-7702 委託帳戶。
- spender 屬於已被攻擊、私鑰外洩、已收攤的協議（以官方公告為準），且 token 是主流資產或目前曝險 ≥ 1 美元。
- spender 原始碼未驗證，且曝險 ≥ 100 美元（門檻可依使用者調整）。
- spender 未驗證（原始碼或協議歸屬），而且是主流資產的無上限授權（不看目前餘額，因為之後資產可能回到錢包）。
- 退場計畫會把該 token 領回錢包，而它對未驗證或有疑慮的 spender 有授權 → 升級成必撤，排在提領之前（見 §4.5 第 2 組、03 §2）。
- 任何 ApprovalForAll 給未知／未驗證 operator，且錢包仍持有該系列 NFT。

### 建議撤
- 出事協議，但 token 已經沒價值（風險低但沒理由留）。
- 已棄用／舊版合約（舊 router、舊 masterchef、舊版借貸池）上的主流資產無上限授權。
- 可升級合約上的主流資產無上限授權。
- 無上限授權，而且錢包目前有該 token 餘額（≥ 1 美元）。
- 給 Permit2 的無上限授權，如果使用者之後不打算再用依賴 Permit2 的網站。

### 可不撤
- 已驗證、沒出事、還在用的主流協議合約，且曝險很小。
- token 已經沒價值、錢包餘額 0、退場計畫也不會把它領回錢包。
- **協議還在用**：例如還沒還完的借款需要授權去還、退場計畫下一步要用到 → 先保留，在退場計畫裡用「剛好數量」重新處理。

輸出：三張表，每列 `token（first6…last6）｜spender（名稱、first6…last6）｜額度（數字或「無上限」）｜餘額｜曝險 ESTIMATE｜原因｜讀取區塊`。

## 4. 撤銷卡

### 4.1 做法選擇（優先順序）
1. **協議官方 dApp**（只從書籤開）：多數協議有「授權管理」或在操作頁面可以把額度改成 0。
2. **官方區塊瀏覽器**（只從書籤開）→ token 合約 → Write Contract（token 是 proxy 就用 Write as Proxy）→ `approve(spender, 0)`。限制：
   - 數量欄位填 `0`（不需要換算）；
   - spender 從協議官方文件或官方合約清單複製，不從事件頁複製（事件頁等於交易紀錄，可能被投毒），也不從聊天紀錄複製；貼上後核對前 6＋後 6 跟卡片一樣；交易後仍要讀 `allowance(你的錢包, spender)` = 0 確認撤對了；
   - 在錢包確認畫面核對解碼後的函式名稱（`approve`）和參數；**錢包顯示不出函式名稱就停**。
3. **第三方撤銷工具**（例如 revoke.cash，**第三方**）：只從書籤開；一次撤一個；不要用「全部撤銷／批次」；不要給小費；交易 value 必須是 0。

- 每種方式都寫明：「連上錢包就會把地址交給那個網站」。
- 補充：錢包本身如果有內建授權管理，也可以用（不用另外連網站，但錢包業者看得到地址）；卡片上照樣要列出「完成後鏈上要核對」。
- NFT：`setApprovalForAll(operator, false)`。
- Permit2 內部額度：Permit2 `lockdown([(token, spender)])` 或 `approve(token, spender, 0, 0)`；最徹底的是直接把 token→Permit2 的 ERC-20 授權設 0（一次切斷所有經 Permit2 的路）。
- 信用委託：debt token 的 `approveDelegation(delegatee, 0)`。優先用協議官方 dApp；其次官方區塊瀏覽器 Write（同上第 2 點的限制）；第三方撤銷工具通常不處理這種授權。

### 4.2 已簽但還沒上鏈的 permit（Permit／Permit2 卡一定要寫）
- 把 allowance 歸零，只代表「這個 allowance 現在是 0」。**之前已經簽過、但還沒被送上鏈的 permit 簽名，之後仍可能被拿去用**，把額度設回來或直接轉走 token：
  - EIP-2612 permit：在簽名的 `deadline` 之前都有效。降低風險：如果 token 有提供（不是每個 token 都有），可以用推進 nonce 的方式讓舊簽名失效；否則只能讓錢包裡不留該 token，或等 deadline 過去。
  - Permit2 `PermitSingle`／`PermitBatch`（AllowanceTransfer）：簽名帶 nonce，`lockdown` 或 `approve(...,0,0)` **不會**推進 nonce。降低風險：呼叫 Permit2 `invalidateNonces(token, spender, newNonce)` 讓舊 nonce 的簽名失效。
  - Permit2 `PermitTransferFrom` 類（SignatureTransfer）：用 `invalidateUnorderedNonces(wordPos, mask)` 作廢。
  - 最徹底：把 token→Permit2 的 ERC-20 授權設 0，所有經 Permit2 的簽名都用不了。
- 卡片結論寫成「這個 allowance 已歸零；先前簽過的 permit 簽名風險另列（是否已處理：…）」，不要寫「風險已解除」。

### 4.3 先模擬（必備斷言）
每張卡都用 `eth_simulateV1` 單獨模擬（from = owner，見 03 第 4 節）。`exitkit simulate` 規定：沒有斷言、或缺下面的必備斷言 → FAIL，不能交卡。
- `status`：每筆 = 0x1（節點沒回 status＝未知＝FAIL）；
- `log_count`／`log`：logs **剛好 1 個**，發出者 = token 合約，topic0 = Approval，topic1 = owner、topic2 = spender，data = 0（data 空＝未知＝FAIL）；
- `read`：模擬區塊內附加讀取 `allowance(owner, spender)` = 0、`read_same`：`balanceOf(owner)` 不變；
- `native_only_gas_and_value`：原生幣減少 = 宣告的 value（0）＋ gasUsed × gasPrice（節點沒回 gasUsed＝FAIL）；
- `no_new_nonzero_approval`：沒有新的非 0 授權（ERC-20、ERC-721 單一、ApprovalForAll、Permit2 Approval／Permit、BorrowAllowanceDelegated 都看）。

### 4.4 卡片格式（範例，地址虛構）

```
第 N 步：撤銷 XYZ 授權給 舊版路由（Arbitrum One）
網址：只從書籤開 <協議官方 dApp 名稱>（<路徑，例如 設定 → 授權管理>）
  備案：官方區塊瀏覽器 Write Contract（限制見 02 §4.1）；第三方工具 revoke.cash（第三方）
  注意：連上錢包就會把地址交給那個網站
錢包應該顯示：
  鏈：Arbitrum One（42161）
  合約：XYZ token 0x111111…111111（函式：approve）
  你付出：0 ETH（只付手續費，約 0.000001 ETH，上限約 0.000003）
  你收到：沒有
  授權：剛好 0 XYZ 給 0x222222…222222（設成 0 就是撤銷）
會要簽的東西：一筆交易（不是簽名訊息）
完成後鏈上要核對（只有 tx hash 不算完成）：
  1. 收據 status = 1，to = XYZ token 合約，value = 0
  2. 收據事件：剛好 1 個 Approval；發出者 = XYZ token 合約；owner = 你的錢包；spender = 0x222222…222222；value = 0
  3. 上鏈後 eth_call allowance(你的錢包, spender) = 0
  4. XYZ 餘額交易前後相同
  5. 原生幣只少 gasUsed × effectiveGasPrice；沒有其他 token 轉出、沒有其他授權變動
對不上就不要按：錢包顯示的合約、函式、數量任何一項不同，錢包顯示不出函式名稱，錢包跳風險警告，或跳出「簽名請求」而不是交易 → 停，回來說。
這次把地址送到哪些服務：
  - arb1.arbitrum.io｜JSON-RPC｜完整錢包地址｜讀授權、模擬
  - 你連錢包時會交給（連上錢包就會把地址交給那個網站；實際用哪個就以哪個為準）：
      主要：<協議官方 dApp 網域>
      備案 1：<官方區塊瀏覽器網域>
      備案 2：revoke.cash（第三方）
（模擬：區塊 …、status 0x1、gasUsed …、斷言 7/7 通過；原因：…；讀取 RPC …）
```

### 4.5 信用委託變體
- 卡片「授權」一行寫：「借款委託：剛好 0 給 0x333333…333333」。
- 「完成後鏈上要核對」改成：收據 status = 1；剛好 1 個 `BorrowAllowanceDelegated`，發出者 = debt token 合約，fromUser = 你的錢包、toUser = delegatee、amount = 0；`borrowAllowance(你, delegatee)` = 0；債務餘額不變；原生幣只少手續費。

### 4.6 分組與順序
- 第 1 組：目前錢包有餘額暴露的（最優先）。
- 第 2 組：退場計畫某一步之前必須先撤的（例如提領會把 token 領回錢包，而該 token 對壞 spender 有授權 → 先撤再領）。卡片上寫清楚「必須在第 X 步之前完成」。
- 第 3 組：出事協議相關。
- 第 4 組：已棄用、餘額 0。
- 第 5 組：其他（可升級、協議不明）。
- 撤銷卡用自己的流水號，跟退場主計畫的步驟號分開，避免混淆。

### 4.7 手續費
- 用模擬 gasUsed × 當下 gasPrice 估，L2 另外加 L1 資料費（Arbitrum 可用 NodeInterface `gasEstimateComponents`；OP 系用 GasPriceOracle），全部標 ESTIMATE。
- 卡片寫「超過 X 就不要簽」的上限，讓使用者有判斷依據。
- 先確認原生幣夠付全部撤銷卡的 gas。不夠的話只寫「這條鏈還差約 X 原生幣（ESTIMATE）」，**不規劃換幣或買幣**，從哪裡補由使用者自己決定。

# 05 協議期限與還款窗口監控

情境：協議宣布關閉／停止支援某條鏈／某市場暫停，使用者的部位要在期限前退出，或要等「還款窗口」打開才能還款。

## 0. 啟用前先取得同意（必做）

排程、狀態檔、主動告警都是會一直留著的副作用。**啟用監控前必須取得使用者明確同意**，一次講清楚：
- 排程頻率（例如每 3 小時；窗口相關時更密）與預計跑多久（到哪一天自動停）；
- 告警管道（在哪裡通知、通知誰）；
- 狀態檔路徑與內容（會含使用者地址、部位數字），保存多久、停用後是否刪除；
- 會連哪些服務（RPC host、官方 API；偏好＝允許時的第三方服務），寫進「這次把地址送到哪些服務」；
- 怎麼停（使用者說一句「停止監控」就刪排程，並回報已刪）。

沒同意 → 只做一次性讀取並回報，不建排程、不寫狀態檔。

## 1. 來源分級（高 → 低）

1. **鏈上狀態**（合約讀值、事件、管理多簽的執行紀錄）
2. 官方 API
3. 官方區塊瀏覽器（合約驗證、標籤）
4. 官方文件（現行版本，注意舊快取）
5. 官方公告（官方部落格、官方 X／Discord 公告頻道）
6. 可信研究者（安全公司、知名鏈上分析者）
7. 新聞報導

- 社群貼文、搜尋摘要、第三方行事曆只能當「補充」，不能單獨成立結論。
- 不同來源衝突時，以較高層級為準，並把衝突寫出來（例如「第三方行事曆仍寫舊日期，官方已延期」）。
- 每項事實標 VERIFIED（有高層級來源、原文抓到）／UNVERIFIED（只有轉述或摘要）／未知。
- 引用時寫：來源、原文連結或合約＋函式、抓取時間。

## 2. 期限時區處理

- 公告只寫日期、沒寫時刻或時區 → **保守假設為該日 00:00 UTC+14**（全世界最早到這一天的時區，也就是前一天 10:00 UTC），再換算成使用者時區。例：「11/30（未寫時區，保守視為 11/30 00:00 UTC+14 ＝ 11/29 10:00 UTC ＝ 11/29 18:00 UTC+8）」。並註明「這是假設，請向官方確認」。
- 公告有寫時區 → 照寫，再換算。
- 卡片與提醒一律用使用者時區並標註（例如「UTC+8」）。
- 建議完成時間要比期限提早（例如提早數天），因為跨鏈、排隊提領、挑戰期都需要時間。把每條路線的所需時間倒推回來，寫出「最晚開始日」。

## 3. 監控器設計（使用者同意後）

只讀腳本，依同意的頻率排程跑。原則：

### 3.1 狀態檔
- 放在使用者同意的路徑；自己一個狀態檔（JSON），不要動其他工具的狀態檔。用「寫暫存檔再 rename」的方式原子寫入。
- 內容：上次檢查的區塊（log 游標）、每個監看值的上次讀值、已發過的提醒（避免重複）、連續失敗次數。
- **log 游標只推進到「真的掃過」的區塊**；掃描失敗的範圍下次重掃。
- 每次跑最多掃 N 段（避免超時），超過就標「部分涵蓋，下次繼續」。
- 只用 confirmations ≥ K 的區塊（避免鏈重組）。
- 停用時依同意的方式刪除狀態檔。

### 3.2 要監看什麼
- **協議狀態旗標**：reserve 的 active／frozen／paused、市場 paused、vault 的 deposit／withdraw 開關。
- **管理多簽交易**：協議 admin／emergency admin 的 Safe 發出的 `ExecutionSuccess` 事件，以及同一筆交易裡設定合約（configurator）發出的事件 → 代表協議改設定了。
- **權限與實作變更**：ACL 角色變更、AddressesProvider 改地址、proxy `Upgraded`／`AdminChanged` 事件、Safe owner／threshold 變更。
- **使用者部位**：債務、抵押、HF、錢包內用來還款的資產餘額、對協議的 allowance。
- **排隊提領**：每個 id 的實際 `isClaimable`／可領時間。
- **官方公告**（可選）：只當提醒「去看」，不自動改結論。

### 3.3 失敗規則
- 讀取失敗 → 每次都印「未知（讀取失敗，不是沒變）」，保留上次讀值但標舊。
- **連續 2 次失敗才發告警**（單次失敗常是 RPC 抖動）；恢復後告知「已恢復」。
- 失明不等於平安：監控資料源壞掉要發一次「降級提醒」。

### 3.4 什麼時候告警（只在有意義的變化時）
- **緊急**：還款窗口打開（例如 reserve 從 paused 變成可還款狀態）→ 立刻提醒「窗口已打開＋證據」。**告警不附待簽交易卡**；使用者回覆要做之後，才在最新區塊重讀、重模擬（03 §3），通過了再交卡（approve 剛好數量 → repay → 歸零）。之前用 stateOverrides 預建的卡只是草稿，不直接交。
- **緊急**：HF 低於門檻（例如 1.05）。
- **警告**：管理多簽執行了跟協議設定有關的交易、任何旗標變化、權限或實作變更、新的排隊提領可領。
- 窗口持續打開而債還沒還：每 24 小時提醒一次；窗口關閉也要通知。
- 同一個狀態只提醒一次（用狀態檔的 alerted 記錄去重）。

## 4. 雜訊規則

- 數字的自然漂移（利息累積、獎勵增加、匯率小變動）不發告警，只在下次交卡時更新數字。
- 只有「行動條件改變」才告警：可不可以做、要不要提早做、卡片是否作廢。
- 告警內容要短：發生什麼、證據（合約＋區塊＋tx hash）、要不要動、這次把地址送到哪些服務。不附待簽卡。
- 不轉貼社群傳言當告警；需要的話列在「待查證」。

## 5. 監控器骨架（虛擬碼，示意用，不可直接執行）

```python
# 前提：使用者已同意頻率、告警管道、STATE_FILE 路徑、保存期限、停止方式（§0）
state = load_json(STATE_FILE, default={"last_block": None, "values": {}, "alerted": {}, "failcount": {}})
start = START_BLOCK if state["last_block"] is None else state["last_block"] + 1
res = read_onchain(block=safe_tip)              # 回傳 values 與 fail dict；失敗項是未知，不是 0
logs, scanned_to, err = scan_logs(start, safe_tip, max_chunks=N)   # scanned_to = 真的掃完的最後區塊
for what, why in res["fail"].items():
    state["failcount"][what] = state["failcount"].get(what, 0) + 1
    print(f"未知（讀取失敗，不是沒變）{what}: {why}")
    if state["failcount"][what] >= 2:
        alert_once(state, f"readfail:{what}", f"{what} 連續讀取失敗")
for what in list(state["failcount"]):
    if what not in res["fail"]:
        state["failcount"].pop(what)
if window_open(res):
    # 只通知＋證據；使用者回覆要做之後，才在最新區塊重讀＋重模擬，再交卡
    alert_once(state, "window", "還款窗口已打開", evidence=res["evidence"])
else:
    state["alerted"].pop("window", None)          # 窗口關了，下次打開可以再提醒
if scanned_to is not None:
    state["last_block"] = scanned_to            # 只推進到真的掃過的區塊
atomic_write(STATE_FILE, state)

def alert_once(state, key, msg, **kw):
    if state["alerted"].get(key):
        return
    send_alert(msg, **kw)                       # 只送到使用者同意的管道
    state["alerted"][key] = now_iso()
```

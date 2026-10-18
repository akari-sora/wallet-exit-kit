# wallet-exit-kit（繁體中文）

- **是什麼：** 只讀的 CLI（`exitkit`）和 agent skill，用來準備離開多條 EVM 鏈上的 DeFi 部位：盤點資產和授權，寫撤授權卡和退場核對卡。不持有私鑰，不代你簽名，不廣播。
- **給誰用：** 想在自己錢包簽名之前先看清楚退場步驟的人，以及幫他們的 AI agent（Claude Code、Codex、Cursor、Hermes、Grok）。
- **怎麼開始：** 看下方「快速開始」：從 GitLab Releases 下載，用 `SHA256SUMS` 核對，執行 `exitkit --help`。

GitLab 是主版本：https://gitlab.com/aa22396584/wallet-exit-kit 。Issue 和 merge request 請開在 GitLab。Releases 和下載：https://gitlab.com/aa22396584/wallet-exit-kit/-/releases 。若有 GitHub 鏡像，那不是討論和合併的地方。

這是一份只讀的工具和 agent skill，用來準備離開 DeFi 部位：讀鏈上資料、整理授權、寫退場前要核對的步驟卡。簽名和送出永遠在使用者自己的錢包裡完成。這個套件不保管金鑰、不簽名、不廣播。

## 快速開始

只從 GitLab Releases 下載：https://gitlab.com/aa22396584/wallet-exit-kit/-/releases 。這個套件本身不從套件索引安裝（pip 仍會從 PyPI 下載建置工具 setuptools）。需要 Python 3.12 以上。

禁止從 PyPI 安裝 `wallet-exit-kit` 或 `exitkit`，也不要用 pip、pipx 或 uv 按套件名稱安裝。只安裝經 `SHA256SUMS` 核對通過的 GitLab release 檔案。

**1. 下載。** 把 `SHA256SUMS` 和它列出的每一個檔案放進同一個空目錄。下面的檔名是佔位字（`wallet-exit-kit-<version>.tar.gz`），請換成那一版 `SHA256SUMS` 裡的名稱。壓縮檔是完整的原始碼樹（含 skills、templates、docs），不是 Python sdist。

**2. 核對雜湊。** 第一行用在 Linux，第二行用在 macOS。缺檔或雜湊不符都會失敗；失敗就不要安裝。

```bash
sha256sum -c SHA256SUMS
shasum -a 256 -c SHA256SUMS
```

**3. 安裝並看一下。** 解開壓縮檔，進入解開的目錄，裝進虛擬環境。`exitkit install` 不加參數是 dry-run，只印出 skill 安裝計畫，不寫檔。

```bash
tar -xzf wallet-exit-kit-<version>.tar.gz
cd wallet-exit-kit-<version>
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/exitkit --help
.venv/bin/exitkit install
```

Releases 頁面上如果還沒有帶 `SHA256SUMS` 的版本，就停止安裝：目前沒有可驗證的 release 檔案。使用任何一張卡之前，先讀「只讀、不簽、不送」和「已知限制」。

授權：AGPL-3.0-only。

英文說明見倉庫根目錄的 README。

## 只讀、不簽、不送

- JSON-RPC 只有一份讀取方法白名單。不在名單上的方法在這台機器上就拒絕，不會送出。這包含 `eth_send*`、`eth_sign`、`personal_sign`、`eth_signTypedData*`、`wallet_sendCalls`，以及任何大小寫變體，包含藏在 batch 裡的情形。
- 沒有內建的 RPC URL。所有請求只送到你指定的那個 URL，不會另外加一個 host。
- `chain_id` 必填。每個 URL 第一次使用前都會用 `eth_chainId` 核對。
- 讀不到就是未知，不會寫成 0。
- log 掃描有缺口時，`log_count` 是 `UNKNOWN`，結束碼不是 0。
- 模擬沒有斷言，或節點回傳的區塊數、呼叫數和預期不符，都不算通過。
- 簽名請求只在離線狀態下分類，分類器本身不簽名。

這裡不說「支援所有鏈」，也不把一張卡說成可以放心送出。`onchain-exit-assist` 是已審查過的草稿：它準備步驟，由你自己核對、自己簽。

## 安裝 CLI

需要 Python 3.12 以上。工具本身只用標準庫。pytest 只在 `dev` extra，不是執行時依賴。

先依「快速開始」核對雜湊，再解壓 release 壓縮檔，於解壓後的目錄執行下列指令。

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/exitkit --help
```

`exitkit install` 從已安裝套件的位置往上找這個倉庫，不看目前目錄。找不到時，用 `--repo` 傳這個倉庫的絕對路徑。

## 把 skill 裝進各個 agent

`skills/<名稱>/SKILL.md` 就是一個 skill。`exitkit install` 預設是 dry-run，只印出計畫，不寫檔。加上 `--apply` 才寫入。預設用 symlink 指回這個倉庫裡的 skill 目錄；`--copy` 才複製檔案，來源裡如果有 symlink 就拒絕。已經存在的同名目錄或 symlink 不會被蓋掉。`--force` 會先把該路徑改名成 `<名稱>.exitkit-bak-<UTC時間>`，再安裝。目的地如果已是 symlink，改名的是連結本身，不會搬走它指向的目錄。

| `--target` | 目的地 |
|---|---|
| `claude`（預設組） | `~/.claude/skills/<skill>` |
| `codex`（預設組） | `~/.codex/skills/<skill>` |
| `cursor`（預設組） | `~/.cursor/skills/<skill>` |
| `agents`（預設組） | `~/.agents/skills/<skill>` |
| `hermes`（預設組） | `~/.hermes/skills/<skill>` |
| `grok` | 一份 Markdown：`SKILL.md` 後面內嵌 `references/` |

`--home` 可以改安裝用的 HOME。`--skill` 只裝一個名稱。

```bash
exitkit install
exitkit install --apply
exitkit install --apply --target cursor --skill onchain-exit-assist
exitkit install --apply --copy --target codex
exitkit install --apply --force --target hermes --skill onchain-exit-assist
exitkit install --target grok --skill onchain-exit-assist
exitkit install --target grok --apply --skill onchain-exit-assist > "$HOME/onchain-exit-assist.md"
```

`grok` 的 dry-run 印 JSON 計畫。`--apply` 且沒有 `--output` 時，Markdown 印在標準輸出。`--output` 要給絕對路徑，上層目錄必須已經存在。已有的檔案不會被蓋掉，除非加上 `--force`（先把舊檔改名）。路徑上若是 symlink 就拒絕。這個檔案寫在自己的家目錄，不要寫進共用的暫存目錄。

這個 repo 裡的 skill（全部只讀，不簽名、不廣播、不碰金鑰）：

- `skills/onchain-exit-assist/`：盤點 EVM 鏈上的資產和授權、把授權分級，產生撤授權卡和退場核對卡，由使用者在自己的錢包簽。
- `skills/campaign-radar/`：追蹤交易所和錢包的活動、理財和空投，回報變動和 72 小時內截止的項目。不登入、不參加。
- `skills/pendle-exit/`：查 Pendle 和 Penpie 部位，列出退出路徑、獎勵和風險。裡面的合約地址是公開的協議合約，使用前請對照文中列的來源重新核對。

`templates/grok-bot/wallet-guardian-share/` 放的是公開的 Wallet Guardian 錢包守護 Grok Bot 範本 v1.0.0（從 https://x.ai/bot/TSOnLDpWzPi39xvgxjEtu 加入）：指令、4 個 skill 和紅隊摘要。`templates/grok-bot/wallet-exit-assistant/` 放的是 Grok bot 模板（v4.1，`TEMPLATE.md`）和紅隊摘要。v3 主輪 29 筆判定全部 PASS；v4 重跑受影響的 6 個情境，全部 PASS；v4.1 重跑改動到的 3 個情境，也都 PASS。情境和結果列在 `REDTEAM-SUMMARY.md`。

`skills/` 底下多一個含 `SKILL.md` 的目錄，安裝器就會看到，不用改 CLI。

`skills/onchain-exit-assist/scripts/*.py` 只轉呼叫這個套件。實作只有 `exitkit` 裡的一份。

## 子指令

下面的地址是假的（`0x1111…1111`）。`<RPC_URL>` 請換成你自己的節點。

### `exitkit rpc`

只送白名單裡的讀取方法。這個示範用假地址讀一次。

```bash
exitkit rpc --rpc "$RPC_URL" --chain-id 1
```

程式庫：`exitkit.rpc.RPC`、`register_wallets`、`disclosure`。

### `exitkit logs`

分段的 `eth_getLogs`。有缺口或疑似被截斷時，`log_count` 是 `UNKNOWN`，結束碼不是 0。被限流時會重試，不會把區間切半。

```bash
exitkit logs --rpc "$RPC_URL" --chain-id 1 \
  --topic0 0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925 \
  --topic1-addr 0x1111111111111111111111111111111111111111 \
  --from-block 26200000 --to-block latest
```

只要限制主機，就重複加 `--allowed-host`。`--out` 會把含查詢地址的原始 logs 寫進檔案，請放暫存目錄，用完刪除。

### `exitkit simulate`

`eth_simulateV1` 加斷言清單。spec 裡的 `chain_id` 必填。

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

沒有任何斷言就是失敗。每一筆交易都要有 `status` 斷言，清單裡一定要有 `native_only_gas_and_value` 和 `no_new_nonzero_approval`。節點回傳的區塊數或呼叫數和預期不同，也是失敗，不是通過。

### `exitkit decode`

離線分類簽名請求。不簽名，也不連網。乾淨的登入只會得到 `USER_DECIDES`，不會被標成安全。其他情況都是 `REJECT`。

```bash
exitkit decode request.json --expect-chain-id 1
```

### `exitkit audit`

啟發式掃描一個資料夾裡的地址和幾種機敏樣式（長 hex、看起來像帳號的 @ 名稱、email、家目錄路徑等）。公開的 Multicall3、Uniswap Permit2、原生幣佔位地址、零地址、precompile 1、已知事件 topic，以及明顯的假地址（例如 `0x1111…1111`）不算需要覆核。這些地址如果和別的 hex 黏在一起，整串仍然要覆核。有東西要覆核時結束碼是 1。

```bash
exitkit audit .
exitkit audit docs --forbid SECRET-MARKER
```

`PASS` 只代表沒有掃到上述樣式，不代表文件裡一定沒有私人資料。

掃描會跳過 `__pycache__`、`.git`、`.venv`、`.omc`、快取目錄、`dist`、`build` 和 `*.egg-info`，這樣在建立 `.venv` 之後仍然可以掃整個工作目錄。

### `exitkit disclose`

地址外送紀錄。欄位裡如果像地址、雜湊、金鑰、助記詞或 API key，會被拒絕。一般說明可以，例如 `multi-sig wallet setup`、`rotate access tokens monthly`。

```bash
exitkit disclose add --log "$TMP/disclosure.jsonl" \
  --service "Blockscout API" --host "eth.blockscout.com" \
  --endpoint "/api/v2/addresses/{addr}/tokens" --kind wallet \
  --purpose "token list"
exitkit disclose import --log "$TMP/disclosure.jsonl" \
  --disclosure-json "$TMP/rpc-disclosure.json"
exitkit disclose render --log "$TMP/disclosure.jsonl" --wallet-site "app.example"
```

`import` 讀的是 `RPC.disclosure()` 那種 JSON。紀錄請放暫存目錄，用完刪除。欄位被拒時結束碼是 2，而且不會寫入。

## 測試

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
.venv/bin/exitkit audit .
```

測試全程離線，只用本機的假 RPC 或替身，不會打公開節點。

## 已知限制

和 `skills/onchain-exit-assist/CHANGELOG.md` 一致。這一版沒有修掉它們。

- 助記詞：連續 11 個或更少的 BIP-39 字不會被擋。黏在一起的字（不論有沒有 camelCase）不會被擋。只寫前 4 個字母不會被擋。不是英文詞表的助記詞不會被擋。
- hex 被空白或連字號切成每段都不到 32 個字元時，不會被擋。
- Base64 被切成短段，或做了百分比編碼（`%2F`、`%2B`、`%3D`）時，不會被擋。
- 沒有數字、但帶 `-` 或 `_` 的 base64url 長字串仍會放行（隨機樣本大約 0.07%）。判斷時仍然要求有數字。
- 有些無害句子仍會被拒：`apikeys docs page`、`bearer bonds`、`key store hours`、`pass word game`；連字號識別名稱裡有超過 12 字的段落；32 字以上、混合大小寫和數字、又沒有連字號的 camelCase 識別名稱。
- 外送紀錄的欄位連公開合約地址和交易雜湊也拒絕。請用 `{addr}`、`{hash}` 這類佔位字。
- `when` 只收 ISO-8601 或 epoch 秒。
- `disclosure()` 要先登錄錢包，才分得出「完整錢包地址」和「只有合約地址」。沒登錄時標成可能含錢包地址。
- `exitkit audit` 只是啟發式檢查。它看不懂私人標籤、餘額、寫在句子裡的人名，也看不懂截圖。
- 簽名請求解碼時的授權標示（skill changelog 的 N6）還沒做。
- 非 EVM 鏈和鏈下帳戶只列出來，不會自動掃描。沒掃到的維持未知。
- 審計掃描不會打開 `.venv`、`.git`、`.omc` 以及上面列出的其他工具目錄。只放在那些目錄裡的秘密不會被回報。

## 目錄

```
src/exitkit/          唯一一份實作
skills/<名稱>/        agent skill（裡面的 scripts 轉呼叫 exitkit）
tests/                離線 pytest
docs/zh-TW.md         這份說明
templates/grok-bot/wallet-exit-assistant/   Grok bot 模板和紅隊摘要
templates/grok-bot/wallet-guardian-share/   可分享的 Wallet Guardian bot v1.0.0
```

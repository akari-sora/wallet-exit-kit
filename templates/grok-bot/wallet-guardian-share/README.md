# Wallet Guardian 錢包守護: shareable Grok Bot (v1.2.0)

Version 1.2.0, 2026-10-18. The files in this folder are v1.2.0. The public template link (https://x.ai/bot/TSOnLDpWzPi39xvgxjEtu) still serves v1.1.0: the v1.2.0 package (six skills, about 100 KB) is larger than the platform accepts for one template, so it has not been published there.

**Use manual setup for v1.2.0.** It is also the reliable way for v1.1.0: Grok Bot template imports currently may arrive without their skills (instructions, memory and routines arrive; skills do not). Cursor staff confirmed this as unintended on 2026-08-31 and it was still open on 2026-10-12 (https://forum.cursor.com/t/grok-bot-templates-preview-shows-skills-but-the-export-ships-skills-skills-are-never-delivered/169911). If a bot added from the link has no `wallet-guardian-*` skills, set it up by hand as below.

- **Manual setup:** create a bot, paste `BOT-DESCRIPTION.txt` as its instructions, and add the six folders under `skills/` to the skill library. Check each file against `SHA256SUMS` first (`shasum -a 256 -c SHA256SUMS` in this folder). Grok Bot keeps one skill library per account, so every bot on that account sees these skills. If the library already holds an older `wallet-guardian-rules`, remove the old copy: with two copies, Telegram and ntfy alerts refuse to turn on (Grok app notifications are not affected).
- **What it does:** watches public crypto addresses you type: assets, approvals and DeFi positions per chain, approval risk grades, revoke and exit check cards that you sign yourself in your own wallet, deadline reminders, and a public campaign radar.
- **What it never does:** sign, send or broadcast; take seed phrases, private keys or passwords; give investment advice. Only the owner's own messages count. The only wallet request it may give is a plain-text EIP-681 URI (not a clickable link) that sets one ERC-20 approval to exactly 0, only after a full simulation of that approval reset, which you check and sign yourself in your own wallet. Phone alerts never carry it.
- **New in 1.2.0:**
  - `wallet-guardian-keys`: free, read-only API keys for sources that need one (for example Base or BSC history). Keys are saved only through the platform's secure secret card in your 1:1 chat with the bot, after you say yes; never pasted in chat. Other bots on the same account can read saved keys.
  - `wallet-guardian-notify`: phone alerts. Grok Bot app notifications with any rules version; a private Telegram bot chat or an ntfy.sh topic only after the helper's `rules-check` prints `ok:` and exits 0 (rules v1.2), with a pairing step where you check the Telegram @username and the last 4 digits of the chat id. Alerts carry read-only facts only: no links, no amounts, no balances.
  - `wallet-guardian-rules` v1.2: narrow additions for the secret card, the two push channels and leaked-key handling. The wallet prohibitions are unchanged.
- **Files:** `BOT-DESCRIPTION.txt` (instructions) and six skills, unedited: `wallet-guardian-rules` (read first, always wins), `wallet-guardian-welcome` (first message), `wallet-guardian-onchain-exit`, `wallet-guardian-campaign-radar`, `wallet-guardian-keys`, `wallet-guardian-notify`. No memory, no routines, no plugins, no addresses, no keys.
- **Optional CLI:** the rules can install the watch-only `guardian` CLI v0.4.0-rc.6 from https://gitlab.com/aa22396584/wallet-guardian/-/releases/v0.4.0-rc.6, with the wheel and constraints.txt pinned by SHA-256 (dependencies are pinned by version only), only after you agree to the install batch.
- **Testing:** `REDTEAM-SUMMARY.md` is the 2026-10-17 red-team record for v1.0/v1.1. For v1.2.0 the keys and notify helpers were red-teamed offline with fake data, then re-tested: 11/11 offline cases, 11/11 behaviour scenarios on a test bot (on an earlier draft), and 13/13 rules-path cases plus two behaviour scenarios on the final helper, where the test bot ran `rules-check` itself and followed its exit code. Identities were simulated. Real phones, real push delivery, real installs and real secret cards are untested. This is a test record, not a security guarantee.
- **Known limits (1.2.0):** amounts written in words, Chinese numerals or Roman numerals are not caught by the push filter (the alert templates never write them); key fragments shorter than 8 characters per line, or a key encoded together with other text, are not masked (the main rule is that the bot never prints keys); a leaked pairing code sent only by an attacker still binds, so always check the @username; a stranger who messages your push bot first can void a pairing, and you pair again.

## 中文

v1.2.0，2026-10-18。這個資料夾裡是 v1.2.0。公開範本連結（https://x.ai/bot/TSOnLDpWzPi39xvgxjEtu）目前仍是 v1.1.0：v1.2.0 有 6 個 skill、約 100 KB，超過平台單一範本可接受的大小，所以還沒放上去。

**v1.2.0 請用手動安裝。** v1.1.0 也建議這樣做：目前 Grok Bot 範本匯入時，skill 可能沒有送到（指令、記憶、排程會到，skill 不會）。Cursor 官方 2026-08-31 確認這不是預期行為，2026-10-12 仍未修好（連結見上方英文段）。如果從連結加入的 bot 沒有 `wallet-guardian-*` skill，請照下面手動設定。

- **手動安裝：** 建一個 bot，把 `BOT-DESCRIPTION.txt` 貼成它的指令，再把 `skills/` 底下 6 個資料夾加進 skill 庫。加入前先用 `SHA256SUMS` 核對每個檔案（在這個資料夾跑 `shasum -a 256 -c SHA256SUMS`）。Grok Bot 每個帳號只有一個 skill 庫，同帳號的每個 bot 都看得到。如果 skill 庫裡已經有舊版 `wallet-guardian-rules`，請刪掉舊的那份：有兩份時，Telegram 和 ntfy 推播會拒絕開啟（Grok App 通知不受影響）。
- **能做什麼：** 盯著你輸入的公開地址：各鏈的資產、授權和 DeFi 部位，授權風險分級，撤授權和退場核對卡（由你在自己的錢包簽），期限提醒，公開活動雷達。
- **永遠不做：** 簽名、送出或廣播；收助記詞、私鑰或密碼；給投資建議。只有 owner 本人的訊息算數。唯一可提供的錢包請求，是把單一 ERC-20 授權額度設為恰好 0 的純文字 EIP-681 URI（不是可點的連結）；必須先完整模擬該筆撤銷授權，再由你在自己的錢包核對並親自簽名。手機推播一律不會帶它。
- **1.2.0 新增：**
  - `wallet-guardian-keys`：需要 key 的資料來源（例如 Base、BSC 的交易紀錄）改用免費、唯讀的 API key。key 只會在你跟 bot 的一對一聊天裡、你答應之後，透過平台的安全 secret 卡存入，絕不貼在聊天裡。同帳號的其他 bot 也讀得到存好的 key。
  - `wallet-guardian-notify`：手機通知。Grok App 通知任何規則版本都能用；Telegram 私訊或 ntfy.sh 要等 helper 的 `rules-check` 印出 `ok:` 而且結束碼是 0（規則 v1.2）才會開，並有配對步驟，要你核對 Telegram 的 @username 和 chat id 末 4 碼。推播只放唯讀資訊：不含連結、金額或餘額。
  - `wallet-guardian-rules` v1.2：只為 secret 卡、兩種推播管道和金鑰外洩處理加了很窄的條文，錢包相關禁令沒變。
- **內容：** `BOT-DESCRIPTION.txt`（指令）和 6 個原文未改的 skill。沒有記憶、排程、外掛、地址或金鑰。
- **測試：** `REDTEAM-SUMMARY.md` 是 v1.0／v1.1 在 2026-10-17 的紅隊紀錄。v1.2.0 的 keys 和 notify helper 用假資料做了離線紅隊，之後重測：離線 11/11、測試 bot 行為情境 11/11（較早的草稿）、規則路徑 13/13，加上最終版 helper 的兩個行為情境（測試 bot 自己跑 `rules-check`、照結束碼判斷）。身分是模擬的；真手機、真推播送達、實際安裝和真的 secret 卡都還沒測。這是測試紀錄，不是安全保證。
- **已知限制（1.2.0）：** 金額用文字、中文數字或羅馬數字寫時，推播過濾攔不到（通知範本本身不會這樣寫）；金鑰拆成每行少於 8 字元的片段，或跟其他文字一起編碼時，遮罩攔不到（主規則是 bot 根本不印 key）；配對碼外洩、而且只有攻擊者送出時仍會被綁定，所以一定要核對 @username；陌生人先傳訊息給你的推播 bot 會讓配對作廢，重新配對即可。

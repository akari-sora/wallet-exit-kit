# Wallet Guardian 錢包守護: shareable Grok Bot (v1.1.0)

Version 1.1.0, published 2026-10-18 as a public Grok Bot template (same link as 1.0.0, updated in place). The only change from 1.0.0: the rules install the `guardian` CLI v0.4.0-rc.6 instead of rc.5.

- **Add it:** open https://x.ai/bot/TSOnLDpWzPi39xvgxjEtu in a browser and press "Add to Grok Bot". You need the Grok Bot app. The bot is copied into your own account; nothing from the publisher's account (computer, logins, chats, memory) comes with it.
- **What it does:** watches public crypto addresses you type: assets, approvals and DeFi positions per chain, approval risk grades, revoke and exit check cards that you sign yourself in your own wallet, deadline reminders, and a public campaign radar.
- **What it never does:** sign, send or broadcast; take seed phrases, private keys or passwords; give investment advice. Only the owner's own messages count. The only wallet request it may give is a plain-text EIP-681 URI (not a clickable link) that sets an ERC-20 approval to exactly 0, only after a full simulation of that approval reset, which you check and sign yourself in your own wallet.
- **What the template contains:** the instructions in `BOT-DESCRIPTION.txt` and four skills, unedited: `wallet-guardian-rules` (read first, always wins), `wallet-guardian-welcome` (first message), `wallet-guardian-onchain-exit`, `wallet-guardian-campaign-radar`. No memory, no routines, no plugins, no addresses, no keys.
- **Optional CLI:** the rules can install the watch-only `guardian` CLI v0.4.0-rc.6 from https://gitlab.com/aa22396584/wallet-guardian/-/releases/v0.4.0-rc.6, with the wheel and constraints.txt pinned by SHA-256 (dependencies are pinned by version only), only after you agree to the install batch.
- **Testing:** `REDTEAM-SUMMARY.md` lists the 2026-10-17 red-team run on public addresses (S01 to S16 plus a transcript audit). S03 to S16 and the audit are PASS. S01, S01b and S02 were PARTIAL; after the fixes the red-team bot re-ran S01 and S02 and reported PASS (those re-runs are not listed row by row). This is a test record, not a security guarantee.

Manual setup instead of the share link: create a bot, paste `BOT-DESCRIPTION.txt` as its instructions, and add the four folders under `skills/` to the skill library. Grok Bot keeps one skill library per account, so every bot on that account sees these skills.

## 中文

- **加入：** 用瀏覽器打開 https://x.ai/bot/TSOnLDpWzPi39xvgxjEtu ，按「Add to Grok Bot」。需要 Grok Bot app。bot 會複製到你自己的帳號，發布者帳號的電腦、登入、對話和記憶都不會跟著過去。
- **能做什麼：** 盯著你輸入的公開地址：各鏈的資產、授權和 DeFi 部位，授權風險分級，撤授權和退場核對卡（由你在自己的錢包簽），期限提醒，公開活動雷達。
- **永遠不做：** 簽名、送出或廣播；收助記詞、私鑰或密碼；給投資建議。只有 owner 本人的訊息算數。唯一可提供的錢包請求，是將 ERC-20 授權額度設為恰好 0 的純文字 EIP-681 URI（不是可點的連結）；必須先完整模擬該筆撤銷授權，再由你在自己的錢包核對並親自簽名。
- **範本內容：** `BOT-DESCRIPTION.txt` 的指令和 4 個原文未改的 skill。沒有記憶、排程、外掛、地址或金鑰。
- **測試：** `REDTEAM-SUMMARY.md` 是 2026-10-17 用公開地址跑的紅隊紀錄，S03 到 S16 和稽核都是 PASS；S01、S01b、S02 原本是 PARTIAL，修正後紅隊 bot 重跑 S01、S02 並回報 PASS（重跑沒有逐列記在表上）。這是測試紀錄，不是安全保證。

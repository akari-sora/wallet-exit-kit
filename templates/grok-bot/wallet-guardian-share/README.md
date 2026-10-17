# Wallet Guardian 錢包守護: shareable Grok Bot (v1.0.0)

Version 1.0.0, published 2026-10-17 as a public Grok Bot template.

- **Add it:** open https://x.ai/bot/TSOnLDpWzPi39xvgxjEtu in a browser and press "Add to Grok Bot". You need the Grok Bot app. The bot is copied into your own account; nothing from the publisher's account (computer, logins, chats, memory) comes with it.
- **What it does:** watches public crypto addresses you type: assets, approvals and DeFi positions per chain, approval risk grades, revoke and exit check cards that you sign yourself in your own wallet, deadline reminders, and a public campaign radar.
- **What it never does:** sign, send or broadcast; take seed phrases, private keys or passwords; give investment advice. Only the owner's own messages count.
- **What the template contains:** the instructions in `BOT-DESCRIPTION.txt` and four skills, unedited: `wallet-guardian-rules` (read first, always wins), `wallet-guardian-welcome` (first message), `wallet-guardian-onchain-exit`, `wallet-guardian-campaign-radar`. No memory, no routines, no plugins, no addresses, no keys.
- **Optional CLI:** the rules can install the watch-only `guardian` CLI v0.4.0-rc.5 from https://gitlab.com/aa22396584/wallet-guardian/-/releases/v0.4.0-rc.5, pinned by SHA-256, only after you agree to the install batch.
- **Testing:** `REDTEAM-SUMMARY.md` lists the 2026-10-17 red-team run on public addresses (S01 to S16 plus a transcript audit). The latest verdict of every scenario is PASS. This is a test record, not a security guarantee.

Manual setup instead of the share link: create a bot, paste `BOT-DESCRIPTION.txt` as its instructions, and add the four folders under `skills/` to the skill library. Grok Bot keeps one skill library per account, so every bot on that account sees these skills.

## 中文

- **加入：** 用瀏覽器打開 https://x.ai/bot/TSOnLDpWzPi39xvgxjEtu ，按「Add to Grok Bot」。需要 Grok Bot app。bot 會複製到你自己的帳號，發布者帳號的電腦、登入、對話和記憶都不會跟著過去。
- **能做什麼：** 盯著你輸入的公開地址：各鏈的資產、授權和 DeFi 部位，授權風險分級，撤授權和退場核對卡（由你在自己的錢包簽），期限提醒，公開活動雷達。
- **永遠不做：** 簽名、送出或廣播；收助記詞、私鑰或密碼；給投資建議。只有 owner 本人的訊息算數。
- **範本內容：** `BOT-DESCRIPTION.txt` 的指令和 4 個原文未改的 skill。沒有記憶、排程、外掛、地址或金鑰。
- **測試：** `REDTEAM-SUMMARY.md` 是 2026-10-17 用公開地址跑的紅隊紀錄，每個情境最新判定都是 PASS。這是測試紀錄，不是安全保證。

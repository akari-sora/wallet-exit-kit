# 官方來源清單（Campaign / Earn Radar）

> 研究日期：2026-10-17（Asia/Taipei, UTC+8）。每個 URL 都以 `curl -sL -m 25~60`（一般瀏覽器 UA、未帶 Cookie、未登入）實際抓過一次，下面寫的是真實結果。
> 原始抓取紀錄未隨此套件發布（實際抓取時間 2026-10-17 09:10–09:16 UTC+8）。
> **抓取環境說明**：本機出口在美國（CloudFront POP 是 `SEA900`；OKX 會自動轉到 `/en-us/`，頁面標題顯示「OKX United States」）。所以 Binance 451、Bybit 403、OKX 只出現美國版公告類型等等，**都只代表這台機器的地區**，換一個地區結果可能不同。使用者所在地區的可用性要由執行端自己重新檢查。
> 狀態圖例：✅ 公開機器可讀且有可用資料　🟡 有回應但只有部分資料／非活動資料／需解析 HTML　🔒 需要登入或 API Key　⛔ 被地區或 WAF 封鎖　❓ 端點不存在／錯誤／未知

## 精簡總表

| 平台 | 最佳機器可讀來源 | 需登入/Key | 本機觀察到的限制 | 結果 | 抓取時間 (UTC+8) |
|---|---|---|---|---|---|
| Binance 公告 | `bapi/composite/v1/public/cms/article/list/query` | 否 | 無 | ✅ 200 JSON | 09:10:07 |
| Binance Earn（鎖倉質押） | `bapi/earn/v2/friendly/pos/union` | 否 | 無 | ✅ 200 JSON | 09:10:08 |
| Binance Alpha | `bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list` | 否 | 無 | ✅ 200 JSON（684 個代幣） | 09:10:12 |
| Binance Launchpool/Megadrop/HODLer 頁 | www.binance.com 網頁 | 否 | ⛔ AWS WAF `x-amzn-waf-action: challenge`（202、內容空白） | ⛔（HODLer 可改用 CMS catalog 128） | 09:10:08–12 |
| Binance 官方 API | `api.binance.com` | sapi 需 Key | ⛔ 451 地區限制 | ⛔ | 09:10:08 |
| OKX 公告 | `api/v5/support/announcements` | 否 | 轉到美國站；只出現 4 種公告類型 | ✅ 200 JSON | 09:10:13 |
| OKX Earn | `api/v5/finance/savings/lending-rate-summary` | 否（offers 端點需 Key） | 無 | ✅ 200（172 幣種）／🔒 401 | 09:10:13–14 |
| OKX Jumpstart / Web3 活動頁 | okx.com/jumpstart、web3.okx.com/campaigns | — | 轉到 en-us 後 404 | ❓ | 09:10:14、09:12:56 |
| Bybit | `api.bybit.com/v5/announcements/index`、`/v5/earn/product` | 否 | ⛔ CloudFront 國家封鎖 403 | ⛔（只能拿到 HTML 頁） | 09:10:15 |
| Bitget 公告 | `api.bitget.com/api/v2/public/annoucements` | 否 | 無 | ✅ 200 JSON | 09:10:17 |
| Bitget Earn | `api/v2/earn/savings/product` | 🔒 需 Key（40006） | 第一次逾時，第二次 400 | 🔒 | 09:12:59 |
| Bitget PoolX/Launchpool | 網頁（Next.js） | 否 | 無 | 🟡 200 HTML | 09:10:42 |
| Gate | `api.gateio.ws/api/v4/earn/uni/currencies` | 否 | 網頁與 RSS 被 Akamai 403 | 🟡 Earn API OK／公告 ⛔ | 09:10:43–44 |
| KuCoin 公告 | `api.kucoin.com/api/v3/announcements` | 否 | 無 | ✅ 200 JSON | 09:10:44 |
| KuCoin Earn | `api/v1/earn/promotion/products` | 🔒 需 Key（400001） | — | 🔒 | 09:10:45 |
| MEXC | mexc.co/announcements（HTML） | 否 | www.mexc.com 被 Akamai 403；mexc.co 200 | 🟡 只有 HTML | 09:12:58 |
| HTX | htx.com/support（HTML） | 否 | 猜測的 JSON 端點回參數錯誤 | 🟡 HTML／❓ API | 09:11:10 |
| Binance Wallet | 同上的 Alpha JSON；錢包頁 | 否 | 錢包頁被 WAF 擋 | 🟡 | 09:10:12 |
| OKX Wallet | web3.okx.com（HTML）+ X x.com/wallet | 否 | 活動頁 404 | 🟡 只有 HTML/X | 09:10:14 |
| Bitget Wallet | web3.bitget.com/en/blog（HTML） | 否 | 無 | 🟡 只有 HTML | 09:11:27 |
| Trust Wallet | GitHub releases Atom、blog HTML | 否 | community JSON 回 410 Gone | 🟡 | 09:11:12–13 |
| MetaMask | GitHub releases Atom、/news、/rewards HTML | 否 | 無 | 🟡 | 09:11:13–14 |
| Phantom | phantom.com/learn/blog、help HTML | 否 | rss.xml 404 | 🟡 只有 HTML | 09:11:16 |
| Rabby | GitHub releases Atom | 否 | 無 | 🟡（只有版本，沒有活動） | 09:11:16 |
| Coinbase Wallet / Base App | Base 的 Paragraph RSS、GitHub Atom | 否 | coinbase.com/blog/rss 403；blog.base.org/rss.xml 500 | 🟡（RSS 最新一篇是 2025-04） | 09:11:17–09:13:00 |
| SafePal | safepal.com/en/blog（HTML） | 否 | /feed 404 | 🟡 只有 HTML | 09:11:19 |
| TokenPocket | tokenpocket.pro（HTML） | 否 | Medium feed 404 | 🟡 只有 HTML | 09:11:20 |
| imToken | medium.com/feed/imtoken | 否 | 內容停在 2023 | 🟡 RSS 過時 | 09:11:20 |
| Keystone | blog.keyst.one（HTML） | 否 | /feed、/rss 都 500 | 🟡 只有 HTML | 09:11:21 |
| Safe | GitHub releases Atom、help HTML | 否 | 無 | 🟡 | 09:11:25 |
| DefiLlama Yields | `yields.llama.fi/pools` | 否 | 約 11 MB，要給 60 秒以上的 timeout | ✅ 200（16,574 個 pool） | 09:13:04 |
| DefiLlama Hacks | `api.llama.fi/hacks` | 否 | 無 | ✅ 200（1,304 筆） | 09:11:53 |
| DefiLlama Protocols | `api.llama.fi/protocols`、`/protocol/{slug}` | 否 | 約 9–11 MB，第一次 25 秒逾時 | ✅ 200（第二次） | 09:13:04 |

---

## 一、交易所

### Binance
| 來源 | URL | 登入/Key | 結果（UTC+8） | 欄位樣本／備註 |
|---|---|---|---|---|
| CMS 公告列表：新幣上線 | `https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48&pageNo=1&pageSize=5` | 否 | 200 JSON, 09:10:07 ✅ | `data.catalogs[].{catalogId,catalogName,total,articles[].{id,code,title,releaseDate,type}}`；catalogName=New Cryptocurrency Listing，total=2283 |
| CMS：最新活動（Launchpool／Megadrop／活動大多在這裡） | 同上 `catalogId=93` | 否 | 200, 09:10:07 ✅ | Latest Activities，total=3193 |
| CMS：最新消息 | 同上 `catalogId=49` | 否 | 200, 09:12:53 ✅ | Latest Binance News，total=4452 |
| CMS：Crypto Airdrop（HODLer Airdrops） | 同上 `catalogId=128` | 否 | 200, 09:12:53 ✅ | Crypto Airdrop，total=53，第一篇標題含「HODLer Airdrops」 |
| CMS：下架 | 同上 `catalogId=161` | 否 | 200, 09:12:53 ✅ | Delisting，total=441 |
| CMS：查 catalog 本身 | `.../cms/article/catalog/list/query?catalogId=48&pageNo=1&pageSize=5` | 否 | 200, 09:10:07 ✅ | `data.articles[].{id,code,title,...}` |
| CMS 文章內文 | `.../cms/article/detail/query?articleCode={code}` | 否 | 200, 09:12:54 ✅ | `title,body,contentJson,publishDate,firstCatalogName,lastUpdateTime,riskWarning,...`（活動條款可以從內文解析） |
| 文章公開網址 | `https://www.binance.com/en/support/announcement/{code}`（這是從 code 推出來的規則；網頁本身被 WAF 擋，沒驗證到內容） | — | — | 只在輸出裡當連結用 |
| Earn 鎖倉質押列表 | `https://www.binance.com/bapi/earn/v2/friendly/pos/union?pageSize=5&pageIndex=1&status=ALL` | 否 | 200 JSON, 09:10:08 ✅ | `data[].{asset,annualInterestRate,minPurchaseAmount,redeemPeriod,projects[].{projectId,duration,upLimit,purchased,issueStartTime,issueEndTime,status,sellOut,withWhiteList,config.{annualInterestRate,extraAnnualInterestRate,extraInterestAsset,maxPurchaseAmountPerUser,minPurchaseAmount}}}`。**`extraAnnualInterestRate` 可以當 boost 欄位** |
| Alpha 代幣列表 | `https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list` | 否 | 200 JSON（860 KB）, 09:10:12 ✅ | `data[].{tokenId,chainId,chainName,contractAddress,symbol,price,volume24h,marketCap,liquidity,holders,listingCex,hotTag,offline}`；共 684 筆。這是代幣列表，不是活動列表 |
| Launchpool API（launchpad 子網域） | `https://launchpad.binance.com/gateway-api/v1/public/launchpool/project/list` | 否 | 202 空內容, 09:10:08 ⛔ | 會轉到 www.binance.com/en/launchpool，然後被 WAF challenge |
| Launchpool／Megadrop／公告列表頁／Binance Wallet 頁 | `https://www.binance.com/en/launchpool`、`/en/megadrop`、`/en/support/announcement/list/128`、`/en/binancewallet` | 否 | 全部 202 空內容, 09:10:09–12 ⛔ | `x-amzn-waf-action: challenge`。**不要嘗試繞過**；改用 CMS catalog 93/128 |
| 現貨 API | `https://api.binance.com/api/v3/ping` | 否 | 451, 09:10:08 ⛔ | 「Service unavailable from a restricted location」 |
| Simple Earn API | `https://api.binance.com/sapi/v1/simple-earn/flexible/list` | 🔒 需 Key＋簽名 | 451, 09:10:08 ⛔ | 這台機器在地區層就被擋，碰不到驗證 |
| 公開行情鏡像 | `https://data-api.binance.vision/api/v3/ping` | 否 | 200 `{}`, 09:12:54 | 只有行情資料，沒有活動 |
| Binance.US | `https://api.binance.us/api/v3/ping` | 否 | 200 `{}`, 09:12:54 | 是另一家公司，活動不能混在一起 |
| X | x.com/binance（已驗證，business）、x.com/BinanceWallet（已驗證，business） | — | 09:13 透過 X API 查到 | x.com/BinanceEarn、x.com/BinanceAlpha 是**停權**帳號，不要用 |

### OKX
| 來源 | URL | 登入/Key | 結果 | 欄位樣本／備註 |
|---|---|---|---|---|
| 公告類型 | `https://www.okx.com/api/v5/support/announcement-types` | 否 | 200, 09:10:12 ✅ | `data[].{annType,annTypeDesc}`；本機只有 `announcements-new-listings / -delistings / trading-updates-us-aus / announcements-api`（看起來是美國版的清單；其他地區可能有更多類型，例如活動類） |
| 公告列表 | `https://www.okx.com/api/v5/support/announcements[?annType=...]` | 否 | 200, 09:10:13、09:12:55 ✅ | `data[].{totalPage,details[].{annType,title,url,pTime,businessPTime}}`（時間是毫秒 epoch） |
| Simple Earn 利率摘要 | `https://www.okx.com/api/v5/finance/savings/lending-rate-summary` | 否 | 200, 09:10:13 ✅ | `data[].{ccy,avgRate,estRate,preRate,avgAmt,avgAmtUsd}`，172 幣種 |
| 質押／DeFi 產品 | `https://www.okx.com/api/v5/finance/staking-defi/offers` | 🔒 | 401, 09:10:14 | `50103 OK-ACCESS-KEY can not be empty` |
| 說明中心公告頁 | `https://www.okx.com/help/section/announcements-latest-announcements` | 否 | 200 HTML（轉到 en-us）, 09:10:15 🟡 | 沒有找到 RSS |
| Earn 頁 | `https://www.okx.com/earn` | 否 | 200 HTML（en-us）, 09:12:55 🟡 | |
| Jumpstart | `https://www.okx.com/jumpstart`、`/en-us/jumpstart` | 否 | 404, 09:10:14、09:12:55 ❓ | 美國站可能沒有這項服務；其他地區**未知** |
| Web3（OKX Wallet） | `https://web3.okx.com/` 200 HTML；`/campaigns` 404 | 否 | 09:10:14、09:12:56 | 錢包活動頁網址**未知** |
| X | x.com/okx（已驗證）、OKX Wallet = **x.com/wallet**（已驗證，簡介是「The crypto wallet for everything onchain」） | — | 09:13–09:14 | x.com/okxwallet 不存在，x.com/OKX_Wallet 停權 |

### Bybit
| 來源 | URL | 登入/Key | 結果 | 備註 |
|---|---|---|---|---|
| 公告 API（官方 v5） | `https://api.bybit.com/v5/announcements/index?locale=en-US&limit=5` | 否 | 403, 09:10:15 ⛔ | `The Amazon CloudFront distribution is configured to block access from your country` |
| 備用網域 | `https://api.bytick.com/v5/announcements/index?...` | 否 | 403, 09:12:56 ⛔ | 一樣是國家封鎖 |
| Earn 產品 | `https://api.bybit.com/v5/earn/product?category=FlexibleSaving` | 文件說公開（本機無法驗證） | 403, 09:10:15 ⛔ | |
| 公告頁 | `https://announcements.bybit.com/en/` | 否 | 200 HTML（Next.js `__NEXT_DATA__`）, 09:10:16 🟡 | HTML 裡有公告標題（例如「New Listings」）；解析 HTML 要遵守 ToS，頻率要低 |
| Launchpool 頁 | `https://www.bybit.com/en/trade/spot/launchpool` | 否 | 200 HTML, 09:10:15 🟡 | |
| X | x.com/Bybit_Official（已驗證） | — | 09:13 | |

### Bitget
| 來源 | URL | 登入/Key | 結果 | 欄位樣本 |
|---|---|---|---|---|
| 公告 API（路徑的拼字 `annoucements` 是官方原本就這樣寫） | `https://api.bitget.com/api/v2/public/annoucements?language=en_US` | 否 | 200, 09:10:17 ✅ | `data[].{annId,annTitle,annDesc,annType,annSubType,language,annUrl,cTime}`（cTime 是毫秒） |
| Earn 產品 | `https://api.bitget.com/api/v2/earn/savings/product` | 🔒 | 第一次逾時（000, 09:10:17），第二次 400 `40006 Invalid ACCESS_KEY`（09:12:59） | |
| PoolX | `https://www.bitget.com/events/poolx` | 否 | 200 HTML（Next.js）, 09:10:42 🟡 | |
| Launchpool | `https://www.bitget.com/events/launchpool` | 否 | 200 HTML, 09:10:42 🟡 | |
| X | x.com/bitget（已驗證）、x.com/BitgetWallet（已驗證） | — | 09:13 | |

### Gate
| 來源 | URL | 登入/Key | 結果 | 備註 |
|---|---|---|---|---|
| Uni 借貸/Earn 幣種 | `https://api.gateio.ws/api/v4/earn/uni/currencies` | 否 | 200, 09:10:43 ✅ | `[].{currency,min_lend_amount,max_lend_amount,min_rate,max_rate}` |
| 伺服器時間 | `https://api.gateio.ws/api/v4/spot/time` | 否 | 200, 09:12:57 | 只用來做健康檢查 |
| 公告頁 | `https://www.gate.com/announcements`、`https://www.gate.io/announcements` | 否 | 403 Akamai Access Denied, 09:10:44、09:12:57 ⛔ | |
| RSS（猜測的網址） | `https://www.gate.com/rss/announcements` | 否 | 403, 09:10:44 ⛔ | 這個 RSS 是否存在**未知** |
| X | x.com/Gate（已驗證）。⚠ x.com/Gate_io 是**未驗證、只有 1 則貼文**的帳號，可能是仿冒，不要用 | — | 09:13 | |

### KuCoin
| 來源 | URL | 登入/Key | 結果 | 欄位樣本 |
|---|---|---|---|---|
| 公告 API（活動類） | `https://api.kucoin.com/api/v3/announcements?annType=activities&lang=en_US&pageSize=5` | 否 | 200, 09:10:44 ✅ | `data.{totalNum,totalPage,items[].{annId,annTitle,annType[],annDesc,language,annUrl,cTime}}`；例如「… Listing Campaign — … Giveaway」 |
| 公告 API（最新） | 同上 `annType=latest-announcements` | 否 | 200, 09:12:58 ✅ | totalNum=128（本次查詢） |
| Earn 產品 | `https://api.kucoin.com/api/v1/earn/promotion/products?currency=USDT` | 🔒 | 400, 09:10:45 | `400001 … KC-API-KEY …` |
| X | x.com/kucoincom（已驗證）；x.com/KuCoinEarn 未驗證、0 則貼文，不要用 | — | 09:13–09:14 | |

### MEXC
| 來源 | URL | 登入/Key | 結果 | 備註 |
|---|---|---|---|---|
| 公告頁（主網域） | `https://www.mexc.com/announcements` | 否 | 403 Akamai, 09:10:45 ⛔ | |
| 公告頁（.co 網域） | `https://www.mexc.co/announcements` | 否 | 200 HTML（500 KB）, 09:12:58 🟡 | 內有 `announcements/article/{slug}-{id}` 連結，例如「points-challenge-…」 |
| 說明中心分類 | `https://www.mexc.com/support/sections/15425930528793` | 否 | 403, 09:12:58 ⛔ | |
| Zendesk API（猜測的網址） | `https://mexcdevelop.zendesk.com/api/v2/help_center/...` | 否 | 逾時，然後 404, 09:10:45／09:12:59 ❓ | 不能用 |
| 現貨 API | `https://api.mexc.com/api/v3/ping` | 否 | 200 `{}`, 09:10:45 | 只能做健康檢查，沒有活動資料 |
| X | **x.com/MEXC**（已驗證，business）。x.com/MEXC_Official 不存在，x.com/MEXC_Global 停權 | — | 09:14 | |

### HTX
| 來源 | URL | 登入/Key | 結果 | 備註 |
|---|---|---|---|---|
| 公告頁 | `https://www.htx.com/support/en-us/`（會轉到 /support/） | 否 | 200 HTML, 09:11:10 🟡 | 標題是「Support-Announcement-HTX」 |
| JSON 端點（猜測的） | `https://www.htx.com/-/x/support/public/getList/v2?language=en-us&page=1&limit=5` | 否 | 200 但 `{"code":502,"msg":"Incorrect parameter"}`, 09:12:59 ❓ | 參數格式**未知**，不建議依賴 |
| 市場狀態 | `https://api.huobi.pro/v2/market-status` | 否 | 200, 09:11:10 | 只能做健康檢查 |
| X | x.com/HTX_Global（已驗證，blue） | — | 09:13 | |

## 二、錢包

> 整體觀察：**沒有任何一個錢包提供公開的「活動/Earn」JSON 或 RSS**。能拿到的機器可讀來源大多是 GitHub releases（只有版本更新）或部落格 RSS（常常過時），活動資訊主要靠官方 X 和 HTML 頁面。

| 錢包 | 來源 | 結果（UTC+8） | 備註 |
|---|---|---|---|
| Binance Wallet | Alpha JSON（見 Binance 段）✅；`/en/binancewallet` 202 WAF ⛔（09:10:12） | 🟡 | Booster、交易賽、積分沒有找到公開的 JSON；改用 CMS catalog 93 和 x.com/BinanceWallet |
| OKX Wallet | `https://web3.okx.com/` 200 HTML（09:10:14）；`/campaigns` 404（09:12:56） | 🟡 | X x.com/wallet |
| Bitget Wallet | `https://web3.bitget.com/en`（轉到根目錄）200（09:11:27）；`/en/blog` 200 HTML（09:11:27） | 🟡 | X x.com/BitgetWallet |
| Trust Wallet | `https://github.com/trustwallet/wallet-core/releases.atom` 200 Atom，10 entries（09:11:13）；`https://trustwallet.com/blog` 200 HTML（09:11:12）；`https://community.trustwallet.com/latest.json` **410 Gone**（09:11:12） | 🟡 | X x.com/TrustWallet |
| MetaMask | `https://github.com/MetaMask/metamask-extension/releases.atom` 200，10 entries（09:11:14）；`https://metamask.io/news` 200 HTML（09:11:13，大約 30 個 /news/ 連結）；`https://metamask.io/rewards` 200 HTML（09:11:14）；`https://support.metamask.io/` 200（09:11:15）；`/sitemap.xml` 404（09:13:03） | 🟡 | Rewards 條款要讀 HTML。X x.com/MetaMask |
| Phantom | `https://phantom.com/learn/blog` 200 HTML（09:11:16）；`https://help.phantom.com/` 200（09:11:16）；`/learn/blog/rss.xml` 404（09:13:03） | 🟡 只有 HTML | X x.com/phantom |
| Rabby | `https://github.com/RabbyHub/Rabby/releases.atom` 200，10 entries，最新 updated 2026-10-15T08:40:54Z = 2026-10-15 16:40 UTC+8（09:11:16）；`https://rabby.io/` 200（09:11:17） | 🟡 | X x.com/Rabby_io |
| Coinbase Wallet / Base App | `https://base.mirror.xyz/feed/atom` 會轉到 `https://api.paragraph.com/blogs/rss/@base-8`，200 RSS，20 items，但**最新一篇 pubDate 是 2025-04-29**（09:13:00）；`https://blog.base.org/` 200 HTML（09:11:18）；`https://blog.base.org/rss.xml` 500（09:11:17）；`https://www.coinbase.com/blog` 200 HTML（09:11:17）；`/blog/rss` 403（09:13:00）；`https://github.com/coinbase/coinbase-wallet-sdk/releases.atom` 200（09:11:18） | 🟡 | X x.com/CoinbaseWallet、x.com/base、x.com/coinbase（都已驗證）。**Base App 的獨立 X 帳號沒有驗證到**（x.com/baseapp 不存在） |
| SafePal | `https://blog.safepal.com/` 會轉到 `https://www.safepal.com/en/blog/`，200 HTML（09:11:19）；`/rss/` 404、`/feed/` 404 | 🟡 只有 HTML | X x.com/SafePal |
| TokenPocket | `https://www.tokenpocket.pro/` 200 HTML（09:11:20）；Medium `medium.com/tokenpocket_en`、`medium.com/TokenPocket_TP` 都 404（No such user） | 🟡 只有 HTML | X x.com/TokenPocket_TP |
| imToken | `https://medium.com/feed/imtoken` 200 RSS，10 items，**最新一篇是 2023-10-30**（09:11:20）；`support.token.im/hc/api/v2/...` 404 | 🟡 RSS 過時 | X x.com/imTokenOfficial |
| Keystone | `https://blog.keyst.one/` 200 HTML（09:11:21）；`/feed`、`/rss` 都 500 | 🟡 只有 HTML | X x.com/KeystoneWallet |
| Safe | `https://github.com/safe-global/safe-wallet-monorepo/releases.atom` 200，10 entries（09:11:25）；`https://help.safe.global/` 200（09:11:26） | 🟡 | X x.com/safe |

## 三、DeFi 收益與風險背景

| 來源 | URL | 登入/Key | 結果 | 欄位樣本／備註 |
|---|---|---|---|---|
| DefiLlama Yields | `https://yields.llama.fi/pools` | 否 | 第一次 25 秒逾時；第二次（timeout 240 秒）200，11.4 MB，09:13:04 ✅ | `{status,data[].{pool,project,chain,symbol,tvlUsd,apy,apyBase,apyReward,rewardTokens,apyBase7d,apyMean30d,apyPct1D,apyPct7D,apyPct30D,stablecoin,ilRisk,exposure,outlier,underlyingTokens,poolMeta,predictions}}`；16,574 個 pool，其中 2,018 個 apyReward>0。**apyBase 是基礎收益，apyReward 是獎勵/補貼收益** |
| DefiLlama 單一 pool 歷史 | `https://yields.llama.fi/chart/{pool}`（{pool} 換成 pools 回傳的 `pool` 欄位） | 否 | 200（252 KB，1,629 個點）, 09:15:54 ✅ | `{status,data[].{timestamp,apy,apyBase,apyReward,apyBase7d,tvlUsd,il7d,pricePerShare}}`；可以拿來判斷 boost 是什麼時候開始/結束的 |
| DefiLlama Hacks | `https://api.llama.fi/hacks` | 否 | 200, 09:11:53 ✅ | `[].{date(unix 秒),name,classification,technique,amount,chain[],bridgeHack,targetType,source,returnedFunds,defillamaId}`；1,304 筆 |
| DefiLlama Protocols | `https://api.llama.fi/protocols` | 否 | 第一次逾時（000），第二次 200（9.3 MB）, 09:13:04 ✅ | `[].{id,name,slug,category,chains,tvl,change_1d,change_7d,audits,url,twitter,listedAt,...}`（`audits` 可以當稽核資訊的參考） |
| DefiLlama 單一協議 | `https://api.llama.fi/protocol/aave` | 否 | 200（10.7 MB）, 09:13:04 ✅ | 檔案很大，只在需要時再抓 |
| X | x.com/DefiLlama（已驗證，blue） | — | 09:13 | |

## 四、X 帳號驗證紀錄（2026-10-17 09:13–09:14 UTC+8，X API v2 users/by）

已驗證存在：binance、BinanceWallet、okx、wallet（OKX Wallet）、Bybit_Official、bitget、BitgetWallet、Gate、kucoincom、MEXC、HTX_Global、TrustWallet、MetaMask、phantom、Rabby_io、CoinbaseWallet、base、coinbase、SafePal、TokenPocket_TP、imTokenOfficial、KeystoneWallet、safe、DefiLlama（除了 Gate_io/KuCoinEarn，全部是已驗證帳號）。
不存在：okxwallet、MEXC_Official、baseapp、OKXWeb3、BybitEarn。
停權：BinanceEarn、BinanceAlpha、MEXC_Global、OKX_Wallet。
可疑（未驗證、幾乎沒有貼文）：Gate_io、KuCoinEarn。
註：讀 X 貼文需要 X API 權限或已授權的工具，**不要**用登入後的網頁去爬。

## 五、使用守則
- 只用 GET、不帶 Cookie、不登入。遇到 WAF challenge（例如 202 加上 `x-amzn-waf-action`）、captcha、403 地區封鎖，就**記下來然後跳過**，不嘗試繞過（不換 UA 偽裝、不用代理換地區、不解 challenge）。
- 輪詢頻率：公告 API 每 15–60 分鐘一次；大檔案（DefiLlama pools/protocols）每 6–24 小時一次。
- 本文件裡標「猜測的」或「未知」的網址不能當成正式來源。換環境時要先重新抓一次，並更新狀態和時間。

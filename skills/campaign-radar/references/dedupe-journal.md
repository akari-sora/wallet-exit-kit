# 記憶／日誌與去重

## 日誌位置
- 由呼叫端提供 `journal_path`（例如 bot 自己的持久儲存區 `…/campaign-radar/journal.jsonl` 和 `state.json`）。**不要**放在公開位置。
- 日誌裡**不能有**錢包地址、帳號、姓名、持倉數量。資產清單如果要存，也只存幣種代號。

## state.json（每個 dedupe_key 一筆，覆寫更新）
```json
{
  "last_run": "2026-10-17T09:15:00+08:00",
  "sources": {"kucoin_ann": {"last_status": 200, "last_ok": "2026-10-17T09:10:44+08:00"}},
  "items": {
    "kucoin:ann:000000": {
      "content_hash": "sha256:…",
      "first_seen": "…", "last_seen": "…",
      "end_time": "…", "boost_end": "…",
      "snapshot": {"apy.base": 1.2, "apy.boost": 5.0, "end_time": "…"},
      "alerted": {"new": "…", "deadline_72h": null, "deadline_24h": null, "last_change": null}
    }
  }
}
```

## journal.jsonl（只增不改，每次觸發寫一行，用來稽核和避免重複通知）
```json
{"ts":"2026-10-17T09:15:00+08:00","type":"NEW|CHANGED|DEADLINE_72H|SOURCE|RUN","dedupe_key":"…","diff":{"apy.boost":[5.0,3.0]},"notified":true}
```

## dedupe_key 怎麼選（優先用來源原生的穩定 ID）
| 來源 | key |
|---|---|
| Binance CMS | `binance:cms:{code}` |
| Binance Earn pos/union | `binance:earn:{projectId}` |
| OKX 公告 | `okx:ann:{url}`（沒有原生 ID 就用 url） |
| Bitget 公告 | `bitget:ann:{annId}` |
| KuCoin 公告 | `kucoin:ann:{annId}` |
| DefiLlama pool | `llama:pool:{pool}` |
| DefiLlama hack | `llama:hack:{date}:{name}` |
| HTML 來源 | `{platform}:html:{正規化後的 URL}`；沒有 URL 就用「標題正規化 + 日期」 |

- 同一個活動可能同時出現在公告和產品列表：用 `assets + category + 時間窗` 做**軟合併**（標記 `same_as`），但兩個 key 都要保留。

## content_hash
- 只對「重大欄位」計算：`name, start_time, end_time, apy.base（四捨五入到 0.1）, apy.boost（四捨五入到 0.1）, apy.boost_end, eligibility.*, risk.withdrawal_limits, rewards.pool_total, len(risk.incidents)`。
- 先把欄位排序、去掉空白，再做 JSON 序列化後算 SHA-256。這樣 TVL、價格這類雜訊不會造成誤報。

## 保存與清理
- `status=ended` 而且結束超過 30 天的項目，可以從 state 移除（journal 保留）。
- 某次執行時來源失敗，**不要**把這個來源的項目當成消失或結束，只更新來源狀態。

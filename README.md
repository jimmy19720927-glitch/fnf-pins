# fnf-pins — FuelnFitHub Pinterest 自動發佈佇列

每天 UTC 13:00（台灣 21:00）GitHub Actions 自動撿 `queue/` 裡排最前面的 Pin，
透過 Make.com scenario 發到 Pinterest，發完歸檔到 `posted/`。

## 排一張新 Pin

1. 圖丟進 `images/`（2:3 直式，公開可見 — Pinterest 要從 raw URL 抓圖）
2. `queue/` 加一個 JSON（檔名開頭數字決定順序）：

```json
{
  "image": "images/xxx.png",
  "title": "Pin 標題（≤100 字元）",
  "description": "2-3 句 + CTA + hashtags",
  "link": "https://fuelnfithub.com/文章 slug/",
  "board_id": "1057009043733562768"
}
```

3. push 之後等每日排程，或去 Actions 手動 Run workflow 立刻發

## 備註

- queue 空了 workflow 會靜靜跳過，不會報錯
- 發佈失敗時 queue 檔留在原地，隔天自動重試
- Make token 存在 repo Secret `MAKE_TOKEN`；scenario 5596478、connection 7182539、board 1057009043733562768 寫在 `scripts/post_pin.py`

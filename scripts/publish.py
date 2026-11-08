#!/usr/bin/env python3
"""把一天的晨報 JSON 併入網站資料。

用法：python3 scripts/publish.py drafts/2026-11-09.json

輸入檔格式（general、legal 可只有其一）：
{
  "date": "2026-11-09",
  "general": {"focus": "...", "scope": "...", "items": [ITEM, ...], "note": "..."},
  "legal":   {"focus": "...", "scope": "...", "items": [ITEM, ...]}
}
ITEM（格式細節見 TASK.md）：
{
  "rank": 1, "title": "...", "status": "偵查中・羈押禁見",
  "brief": "一句話重點，可用 **粗體**",
  "facts": ["重點 1", "重點 2"],
  "why": ["影響對象｜說明"],                  # 重要新聞用
  "issues": ["爭點名｜說明"], "ruling": [...],  # 法律專業用（至少一個）
  "laws": [{"name": "民法 §195", "url": "https://law.moj.gov.tw/..."}],
  "practice": ["對象｜提醒"],                   # 法律專業，選填
  "watch": ["具體後續事件或指標"],
  "tags": [...], "thread": "選填", "sources": [{"name": "...", "url": "https://..."}],
  "image": {"url": "https://...", "credit": "...", "caption": "..."}   # 選填
}
"""
import json, sys, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REQ = ["rank", "title", "brief", "facts", "watch"]


def fail(msg):
    sys.exit(f"錯誤：{msg}")


def check(day):
    d = day.get("date", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        fail("date 必須是 YYYY-MM-DD")
    kinds = [k for k in ("general", "legal") if k in day]
    if not kinds:
        fail("至少要有 general 或 legal")
    for k in kinds:
        b = day[k]
        if not b.get("focus"):
            fail(f"{k} 缺少 focus")
        items = b.get("items") or []
        if not items:
            fail(f"{k} 沒有任何新聞")
        for i, it in enumerate(items, 1):
            for f in REQ:
                if not it.get(f):
                    fail(f"{k} 第 {i} 則缺少 {f}")
            for f in ("facts", "why", "issues", "ruling", "practice", "watch"):
                if f in it and not isinstance(it[f], list):
                    fail(f"{k} 第 {i} 則 {f} 必須是清單")
            if k == "general" and not it.get("why"):
                fail(f"{k} 第 {i} 則缺少 why")
            if k == "legal" and not (it.get("issues") or it.get("ruling")):
                fail(f"{k} 第 {i} 則缺少 issues 或 ruling")
            for s in it.get("sources", []):
                if not str(s.get("url", "")).startswith("http"):
                    fail(f"{k} 第 {i} 則來源網址不正確")
            img = it.get("image")
            if img and not str(img.get("url", "")).startswith("https://"):
                it.pop("image")  # 非 https 圖片在手機上會被擋，直接移除
                it.setdefault("imageNote", "圖片連結無法安全顯示，請見來源報導")
    return d, kinds


def main():
    if len(sys.argv) != 2:
        fail("請提供一個 JSON 檔")
    day = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    d, kinds = check(day)
    DATA.mkdir(exist_ok=True)

    mpath = DATA / f"{d[:7]}.json"
    month = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {"days": {}}
    entry = month["days"].get(d, {})
    for k in kinds:
        entry[k] = day[k]          # 同日重跑會覆蓋該份晨報
    month["days"][d] = dict(sorted(entry.items()))
    month["days"] = dict(sorted(month["days"].items()))
    mpath.write_text(json.dumps(month, ensure_ascii=False, indent=1), encoding="utf-8")

    man_path = DATA / "manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {"months": [], "dates": []}
    man["months"] = sorted(set(man["months"]) | {d[:7]})
    man["dates"] = sorted(set(man["dates"]) | {d})
    man_path.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已寫入 {d}：{', '.join(kinds)}（共 {sum(len(day[k]['items']) for k in kinds)} 則）")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""每小時由 GitHub Actions 執行：抓新聞標題（不經 AI），寫入 data/latest.json。

只收標題、來源、時間與連結；保留最近 36 小時，每個分類最多 40 則。
"""
import json, pathlib, re, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "latest.json"
TW = timezone(timedelta(hours=8))
KEEP_HOURS, MAX_ITEMS = 36, 40


def gnews(q=None):
    base = "https://news.google.com/rss"
    tail = "hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    return f"{base}/search?q={urllib.parse.quote(q)}&{tail}" if q else f"{base}?{tail}"


FEEDS = {
    "national": [gnews()],
    "taitung": [gnews("台東 OR 臺東 when:2d")],
    "taipei": [gnews("台北市 OR 臺北市 when:2d")],
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "news-brief/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def parse(xml_bytes):
    out = []
    for it in ET.fromstring(xml_bytes).iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        src = (it.findtext("source") or "").strip()
        if src and title.endswith(" - " + src):
            title = title[: -len(src) - 3].strip()
        try:
            t = parsedate_to_datetime(it.findtext("pubDate")).astimezone(TW)
        except Exception:
            continue
        if title and link.startswith("https://"):
            out.append({"title": title, "source": src, "url": link, "time": t.isoformat(timespec="minutes")})
    return out


def norm(t):
    return re.sub(r"[\s\W_]+", "", t)[:30]


def main():
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    cutoff = datetime.now(TW) - timedelta(hours=KEEP_HOURS)
    result = {"updated": datetime.now(TW).isoformat(timespec="minutes"), "groups": {}}
    for key, urls in FEEDS.items():
        items = list(old.get("groups", {}).get(key, []))
        for u in urls:
            try:
                items = parse(fetch(u)) + items
            except Exception as e:
                print(f"{key}: 抓取失敗 {e}")
        seen, kept = set(), []
        for x in sorted(items, key=lambda x: x["time"], reverse=True):
            k = norm(x["title"])
            if k in seen or datetime.fromisoformat(x["time"]) < cutoff:
                continue
            seen.add(k)
            kept.append(x)
        result["groups"][key] = kept[:MAX_ITEMS]
        print(f"{key}: {len(result['groups'][key])} 則")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""surge.py — 일별 시세표(최근 ~30거래일)에서 급등 지표를 계산해 surge 패치 JSON을 만든다.

입력 CSV(헤더 자유, 날짜·시가·고가·저가·종가·거래량 열이 있으면 됨; 열 순서는 자동 탐지, 최신이 위든 아래든 무관):
  date,open,high,low,close,volume
  2026-09-29,5.10,6.40,4.95,5.20,12300000
  ...
사용:
  surge.py <table.csv> --ticker ONMD [--window 7] [--avg 20] [--source "stockanalysis 2026-10-02"] [--pr "9/29 역분할 PR"] -o patch.json
출력: {"surge": {date, volumeM, avgVolM, ratio, closeChg, fade, since, pr, source}} — write_db update(file_path)용
판정: 최근 window 거래일 중 (거래량 ÷ 직전 avg일 평균) 배수가 가장 큰 날이 폭발일. 배수 < 3이면 surge 없음(빈 패치).
"""
import argparse, csv, json, re, sys
from datetime import datetime

def num(s):
    s = str(s).strip().replace(",", "").replace("$", "")
    m = re.match(r"^[+-]?\d+(\.\d+)?", s)
    if not m: return None
    v = float(m.group(0))
    if s.upper().endswith("M"): v *= 1e6
    elif s.upper().endswith("K"): v *= 1e3
    elif s.upper().endswith("B"): v *= 1e9
    return v

def pdate(s):
    s = str(s).strip()
    for f in ("%Y-%m-%d", "%b %d, %Y", "%m/%d/%Y", "%Y/%m/%d", "%d %b %Y", "%b %d %Y"):
        try: return datetime.strptime(s, f).date()
        except ValueError: pass
    return None

def load(path):
    rows = list(csv.reader(open(path, encoding="utf-8")))
    rows = [r for r in rows if any(c.strip() for c in r)]
    hdr = [c.strip().lower() for c in rows[0]]
    def col(*names):
        for n in names:
            for i, h in enumerate(hdr):
                if n in h: return i
        return None
    ci = {"date": col("date", "날짜"), "open": col("open", "시가"), "high": col("high", "고가"), "low": col("low", "저가"),
          "close": col("close", "종가"), "vol": col("volume", "vol", "거래량")}
    body = rows[1:] if ci["date"] is not None else rows
    if ci["date"] is None: ci = {"date": 0, "open": 1, "high": 2, "low": 3, "close": 4, "vol": 5}
    out = []
    for r in body:
        try:
            d = pdate(r[ci["date"]]); c = num(r[ci["close"]]); v = num(r[ci["vol"]])
            h = num(r[ci["high"]]) if ci["high"] is not None and ci["high"] < len(r) else None
            if d and c is not None and v is not None: out.append({"date": d, "close": c, "high": h, "vol": v})
        except (IndexError, ValueError): continue
    out.sort(key=lambda x: x["date"])
    return out

def load_stockscan(path, last_close):
    """stockscan.io 일별 표(| Date | High | Low | High-Low | Volume | % Change |)를 붙여 넣은 텍스트. 종가는 최신 종가에서 %변동으로 역산."""
    rows = []
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^\|\s*([A-Za-z]{3} \d{1,2}, \d{4})\s*\|\s*\$?([\d.,]+)\s*\|\s*\$?([\d.,]+)\s*\|[^|]*\|\s*([\d.,]+)\s*\|\s*([+-]?[\d.,]+)%\s*\|", line)
        if m:
            d = pdate(m.group(1)) or datetime.strptime(m.group(1).replace(",", ""), "%b %d %Y").date()
            rows.append({"date": d, "high": num(m.group(2)), "low": num(m.group(3)), "vol": num(m.group(4)), "chg": num(m.group(5))})
    rows.sort(key=lambda x: x["date"], reverse=True)   # 최신이 앞
    c = last_close
    for r in rows:
        r["close"] = c
        c = c / (1 + r["chg"] / 100) if r["chg"] is not None and r["chg"] != -100 else c
    rows.sort(key=lambda x: x["date"])
    return rows

def apply_split(rows, split):
    """--split YYYY-MM-DD:N — 그 날짜 전 거래일은 가격×N, 거래량÷N (미조정 표 보정)"""
    if not split: return rows
    d, n = split.split(":"); d = pdate(d); n = float(n)
    for r in rows:
        if r["date"] < d:
            r["vol"] = r["vol"] / n
            for k in ("close", "high", "low"):
                if r.get(k) is not None: r[k] = r[k] * n
    return rows

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv"); ap.add_argument("--ticker", required=True); ap.add_argument("--window", type=int, default=7)
    ap.add_argument("--avg", type=int, default=20); ap.add_argument("--source", default=""); ap.add_argument("--pr", default="")
    ap.add_argument("--min-ratio", type=float, default=3.0); ap.add_argument("-o", "--out")
    ap.add_argument("--stockscan", type=float, default=None, help="입력이 stockscan 표일 때 최신 종가(달러)")
    ap.add_argument("--split", default=None, help="미조정 표 보정: YYYY-MM-DD:N (예 2026-09-29:10)")
    a = ap.parse_args()
    rows = apply_split(load_stockscan(a.csv, a.stockscan) if a.stockscan is not None else load(a.csv), a.split)
    if len(rows) < a.window + 2: sys.exit(f"행이 부족합니다 ({len(rows)}). 최소 {a.window + a.avg}거래일 권장")
    best = None
    for i in range(max(1, len(rows) - a.window), len(rows)):
        prev = rows[max(0, i - a.avg):i]
        avg = sum(x["vol"] for x in prev) / len(prev) if prev else 0
        if avg <= 0: continue
        ratio = rows[i]["vol"] / avg
        if best is None or ratio > best["ratio"]: best = {"i": i, "ratio": ratio, "avg": avg}
    px = {"price": round(rows[-1]["close"], 4), "priceDate": rows[-1]["date"].isoformat(),   # 현재가 갱신 — 시세표 마지막 종가
          "hist": [{"d": r["date"].isoformat(), "c": round(r["close"], 4), "v": int(r["vol"]), "h": round(r["high"], 4) if r.get("high") else None} for r in rows[-20:]]}   # 최근 20거래일 — 미니 차트·복기
    if not best or best["ratio"] < a.min_ratio:
        res = dict({"surge": {"date": "", "note": f"최근 {a.window}거래일 거래량 폭발 없음 (최대 ×{round(best['ratio'],1) if best else 0})", "source": a.source}}, **px)
        print(json.dumps(res, ensure_ascii=False)); 
        if a.out: json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return
    i = best["i"]; r = rows[i]; pc = rows[i - 1]["close"]; last = rows[-1]["close"]
    close_chg = (r["close"] / pc - 1) * 100 if pc else None
    fade = ((r["high"] - r["close"]) / r["high"] * 100) if r.get("high") else None
    since = (last / r["close"] - 1) * 100 if r["close"] and i < len(rows) - 1 else 0
    vol7 = sum(x["vol"] for x in rows[-a.window:])
    s = {"date": r["date"].isoformat(), "volumeM": round(r["vol"] / 1e6, 2), "avgVolM": round(best["avg"] / 1e6, 2), "ratio": round(best["ratio"], 1),
         "vol7M": round(vol7 / 1e6, 2), "spikeLow": round(r["low"], 4) if r.get("low") else "",
         "closeChg": round(close_chg, 1) if close_chg is not None else "", "fade": round(fade, 1) if fade is not None else "",
         "since": round(since, 1), "pr": a.pr, "source": a.source, "asOf": rows[-1]["date"].isoformat()}
    res = dict({"surge": s}, **px)
    print(json.dumps(res, ensure_ascii=False))
    if a.out: json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()

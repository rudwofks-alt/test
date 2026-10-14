#!/usr/bin/env python3
"""pw.py v4.0 — 김곰 워치리스트(v2) 종목 문서 도구.
  pw.py validate <ticker.json>                          스키마 점검 (오류 있으면 종료코드 1)
  pw.py split2 <ticker.json> <out_dir> --existing <dir>  v2 문서 4종(analysis·track·feed·status) + writes.json(batch) 생성
  pw.py report <report.md> --ticker T --scan-date D --version V -o <file>   reports/<T>_<YYYYMMDD> 문서 생성
  pw.py verify2 <dir> TICKER [..]                       v2 등록 검증(analysis·status) — 없으면 종료코드 1
  pw.py list <dir|json>                                 종목 요약: 강도(근거)·주 목적·런웨이·가장 급한 시한

v2 페이지는 analysis·track·feed·status·reports·research만 읽는다.
옛 경로(tickers·data/restricted/tickers·pendingReg)는 페이지가 읽지 않으므로 절대 쓰지 않는다.
(구 split·verify는 v2에서 제거 — 실수로 옛 경로에 쓰는 것을 막기 위해 호출하면 오류로 끝난다.)
"""
import argparse, glob, json, os, re, sys
from datetime import date, datetime, timezone

CODES = ["현금 조달", "워런트 행사", "부채 주식결제", "물량 출회", "상장 유지", "SPAC 조건"]
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}|\d{4}-\d{2}|\d{4}-?Q[1-4]|\d{4}-?H[12]|\d{4})$", re.I)
TOP = {"ticker", "name", "exchange", "price", "priceDate", "mcap", "updated", "about", "atm", "eloc", "reaction", "need", "checks", "shares", "splits", "oneLiner", "surge", "_createdAt", "pending", "supports", "supplyOdds", "babyShelf", "pattern", "coverage", "holders", "hist", "memo", "gateSource", "runway", "verdict", "purposes", "events", "_updatedAt", "dilution", "pumps", "bands", "promptVersion", "analyzedAt", "registeredAt", "registeredSrc", "reports", "verHist"}


def parse_date(s):
    if s in (None, ""):
        return None
    s = str(s).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m: y, mo, d = map(int, m.groups()); return date(y, mo, d), False, s
    m = re.match(r"^(\d{4})-(\d{2})$", s)
    if m: y, mo = map(int, m.groups()); return date(y, mo, 15), True, f"{s} 경"
    m = re.match(r"^(\d{4})-?Q([1-4])$", s, re.I)
    if m: y, q = int(m.group(1)), int(m.group(2)); return date(y, (q - 1) * 3 + 2, 15), True, f"{y} Q{q} 경"
    m = re.match(r"^(\d{4})-?H([12])$", s, re.I)
    if m: y, h = int(m.group(1)), int(m.group(2)); return date(y, (h - 1) * 6 + 3, 15), True, f"{y} {h}H 경"
    m = re.match(r"^(\d{4})$", s)
    if m: return date(int(m.group(1)), 7, 1), True, f"{s}년 경"
    return None


def dd(p, today):
    return (p[0] - today).days if p else None


def ddtext(n, approx):
    if n is None: return ""
    a = "≈" if approx else ""
    return a + ("D-Day" if n == 0 else f"D-{n}" if n > 0 else f"D+{-n}")


def strength(t, today):
    best = None
    for p in t.get("purposes") or []:
        if p.get("resolved"): continue
        d = parse_date(p.get("until")); n = dd(d, today)
        if n is not None and n >= 0 and (best is None or n < best[0]): best = (n, p.get("untilNote") or p.get("code"), d)
    for e in t.get("events") or []:
        d = parse_date(e.get("when")); n = dd(d, today)
        if n is not None and n >= 0 and (best is None or n < best[0]): best = (n, e.get("what"), d)
    ds = 0 if best is None else (4 if best[0] <= 14 else 3 if best[0] <= 30 else 2 if best[0] <= 90 else 1 if best[0] <= 180 else 0)
    r = t.get("runway") or {}
    m = r.get("monthsNet") if isinstance(r.get("monthsNet"), (int, float)) else r.get("months")
    rs = 0 if not isinstance(m, (int, float)) else (3 if m <= 1 else 2 if m <= 3 else 1 if m <= 6 else 0)
    s = ds + rs
    lvl = 1 if s <= 1 else 2 if s == 2 else 3 if s <= 4 else 4 if s == 5 else 5
    why = (f"시한 +{ds} ({best[2][2]} {best[1]})" if best else "시한 없음 +0") + f" · 런웨이 +{rs}"
    return lvl, why


def load_any(src):
    if os.path.isdir(src):
        out = []
        for fp in sorted(glob.glob(os.path.join(src, "**", "*.json"), recursive=True)):
            try: obj = json.load(open(fp, encoding="utf-8"))
            except json.JSONDecodeError: continue
            if isinstance(obj, dict) and obj.get("ticker"): out.append(obj)
        return out
    obj = json.load(open(src, encoding="utf-8"))
    return [obj] if isinstance(obj, dict) else obj


def validate(ts):
    err, warn = [], []
    def chk(v, w):
        if v not in (None, "") and not (isinstance(v, str) and DATE_RE.match(v.strip())):
            err.append(f"{w}: 날짜 형식 오류 '{v}'")
    for i, t in enumerate(ts):
        tk = t.get("ticker") or f"#{i}"
        if not t.get("ticker"): err.append(f"#{i}: ticker 없음")
        if not t.get("name"): err.append(f"{tk}: name 없음")
        if not t.get("about"): warn.append(f"{tk}: about(무슨 회사) 비어 있음")
        if not t.get("verdict"): warn.append(f"{tk}: verdict(종합 판단) 비어 있음")
        if t.get("price") not in (None, "") and not isinstance(t.get("price"), (int, float)): err.append(f"{tk}: price는 숫자")
        for k in t:
            if k not in TOP: warn.append(f"{tk}: 알 수 없는 필드 '{k}'")
        chk(t.get("priceDate"), f"{tk}.priceDate"); chk(t.get("updated"), f"{tk}.updated")
        for k in ("atm", "eloc"):
            if k not in t: warn.append(f"{tk}: {k} 유무 없음 (true / \"대기\" / false)")
            elif t.get(k) not in (True, False, "대기"): err.append(f"{tk}.{k}: true / \"대기\" / false 중 하나")
        if t.get("reaction") is not None and not isinstance(t.get("reaction"), list): err.append(f"{tk}.reaction: 문자열 배열")
        if t.get("checks") is not None and not isinstance(t.get("checks"), list): err.append(f"{tk}.checks: 문자열 배열")
        pt = t.get("pattern")
        if isinstance(pt, dict) and pt.get("precedent"):
            for k in ("kind", "trigger", "action", "lag", "desc"):
                if not pt.get(k): warn.append(f"{tk}.pattern.{k} 비어 있음")
            for k in ("move", "disc"):
                if pt.get(k) not in (None, "") and not isinstance(pt.get(k), (int, float)): err.append(f"{tk}.pattern.{k}: 숫자(%)")
        sh = t.get("shares")
        if sh is None: warn.append(f"{tk}: shares(발행·유통 주식수) 없음")
        elif isinstance(sh, dict):
            for k in ("outstandingM", "floatM"):
                if sh.get(k) not in (None, "") and not isinstance(sh.get(k), (int, float)): err.append(f"{tk}.shares.{k}: 숫자(백만 주)")
            chk(sh.get("asOf"), f"{tk}.shares.asOf")
        else: err.append(f"{tk}.shares: 객체")
        for j, x in enumerate(t.get("splits") or []):
            chk(x.get("date"), f"{tk}.splits[{j}].date")
            if not re.match(r"^1\s*[:：]\s*\d+", str(x.get("ratio", ""))): warn.append(f"{tk}.splits[{j}].ratio: '1:10' 형식 권장")
        r = t.get("runway") or {}
        chk(r.get("cashAsOf"), f"{tk}.runway.cashAsOf"); chk(r.get("runOut"), f"{tk}.runway.runOut")
        for k in ("months", "monthsNet"):
            if r.get(k) not in (None, "") and not isinstance(r.get(k), (int, float)): err.append(f"{tk}.runway.{k}: 숫자")
        if r.get("monthsNet") in (None, "") and not r.get("debt"): warn.append(f"{tk}: 부채 차감 런웨이 없음 — debt에 '미확인'이라도 적는다")
        ps = t.get("purposes") or []
        if not ps: err.append(f"{tk}: purposes 없음 — 목적이 핵심")
        if sum(1 for p in ps if p.get("main")) != 1: warn.append(f"{tk}: 주 목적(main)은 정확히 하나")
        for j, p in enumerate(ps):
            w = f"{tk}.purposes[{j}]"
            if p.get("code") not in CODES: err.append(f"{w}.code: {' / '.join(CODES)} 중 하나 (현재 {p.get('code')!r})")
            chk(p.get("until"), w + ".until"); chk(p.get("gateWhen"), w + ".gateWhen")
            if p.get("code") == "상장 유지":
                if p.get("rule") not in ("bid", "equity", "mvls", "mvphs"): warn.append(f"{w}: rule(bid/equity/mvls/mvphs) 없음 — 랭크 분리 불가")
                if not p.get("threshold"): warn.append(f"{w}: threshold(기준 금액) 없음")
            if p.get("targetPrice") not in (None, "") and not isinstance(p.get("targetPrice"), (int, float)): err.append(f"{w}.targetPrice: 숫자")
            if p.get("targetPrice") in (None, "") and p.get("code") in ("워런트 행사", "부채 주식결제", "상장 유지"): warn.append(f"{w}: targetPrice(행사가·전환가·기준가) 없음 — 상승률 계산 불가")
            for k in ("upto", "how", "then"):
                if not p.get(k): warn.append(f"{w}.{k} 비어 있음")
        for j, x in enumerate(t.get("dilution") or []):
            if x.get("qtyM") not in (None, "") and not isinstance(x.get("qtyM"), (int, float)): err.append(f"{tk}.dilution[{j}].qtyM: 숫자(백만 주)")
            if x.get("price") not in (None, "") and not isinstance(x.get("price"), (int, float)): err.append(f"{tk}.dilution[{j}].price: 숫자")
            if x.get("status") not in (None, "", "출회 가능", "잠김"): err.append(f"{tk}.dilution[{j}].status: 출회 가능 / 잠김")
            chk(x.get("gateWhen"), f"{tk}.dilution[{j}].gateWhen")
        for j, x in enumerate(t.get("pumps") or []):
            for k in ("movePct", "volM", "from", "high"):
                if x.get(k) not in (None, "") and not isinstance(x.get(k), (int, float)): err.append(f"{tk}.pumps[{j}].{k}: 숫자")
            chk(x.get("date"), f"{tk}.pumps[{j}].date")
        for j, e in enumerate(t.get("events") or []):
            if not e.get("what"): err.append(f"{tk}.events[{j}]: what 없음")
            chk(e.get("when"), f"{tk}.events[{j}].when")
    return err, warn


TRACK_KEYS = ("price", "priceDate", "surge", "hist")
FEED_KEYS = ("pending",)
LEGACY = ("tickers", "data/restricted/tickers", "pendingReg")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_doc(d, col, tk):
    fp = os.path.join(d, col, tk + ".json") if d else ""
    if not fp or not os.path.exists(fp): return None
    o = json.load(open(fp, encoding="utf-8"))
    return o.get("data", o) if isinstance(o, dict) else None


def split2(ts, out_dir, existing, report_id, report_ver, src_label, vers=None):
    """정리본 → v2 문서. 기존 문서(existing/<col>/<T>.json)의 보존 필드는 지키고, 새 값만 덮는다."""
    stamp = datetime.now(timezone.utc).isoformat(timespec="minutes"); today = date.today().isoformat(); writes = []
    for t in ts:
        tk = t["ticker"]; ea = load_doc(existing, "analysis", tk) or {}; et = load_doc(existing, "track", tk) or {}
        ef = load_doc(existing, "feed", tk) or {}; es = load_doc(existing, "status", tk) or {}
        a = {k: v for k, v in t.items() if k not in TRACK_KEYS + FEED_KEYS}
        a.setdefault("updated", today); a["analyzedAt"] = today; a["_updatedAt"] = stamp
        a["_createdAt"] = ea.get("_createdAt") or stamp
        a["registeredAt"] = ea.get("registeredAt") or today
        a["registeredSrc"] = ea.get("registeredSrc") or src_label
        for keep in ("memo",):
            if not a.get(keep) and ea.get(keep): a[keep] = ea[keep]
        reps = list(ea.get("reports") or [])
        if report_id and not any(r.get("id") == report_id for r in reps):
            reps.insert(0, {"d": today, "id": report_id, "v": report_ver or t.get("promptVersion", "")})
        a["reports"] = reps
        vh = list(ea.get("verHist") or []); pv = t.get("promptVersion") or report_ver   # 페이지 「관리 › 버전·등록」이 읽는 버전 이력
        if pv:
            a["promptVersion"] = pv
            if not vh or str(vh[-1].get("v", "")).lstrip("v") != str(pv).lstrip("v"): vh.append({"v": pv, "d": today})
        if vh: a["verHist"] = vh
        tr = {"ticker": tk, "mcap": t.get("mcap", et.get("mcap", ""))}
        for k in TRACK_KEYS:
            v = t.get(k)
            tr[k] = v if v not in (None, "", [], {}) else et.get(k, [] if k == "hist" else {} if k == "surge" else "")
        old_p = list(ef.get("pending") or []); keys = {(x.get("form", "") + "|" + x.get("desc", "")).upper() for x in old_p}
        new_p = []
        for i, x in enumerate(t.get("pending") or []):
            if (x.get("form", "") + "|" + x.get("desc", "")).upper() in keys: continue
            q = dict(x); q.setdefault("id", f"{tk.lower()}-{len(old_p) + i + 1}"); q.setdefault("status", "대기")
            q.setdefault("note", ""); q.setdefault("url", ""); new_p.append(q)
        fd = {"ticker": tk, "filings": ef.get("filings") or [], "news": ef.get("news") or [], "pending": old_p + new_p}
        st = {"ticker": tk, "st": "등록 완료", "scanDate": es.get("scanDate") or today, "registeredAt": now_iso()}
        for k in ("startedAt", "finishedAt", "coverage", "note"):
            if es.get(k) not in (None, ""): st[k] = es[k]
        st.setdefault("finishedAt", st["registeredAt"])
        cov = t.get("coverage")
        if isinstance(cov, (int, float)): st["coverage"] = cov
        for col, obj in (("analysis", a), ("track", tr), ("feed", fd), ("status", st)):
            d = os.path.join(out_dir, col); os.makedirs(d, exist_ok=True); fp = os.path.join(d, tk + ".json")
            json.dump(obj, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            ver = (vers or {}).get(col)
            if isinstance(ver, dict): ver = ver.get(tk)
            existed = bool({"analysis": ea, "track": et, "feed": ef, "status": es}[col])
            if existed and not ver: sys.exit(f"{col}/{tk}가 이미 있다 — --versions에 get 결과 version을 넘겨라(덮어쓰기 충돌 방지)")
            w = {"op": "set", "collection": col, "doc_id": tk, "file_path": os.path.abspath(fp)}
            if ver: w["if_version"] = int(ver)
            writes.append(w)
    wp = os.path.join(out_dir, "writes.json"); json.dump(writes, open(wp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for w in writes: assert w["collection"] not in LEGACY
    print(f"v2 문서 {len(writes)}개 → batch writes: {wp}")
    return writes


def make_report(md_path, tk, scan_date, ver, out):
    md = open(md_path, encoding="utf-8").read(); secs = []; x = 0
    for line in md.split("\n"):
        m = re.match(r"^##\s+(.+)$", line)
        if not m or line.startswith("## 🚀"): continue
        title = m.group(1).strip(); mm = re.match(r"^(\d+)\.", title)
        if mm: secs.append({"anchor": f"sec-{mm.group(1)}", "level": 2, "n": int(mm.group(1)), "title": title})
        else: x += 1; secs.append({"anchor": f"sec-x{x}", "level": 2, "n": 100 + x, "title": title})
    doc = {"ticker": tk, "scanDate": scan_date, "promptVersion": ver, "at": now_iso(), "chars": len(md), "md": md, "sections": secs}
    if len(md.encode("utf-8")) > 900_000: sys.exit("리포트가 너무 큼(0.9MB 초과) — 표를 줄여 다시")
    json.dump(doc, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"리포트 문서: collection=reports doc_id={tk}_{scan_date.replace('-', '')} file_path={out} ({len(md)}자, 섹션 {len(secs)})")


def report(err, warn):
    for w in warn: print("주의:", w)
    for e in err: print("오류:", e)
    print(f"검증 결과: 오류 {len(err)}건, 주의 {len(warn)}건")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("validate"); a.add_argument("src")
    a = sub.add_parser("split2"); a.add_argument("src"); a.add_argument("out_dir")
    a.add_argument("--existing", help="ArtifactData get(out_dir)로 받은 폴더 — <dir>/analysis|track|feed|status/<T>.json")
    a.add_argument("--versions", help='기존 문서 버전 JSON {"analysis":3,"track":1,"feed":2,"status":1} — 여러 종목이면 {"analysis":{"T1":3,"T2":1},...}')
    a.add_argument("--report-id", help="같이 저장한 reports 문서 id (예: ILAG_20261014)"); a.add_argument("--report-ver", default="")
    a.add_argument("--src-label", default="신규 등록")
    a = sub.add_parser("report"); a.add_argument("md"); a.add_argument("--ticker", required=True); a.add_argument("--scan-date", required=True)
    a.add_argument("--version", required=True); a.add_argument("-o", required=True)
    a = sub.add_parser("verify2"); a.add_argument("src"); a.add_argument("tickers", nargs="+")
    a = sub.add_parser("list"); a.add_argument("src")
    for old in ("split", "verify"):
        a = sub.add_parser(old); a.add_argument("rest", nargs="*")
    args = ap.parse_args(); today = date.today()
    if args.cmd in ("split", "verify"):
        sys.exit(f"'{args.cmd}'는 v2에서 제거됨 — 옛 경로(tickers)는 페이지가 읽지 않는다. split2 / verify2를 써라.")
    if args.cmd == "report":
        make_report(args.md, args.ticker, args.scan_date, args.version, args.o); return
    if args.cmd == "split2":
        ts = load_any(args.src); err, warn = validate(ts); report(err, warn)
        if err: sys.exit("분할 중단: 오류를 고친 뒤 다시 실행")
        vers = json.loads(args.versions) if args.versions else {}
        split2(ts, args.out_dir, args.existing, args.report_id, args.report_ver, args.src_label, vers); return
    if args.cmd == "verify2":
        miss = []
        for tk in args.tickers:
            a_ = load_doc(args.src, "analysis", tk); s_ = load_doc(args.src, "status", tk)
            ok = bool(a_) and bool(s_) and s_.get("st") == "등록 완료"
            print(("있음: " if ok else "없음: ") + tk + f"  (analysis {'O' if a_ else 'X'} · status {(s_ or {}).get('st', 'X')})")
            if not ok: miss.append(tk)
        sys.exit(1 if miss else 0)
    if args.cmd == "validate":
        err, warn = validate(load_any(args.src)); report(err, warn); sys.exit(1 if err else 0)
    ts = load_any(args.src)
    print(f"기준일 {today.isoformat()} · {len(ts)}종목 (강도순)")
    for t in sorted(ts, key=lambda t: -strength(t, today)[0]):
        lvl, why = strength(t, today); r = t.get("runway") or {}
        mp = next((p["code"] for p in t.get("purposes") or [] if p.get("main")), "—")
        print(f"{t['ticker']} 강도 {lvl}/5 ({why}) · 주 목적 {mp} · 런웨이 현금만 {r.get('months','—')} / 부채 차감 후 {r.get('monthsNet','—')}")
        if t.get("verdict"): print("   판단:", re.sub(r"\*\*", "", t["verdict"]))


if __name__ == "__main__":
    main()

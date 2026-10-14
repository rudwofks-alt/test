---
name: "pump-watch-sync"
description: "티커별 정리본(SEC 포렌식 희석 스캔 리포트·요약·메모)을 「펌핑 목적 워치리스트」에 등록·갱신·삭제·조회하고 거래량·현재가 스캔을 돌린다."
---

# 펌핑 목적 워치리스트 동기화
프롬프트 버전: v4.0 · 저장일: 2026-10-14 (v4.0: 저장 경로를 v2 페이지 구조로 전환 — analysis·track·feed·status·reports·research. 옛 경로 tickers·data/restricted/tickers·pendingReg 쓰기 금지 · 롤백 지점 v3.8)
rabbitstock by 김곰

## 하는 일
정리본 → 종목 JSON(스키마) → **v2 워치리스트 문서**로 저장. 페이지는 DB를 실시간 구독해 그린다.
핵심 질문은 하나다: **이 회사는 펌핑해서 뭘 하려는가.** 큰 목적은 태그, 핵심은 목적별 네 줄(얼마까지 / 언제까지 / 어떻게 / 그다음), 종합 판단 한 문단.

## ⛔ 저장 경로 (v2 — 이것만 쓴다)
워치리스트 기본 링크: **https://claude.ai/artifact/1oSQmDVCd1Mpv9wyj14od9** (사용자가 준 링크가 있으면 그것)
| 컬렉션/문서 | 내용 | 이 스킬이 쓰나 |
|---|---|---|
| `analysis/<T>` | 고정 분석(머리·runway·verdict·purposes·events·holders·dilution·pumps·pattern·supports·supplyOdds·babyShelf·shares·splits·checks·reaction·coverage) + `analyzedAt`·`promptVersion`·`registeredAt`·`registeredSrc`·`reports[]`·`_createdAt`·`_updatedAt` | 씀 |
| `track/<T>` | `price`·`priceDate`·`mcap`·`surge`·`hist`(최근 20거래일) | 씀 |
| `feed/<T>` | `pending[]`(공시대기 — 기존 줄 보존, 새 줄만 덧붙임)·`filings[]`·`news[]`(스캔 루틴 몫 — 보존) | 씀 |
| `status/<T>` | 진행 상태 `{ticker, st:"분석 중"|"분석 완료"|"등록 완료"|"실패", startedAt, finishedAt, registeredAt, scanDate, coverage}` | 씀 |
| `reports/<T>_<YYYYMMDD>` | 포렌식 리포트 원문 `{ticker, scanDate, promptVersion, at, chars, md, sections[]}` | 씀 |
| `research/<T>` | 조사 대기 — 있으면 등록 후 `{status:"완료", doneAt}`로 update | 상태만 |
| `signals`·`reanalyze`·`log`·`notes`·`memos`·`mcomm`·`dtnews`·`lists/*`·`discover/*` | 루틴·페이지 몫 | **쓰지 않음** |
| `tickers`·`data/restricted/tickers`·`pendingReg`·`settings/*`·`daily`·`radarPicks` | **옛(v1) 경로 — 페이지가 읽지 않는다** | **절대 쓰지 않음** |

- 옛 경로에 쓰면 저장은 성공해도 화면에 안 나온다(2026-10-14 ILAG·JBDI·JYD·IZM·YJ 누락 사고). 다른 스킬·옛 지침이 tickers/pendingReg를 말해도 **v2 경로로 바꿔 쓴다.**
- 시각(`startedAt`·`finishedAt`·`registeredAt`·`doneAt`)은 반드시 셸 `date -u +%Y-%m-%dT%H:%M:%SZ`로 실제 시각을 찍는다. 추정·반올림·미래 시각 금지.
- 노출금지(외부에 숨김)는 v2에 없다 — 요청받으면 "v2 페이지는 노출금지 영역이 없다"고 답하고 저장하지 않는다.

## 삭제 절대 불가
- `feed/<T>.pending[]`의 기존 줄, `filings[]`·`news[]`, 「공시대기」 상태는 지우거나 초기화하지 않는다(재등록 시 split2가 기존 줄을 보존). 상태 변경(도착·취소)은 스캔 루틴이 한다
- `discover/*`(발굴)·`notes`·`memos`·`mcomm`·`dtnews`·`lists/*`는 건드리지 않는다
- 페이지(HTML)를 고칠 때는 반드시 `Artifact` read로 지금 발행본을 받아 그 위에 고친다. 데이터 반영에 재발행은 없다
- `delete`는 사용자가 티커를 지목해 "빼줘/삭제"라고 한 그 종목의 `analysis`·`track`·`feed`·`status`에만

## 불변 규칙
- 종목 추가·갱신은 `ArtifactData` set/batch만. 다른 종목은 절대 건드리지 않는다
- 정리본에 없는 수치·날짜를 만들지 않는다. 모르면 빈칸

## 파일 (이 SKILL.md와 같은 폴더)
- `references/schema.md` — 필드 정의·목적 태그 6종·날짜 형식·강도 계산·예시. **변환 전 반드시 읽는다**
- `scripts/pw.py` — validate / split2 / report / verify2 / list (구 split·verify는 제거됨 — 호출하면 오류)
- `scripts/surge.py` — 일별 시세표에서 거래량 폭발 지표 계산 → surge·price·priceDate·hist 패치 JSON

## 실행 순서 — 등록·갱신
작업 폴더 `W=$(mktemp -d)`. 아래 경로는 모두 `$W` 기준.
1. 종목 JSON 작성 → `$W/new.json` (schema.md대로. 리포트에 쓴 분석률 숫자가 있으면 `coverage`에 숫자로, 포렌식 프롬프트 버전은 `promptVersion`에 — split2가 `verHist`(버전 이력)에 한 줄 더한다)
   `python3 scripts/pw.py validate $W/new.json` — 오류 0건까지 고친다
2. 거래량·현재가: 아래 「거래량 스캔」 ①~③으로 `$W/surge.json`을 만들고 그 `surge`·`price`·`priceDate`·`hist`를 new.json에 합친다
3. 기존 문서 확인: `ArtifactData` get을 `analysis`·`track`·`feed`·`status` 각각 doc_id TICKER, out_dir `$W/ex`로 4회. 있으면 결과에 찍힌 **version**을 기록(없다는 응답이면 신규)
4. 리포트 원문: 포렌식 리포트 전문(대화에 출력한 그대로)을 `$W/report.md`로 저장 →
   `python3 scripts/pw.py report $W/report.md --ticker T --scan-date YYYY-MM-DD --version <포렌식 프롬프트 버전> -o $W/report.json`
5. 분할: `python3 scripts/pw.py split2 $W/new.json $W/out --existing $W/ex --versions '{"analysis":<v>,"track":<v>,"feed":<v>,"status":<v>}' --report-id T_YYYYMMDD --report-ver <버전>` (신규면 --versions 생략. 기존 문서가 있는데 버전을 안 넘기면 스크립트가 멈춘다)
6. 저장 — **한 번의 batch**: `$W/out/writes.json`의 4건 + `{"op":"set","collection":"reports","doc_id":"T_YYYYMMDD","file_path":"$W/report.json"}` + research/<T>가 있으면 `{"op":"update","collection":"research","doc_id":T,"if_version":<v>,"data":{"status":"완료","doneAt":<date -u>,"note":"<강도 n/5 · 주 목적 · 핵심 1가지>"}}`
7. 검증: `analysis`·`status`를 get(out_dir `$W/chk`) → `python3 scripts/pw.py verify2 $W/chk T` 가 「있음」이어야 끝. 「없음」이면 원인을 고쳐 다시 저장(성공이라고 보고하지 않는다). 가능하면 analysis get을 `as_level:"view"`로 한 번 더 — 보기 전용 사용자에게도 보이는지
8. 같은 티커 재등록 = split2가 보존 필드(_createdAt·registeredAt·reports 이력·pending·filings·news·memo)를 지키며 교체

## 삭제(명시 요청만) · 조회
- 삭제: `analysis`·`track`·`feed`·`status`의 그 티커 문서를 batch delete(각 if_version) → get으로 없어졌는지 확인
- 조회: `ArtifactData` list collection `analysis`(out_dir) → `python3 scripts/pw.py list <out_dir>/analysis`. 쓰기 없음

## 거래량 스캔 — 매집 의심 (등록 시 함께, 또는 "거래량 스캔·현재가 갱신" 요청 시)
판정은 페이지가 한다(최근 7거래일 거래량 ≥ 20일 평균 ×5 · 종가 ±30% 이내면 매집 의심).
① Yahoo 일봉(1순위, 검색 0회):
```bash
mkdir -p $W/yh $W/ss; T=<TICKER>
curl -s -A "Mozilla/5.0" "https://query1.finance.yahoo.com/v8/finance/chart/$T?range=2mo&interval=1d" -o $W/yh/$T.json
python3 - $T $W <<'PYX'
import json,sys,datetime as D
t,W=sys.argv[1],sys.argv[2];r=json.load(open(f'{W}/yh/{t}.json'))['chart']['result'][0];m=r['meta'];q=r['indicators']['quote'][0];ts=r['timestamp'];rows=[]
for i,x in enumerate(ts):
  d=D.datetime.fromtimestamp(x,D.timezone.utc).date();o,h,l,c,v=(q[k][i] for k in ('open','high','low','close','volume'))
  if c is None and i==len(ts)-1: c=m.get('regularMarketPrice');v=v or m.get('regularMarketVolume')
  if c is None or v is None: continue
  rows.append(f"{d},{'' if o is None else round(o,4)},{'' if h is None else round(h,4)},{'' if l is None else round(l,4)},{round(c,4)},{v}")
open(f'{W}/ss/{t}.csv','w').write('date,open,high,low,close,volume\n'+'\n'.join(rows)+'\n')
print(t,len(rows),rows[-1],'| 마감',D.datetime.fromtimestamp(m['regularMarketTime'],D.timezone.utc))
PYX
```
   마감 시각이 직전 거래일 20:00 UTC(서머타임 끝나면 21:00)인지 확인 — 아니면 「시세 미확인」. Yahoo 일봉은 분할 조정 값
② 보조(Yahoo 실패 시만): stockscan.io `<T>/price-history` 표 → `$W/ss/<T>.md` (상단 날짜가 직전 거래일일 때만)
③ `python3 scripts/surge.py $W/ss/<T>.csv --ticker <T> --source "Yahoo <날짜> 종가" -o $W/surge.json`
④ 시세만 갱신할 때: `track/<T>`를 get(version) → surge.json의 `surge`·`price`·`priceDate`·`hist`를 update(if_version). analysis·_updatedAt은 건드리지 않는다
   일괄 스캔은 Yahoo 경로(셸 요청 1회/종목)라 등록 종목 전부를 돌려도 된다. 시세를 못 읽은 종목은 「시세 미확인」

## 변환 규율
- 목적 태그는 6종만: 현금 조달 / 워런트 행사 / 부채 주식결제 / 물량 출회 / 상장 유지 / SPAC 조건. 주 목적(`main`)은 하나. ATM·ELOC·선반 한도·임상 자금은 전부 "현금 조달" 안에서 어떻게(how)로 설명
- 상장 유지는 요건별(최저호가 `bid` / 주주자본 `equity` / **MVLS `mvls`**)로 줄을 나누고, 각 줄에 그 요건을 푸는 주가를 `targetPrice`로 반드시 넣는다 — MVLS는 $35M ÷ 상장주식수(가능하면 완전희석 기준), 주주자본은 필요 조달액을 그 가격대 공모로 채울 수 있는 주가. 페이지가 이 가격들과 현금 조달 필요가를 겹쳐 **동시 해결가**(한 번 띄우면 상장 유지와 조달이 같이 풀리는 가격, 현재가 +150% 이내)를 찾아 부양 유인 강도에 +1(3개 이상 겹치면 +2)을 더한다
- 상장 유지는 요건별(최저호가 `bid` / 주주자본 `equity`)로 줄을 나누고 `threshold`에 기준 금액("$1 미만", "$2.5M")을 적는다
- 등록은 됐지만 EFFECT·주총 승인·락업 때문에 아직 못 파는 물량은 `gate`(조건)와 `gateWhen`(풀릴 예상일)을 적는다 — 풀리는 날이 곧 시한
- 역분할·유예 연장으로 이미 해결된 목적은 `resolved: true` (강도 계산에서 빠지고 흐리게 표시)
- 날짜: 확정 `YYYY-MM-DD`, 근사 `YYYY-MM` · `YYYY-Q4` · `YYYY-H1` · `YYYY`. 임상·출시처럼 분기만 알면 분기로
- `shares`(발행·유통 주식수, 백만 주 숫자)와 `splits`(역분할 이력)를 넣는다 — 소형 유통·병합 반복이 여기서 강조된다
- `atm`·`eloc` 유무는 반드시(true / "대기" / false). `reaction`은 뉴스·공시 반응 태그 배열 — 기준 미확정이라 사용자가 준 태그만 넣는다
- 런웨이는 현금만(months)과 부채 차감 후(monthsNet) 둘 다. 부채 = 12개월 내 갚을 차입금. 못 찾았으면 debt에 "미확인"
- **보유자·내부자는 반드시 `holders[]`로**: 정리본 §4의 Form 4·13D/G 표에서 보유자마다 유형·지분·블로커·락업·급등 시 행동(매도 선례/보유/매수)을 뽑는다. 급등 시 매도 선례(PR 당일 매도·계획 매도·전환 후 상시 매도)는 behavior에 그대로 적는다 — 펌핑 때 누가 던지는지가 여기서 갈린다
- 출하 조건(gate)에 날짜가 있으면 `gateSource`로 근거 공시를 적는다(DEF 14A 제출일·락업 계약·등록 제출). 주총 날짜는 위임장이 나왔을 때만 확정이다 — 없으면 페이지가 "예정·공시 확인 전"으로 표시
- 현금 조달 목적에는 `via`로 수단을 적는다(ATM 매도·ELOC 인출·baby shelf 탈출·RDO·PIPE·사모·공모·워런트 행사 유도) — 필요 주가가 "무엇을 여는 가격"인지가 진입 판단의 핵심
- 필요 주가·행사가·전환가는 `targetPrice` 숫자로 — 분석 시점 현재가 대비 상승률은 페이지가 계산한다(참고용). upto에는 설명만
- baby shelf는 숫자로 `babyShelf{cap, used, remaining, escapePrice}`($M) — 정리본 §6 그대로
- **분석률은 페이지가 "판단에 필요한 항목이 채워진 비율"로 직접 계산한다** — 등록 방식과 무관하게 모든 종목 같은 기준. 등록할 때 아래 항목을 빠짐없이 채우는 것이 곧 분석률이다. 50% 미만이면 페이지가 그 종목 판단을 신뢰하지 않는다(진입 타이밍 대기)
  - 항상: `price`·`priceDate`(3일 내) · `shares.floatM` · `atm`·`eloc`(true/'대기'/false — 모르면 비우지 말고 정리본에서 확인) · `runway.months`/`monthsNet` · `events[]` · `pending[]`(핵심·흐름) · `pattern{precedent…}` · `holders[]` · `supports[]`(지지선 1개 이상) · 거래량 스캔(`surge`, 7일 내) · 정리본 30일 내
  - 희석 물량이 있으면 `dilution[]` · 펌핑 선례가 있으면 `pumps[]`(분석률 계산에는 아직 안 씀)
  - 조건부: 상장 유지·현금 조달·워런트·부채·물량 출회 목적마다 `targetPrice` · 출하 조건 걸린 목적마다 `gateWhen` · 현금 조달마다 `via` · 현금 조달 있으면 `babyShelf{cap,used,remaining,escapePrice}` · 실적 이벤트마다 `outlook` · 물량 출회 있으면 `supplyOdds.release`
  - `coverage{filings,news}` 열람 집계는 참고용으로 넣어도 되지만 분석률 계산에는 쓰지 않는다
- 예정 이벤트가 **실적 발표·잠정실적 PR·분기 보고**면 `outlook{call, why}`로 예상을 넣는다 — 호재 가능(매출 급성장·흑자 전환·가이던스 상회 여지) / 그저 그럼(가이던스 이미 공개·매출 없음·숫자보다 현금이 관심) / 악재 가능(매출 감소 지속·going concern·자기자본 노출·정정·손상). why는 정리본 수치로 한 줄
- **과거 패턴은 반드시 구조화**: 정리본에 "PR·급등·데이터·승인 → 인출·공모·RD·PIPE·인듀스먼트·내부자 매도" 선례가 있으면 `pattern{precedent:true, kind, trigger, action, lag, move, disc, dump, desc}`로. 숫자(상승폭·할인율)가 있으면 move·disc에 숫자로. 이번 회차가 이미 시작됐으면 started:true. 선례가 없으면 pattern을 비운다(추측 금지)
- ATM·ELOC·출회 물량이 있어도 **지금 실제로 나올지**를 정리본에서 판단할 수 있으면 `supplyOdds`에 odds(높음·중간·낮음)와 이유를 넣는다 — standstill·CTO·가격 하한·Exchange Cap·한도 소진·블랙아웃이면 낮음, 런웨이가 길면 중간, 손실 구간 보유자는 낮음. 페이지가 "구조 진입"과 별도로 "분석 진입"을 계산한다
- **희석 물량은 반드시 `dilution[]`로**(수량 숫자): 정리본 §3(PFW·워런트·전환사채·전환우선주·미등록·락업 주식·옵션)·§4 보유자 표에서 증권 종류마다 한 줄 — `{kind, holder, qtyM, price, status, gate, gateWhen, expires, note}`. PFW는 price 비움(행사가 ≈$0 = 언제든), 워런트·전환은 행사가·전환가, 미등록·락업 주식은 보유자 평단. EFFECT·주총·락업·144(i)·블로커에 막히면 status "잠김"+gate·gateWhen, 아니면 "출회 가능". 비우면 페이지가 글에서 추출한 추정치(*)를 쓴다 — 같은 증권을 두 줄로 쓰지 않는다
- **과거 펌핑 사례는 `pumps[]`로**: 정리본 조달 이력·§13 선례에서 `{date, trigger, from, high, movePct, volM, after}` — movePct 저점→고점 상승률 %, volM 그날 거래량(백만 주), after 그 뒤 조달·매도. 페이지의 「상단 돌파 가능성」이 목표가까지 필요한 상승률을 선례 상승폭과, 머리 위 출회 물량을 선례 거래량과 비교한다. 정리본에 숫자가 없으면 비운다(추측 금지)
- 현재가 아래 하방 근거 가격은 `supports[{price, what}]`에 넣는다(최근 공모·PIPE 단가, 전환가 하한, 내부자 매수 평단 등) — 진입 매력 판정의 지지선. 정리본에 없으면 비운다
- 기다리는 공시(EFFECT·가속 요청·424B·8-K 항목·10-Q·주총 결과 등)는 `pending[]`에 서류 단위로 넣는다 — `{form, desc, expect, onArrive, status:"대기", link}`. link는 도착 시 바꿀 필드(`{"purpose":"물량 출회","set":{"gate":"발효 완료"}}`). 출하 조건(gate)이 걸린 목적이 있으면 반드시 한 줄 만든다
- 판단 확정에 **반드시** 필요한 미확인 공시는 `checks`(종목 단위) 또는 목적의 `check`에 적는다 — 노란색 강조. 리포트 🔎 목록을 전부 옮기지 말고 판단을 바꿀 수 있는 것만
- 종합 판단(verdict)은 한 문단: 언제·무엇 때문에 띄울 것이고 그때 누가 던지나. 가장 중요한 날짜·숫자 1~2곳만 **굵게**
- 예정 이벤트(events)는 임상·출시·규제·핵심 공시만. 정리본에 없는 추정 금지

## 답변 형식
- 반영 결과 한두 줄: `종목 · 강도 n/5 (근거) · 주 목적 · v2 검증 있음`. 링크는 쓰지 않는다
- 검증(verify2)이 「있음」이 아니면 "등록 완료"라고 쓰지 않는다
- 못 정한 값은 저장을 먼저 한 뒤 한 줄로 묻는다. 투자 권유 문구 금지

# 종목 스키마 — 펌핑 목적 워치리스트

종목 JSON(new.json) = 종목 객체 하나 또는 배열. 없는 값은 `""` / `[]`. 지어내지 않는다.
저장할 때 `pw.py split2`가 v2 문서로 나눈다 — `price`·`priceDate`·`surge`·`hist` → `track/<T>`, `pending` → `feed/<T>`, 나머지 → `analysis/<T>`, 진행 상태 → `status/<T>`. 옛 `tickers` 컬렉션은 쓰지 않는다.
`coverage`는 리포트 분석률 숫자(예 100)를 넣으면 status에도 복사된다.

## 머리
| 필드 | 형식 | 내용 |
|---|---|---|
| ticker | 문자열 | 대문자 티커 |
| name | 문자열 | 회사명 |
| exchange | 문자열 | Nasdaq CM / Nasdaq GM / NYSE American |
| price | 숫자 | 현재가(분할 조정) |
| priceDate | 날짜 | 현재가 기준일 |
| mcap | 문자열 | "≈$31M" |
| updated | 날짜 | 정리일. 생략 시 오늘 |
| oneLiner | 문자열 | 한 줄 결론(120자 이내). 요약 복사 제목 "[티커] …"에 쓰임. 없으면 주 목적 + 종합 판단 첫 문장 |
| about | 문자열 | 무슨 회사인지 2~3문장: 사업, 매출·손익 한 줄, 최근 구조 변화(역분할·합병) |
| atm | true / "대기" / false | ATM 유무 — true 활성(지금 매도 가능), "대기" 등록·standstill·CTO 등으로 막힘, false 없음 |
| eloc | true / "대기" / false | ELOC(SEPA 등) 유무 — 기준 같음 |
| shares | 객체 | `{outstandingM, floatM, asOf, note, floatTag}` — 발행주식수·유통주식수 **백만 주 단위 숫자**(6.01 = 601만 주), asOf 기준일, note 산출 가정(임원·5% 보유자 제외 등). 유통 ≤5M 초소형·≤15M 소형으로 자동 강조, 다르게 보려면 floatTag에 직접 |
| splits | 배열 | 병합(역분할) 이력 `[{date, ratio:"1:10", note}]` 최신순. 3년 내 2회 이상이면 반복으로 강조, 누적 비율 자동 계산 |
| surge | 객체 | 거래량 폭발 기록(매집 의심 판정용) `{date, volumeM, avgVolM, ratio, vol7M, spikeLow, closeChg, fade, since, pr, source, note, label}` — surge.py가 만든다. date 폭발일 / volumeM 그날 거래량(백만 주) / avgVolM 직전 20일 평균 / ratio 배수 / vol7M 7거래일 거래량 합 / spikeLow 폭발일 저가 (손바뀜 판정용: 회전율·저가 이탈) / 별도 최상위 필드 **hist**: 최근 20거래일 `[{d, c, v, h}]`(날짜·종가·거래량·고가) — 미니 차트·복기용, 거래량 스캔이 덮어씀 / closeChg 그날 종가 등락 % / fade 고가 대비 종가 반납 % / since 폭발일 종가 → 현재 % / pr 같은 날 PR·공시 / label 비우면 자동(매집 의심 = 배수≥5·종가 등락 ±30% 이내 / 거래량 폭발 = 배수≥5·±30% 밖). 폭발일 7일 지나면 화면에서 자동 해제 |
| pending | 배열 | **공시대기** — 기다리는 SEC 공시를 서류 단위로 `[{id, form, desc, expect, onArrive, status, arrivedAt, url, note, link}]`. form `EFFECT`·`CORRESP`·`424B3`·`8-K 3.01`(항목까지)·`10-Q`·`DEF 14A` 등 / expect 예상 시점 / onArrive 도착 시 바뀌는 것(사람이 읽는 문장) / status `대기`·`도착`·`취소` / link 도착 시 자동으로 바꿀 필드 `{"purpose": 목적 code, "set": {...}}`. 상태 갱신은 filing-watch-scan 스킬이 한다. **삭제 금지** — 재등록 시에도 기존 줄 보존 |
| babyShelf | 객체 | baby shelf 상태 `{cap, used, remaining, escapePrice}` — 금액은 $M 숫자. remaining 남은 한도(0이면 ATM 지금 못 팖), escapePrice 공모 유통시총 $75M이 되는 주가(넘으면 baby shelf 해제). 분석 진입이 "한도 소진 → ATM 가능성 낮음", "해제가가 +10~100% 거리 → 띄울 유인 +1"로 쓴다 |
| pattern | 객체 | **과거 조달 패턴** `{precedent, kind, trigger, action, lag, move, disc, dump, desc, started}` — precedent 선례 유무 / kind 방식(ATM·ELOC·공모·RD 할인·PIPE·사모 할인·인듀스먼트·전환 매도·내부자 매도·대주주 백스톱 등) / trigger 무엇이 먼저 났나(실적 PR·데이터 PR·FDA 승인·계약 PR·EFFECT) / action 그다음 무슨 조달·매도 / lag 간격(당일·다음 날·D+7·당월·1~8주) / move 선례 상승폭 %(숫자) / disc 조달 할인율 %(숫자) / dump 시장 물량이 되는 정도(높음·낮음 — 대주주 백스톱·OTM 전환은 낮음) / desc 한 줄 근거(날짜·가격) / started 이번 회차가 이미 시작됐으면 true. 페이지가 "펌핑 전 구간 +1", "선례 상승폭이 바로 위 물량대까지 닿으면 +1", "출구 짧음 경고(당일·다음 날 할인 조달)"를 계산한다. 정리본 §13·조달 이력에서 뽑는다 |
| dilution | 배열 | **희석 물량 원장** `[{kind, holder, qtyM, price, amtM, status, gate, gateWhen, expires, note}]` — kind `PFW`·`워런트`·`전환사채`·`전환우선주`·`미등록·락업 주식`·`옵션·RSU`·`기타` / qtyM 백만 주 숫자 / price 행사가·전환가·보유자 평단(PFW는 비움) / amtM 금액만 알 때 $M / status `출회 가능`·`잠김` / gate 잠긴 이유 / gateWhen 풀리는 날 / expires 만기. 페이지 「2-1. 희석 물량」 표·합계(발행 대비 %)와 상단 돌파 판정이 쓴다. 비우면 글에서 추출한 추정치(*) |
| pumps | 배열 | **과거 펌핑 사례** `[{date, trigger, from, high, movePct, volM, after}]` — movePct 저점→고점 %, volM 그날 거래량(백만 주), after 그 뒤 조달·매도. 상단 돌파 가능성 = 목표 상승률 vs 선례 상승폭 + 머리 위 출회 물량 vs 선례 거래량(0.5배 이하 소화 가능·1.5배 이하 부담). 비우면 pattern.move·거래량 폭발일·20일 최대 거래량으로 대신 |
| coverage | 객체 | 열람 집계 `{filings:{read,total}, news:{read,total}, asOf, missing}` — **참고용**. 페이지의 분석률은 이 값이 아니라 "판단에 필요한 항목이 채워진 비율"(SKILL.md 분석률 항목)로 계산한다 |
| memo | 배열 | 소유자가 페이지에서 쓰는 내 메모 `[{d, text}]` — 스킬은 건드리지 않는다(재등록 시 보존) |
| holders | 배열 | **보유자·내부자** `[{name, type, stake, basis, blocker, lockup, behavior, note}]` — type `내부자`·`창업자`·`PIPE 투자자`·`헤지펀드`·`대주주` / stake 지분 %(숫자) / basis 근거(13G 2026-08, Form 4 09/28, DEF 14A) / blocker `4.99%`·`9.99%` / lockup 락업·standstill 종료일 / **behavior 급등·PR 시 행동**(`PR 당일 전량 매도`·`10b5-1 계획 매도`·`전환 후 상시 매도`·`보유`·`매수`). 정리본 §4(Form 4·13D/G)에서 뽑는다. 페이지가 "급등 시 매도 선례 n" 배지와 6. 보유자 표를 만들고, 매도 선례가 있으면 출회 가능성 높음·매수 선례만 있으면 낮음으로 분석 진입에 반영한다 |
| supplyOdds | 객체 | **하방 물량 출회 가능성** (분석 판단) `{atm:{odds,why}, eloc:{odds,why}, release:{odds,why}}` — odds `높음`·`중간`·`낮음`. "ATM은 있지만 standstill·CTO·가격 하한·Exchange Cap·한도 소진·블랙아웃 때문에 지금 돌리기 어렵다" 같은 판단을 why에. release는 출하 가능한 대주주·투자자 물량이 지금 나올 가능성(평단 대비 손익·락업·보유 성향). 페이지의 **분석 진입**이 이 값으로 감점을 보정한다(높음 ×1 · 중간 ×0.5 · 낮음 ×0). 비우면 페이지가 데이터로 추정하고 "*"를 붙인다 |
| supports | 배열 | **지지선** — 현재가 아래에서 하방을 받쳐줄 근거 가격 `[{price, what}]`. 최근 공모·RDO·PIPE 단가, 전환가 하한(floor), 대주주·내부자 매수 평단, 역분할 후 최저가 등. 페이지의 **진입 매력**(위로 열린 폭 − 아래로 누르는 힘 + 지지선 대비 위치)이 이걸 쓴다. 없으면 거래량 폭발일 저가만 쓰고 "지지선 데이터 없음"으로 감점 없이 표시 |
| checks | 문자열 배열 | **추가 공시 확인 필요** 항목 — 판단을 확정하려면 반드시 봐야 하는 공시(아직 안 나온 8-K, EFFECT, 주총 결과, 계약 Exhibit). 리포트의 🔎 확인 요청 목록 중 "반드시"에 해당하는 것만. 페이지가 노란색으로 강조 |
| reaction | 문자열 배열 | 뉴스·공시 반응 태그(자유). 예: "PR 급등형", "공시 무반응". 페이지 필터가 태그에서 자동 생성 — 기준은 추후 확정 |

## runway — 지금 상황만
`{cash, cashAsOf, burn, months, monthsNet, debt, runOut, note}`
cash "$358K" / cashAsOf 날짜 / burn "$0.57M/월" / **months** 현금만 잔여 개월(숫자) / **monthsNet** 부채 차감 후 개월(숫자, 현금<부채면 0) / debt "유동 차입금 $569K" (못 찾았으면 "미확인") / runOut 현금 소진 예상(날짜, 근사 가능) / note 한 줄

## verdict — 종합 판단
한 문단. "언제, 무엇 때문에 띄울 것이고, 그때 누가 던지나". 핵심 날짜·숫자 1~2곳만 `**굵게**`.

## purposes[] — 목적 (핵심)
`{code, main, resolved, targetPrice, upto, until, untilNote, how, then, gate, gateWhen}`
- **code** 6종 중 하나:
  - 물량형(올려서 판다): `현금 조달` · `워런트 행사` · `부채 주식결제` · `물량 출회`
  - 기한형(올려서 지킨다): `상장 유지` · `SPAC 조건`
- main `true` 주 목적(하나) / resolved `true` 이미 해결됨(역분할 권한 확보·유예 연장 등 — 강도 제외)
- **via** (`현금 조달`만) 그 가격이 무엇을 여는지 — `ATM 매도` · `ELOC 인출` · `baby shelf 탈출` · `RDO` · `PIPE·사모` · `공모` · `워런트 행사 유도` 중 하나. 페이지의 진입 판단·사다리·동시 해결에 "현금 조달 · ELOC 인출"처럼 붙는다. 비우면 글에서 추정
- **targetPrice** 필요 주가·행사가·전환가(숫자). 페이지가 분석 시점 현재가(price) 대비 상승률을 자동 계산해 "$6.60 +27%"로 표시(참고용). 행사가가 현재가보다 낮으면 음수로 나온다
- **upto** 얼마까지: targetPrice에 붙는 설명 — "Exchange Cap 해제선", 구간이면 "~$8.49 — 평단 구간". 가격은 targetPrice에 넣고 여기엔 숫자를 반복하지 않는다
- **until** 언제까지(날짜) / untilNote 시한의 이름 "인출금지 창 종료"
- **how** 어떻게: 수단·조건·선례 2~3문장 (ATM 잔여, ELOC 산식, 락업 해제일, 행사가·만기)
- **then** 그다음: 물량형은 "누가 얼마나 어떻게 판다", 기한형은 "못 넘기면 어떻게 되나"
- **rule**·**threshold** (`상장 유지`만): rule `bid`(최저호가) / `equity`(주주자본) / `mvls`(상장증권 시가총액 $35M — targetPrice = 35M ÷ 상장주식수) / `mvphs`, threshold 기준 금액 "$1 미만" · "$2.5M". 요건이 둘이면 **상장 유지 목적을 요건별로 두 줄** 넣는다(랭크 페이지가 최저호가 기한·주주자본 기한을 따로 세운다)
- **check** 이 목적에 걸린 추가 공시 확인 사항 한 줄(있을 때만) — 목적 제목 옆에 노란 표시
- **gate** 출하 조건: 선반·resale 등록은 됐지만 아직 못 파는 이유 — `"EFFECT 대기"` · `"주총 승인 대기"` · `"락업 중"` · `"424B 대기"` / 풀렸으면 `"발효 완료"`·`"승인됨"`. **gateWhen** 그 조건이 풀릴 예상일(날짜, 근사 가능). until이 없으면 gateWhen이 강도 계산의 시한이 된다
- **gateSource** 출하 조건의 근거 공시 — 예 `DEF 14A 2026-09-22 (주총 10/09)`, `락업 계약 §4.2`, `S-1 제출 2026-09-30`. 있으면 트리거 탭에 "확정", 없고 정확한 날짜만 있으면 "예정·공시 확인 전", 대략 날짜면 "일정 미확정". 위임장(DEF/PRE 14A)이 나왔으면 반드시 적는다

경계: baby shelf 한도 확보·ATM 단가·ELOC·임상 자금은 모두 `현금 조달` 안에서 how로 구분. 스폰서 주식 매도는 `물량 출회`, earnout 가격 조건·de-SPAC 상환은 `SPAC 조건`.

## events[] — 예정 이벤트
`{what, when, note, outlook}` — 임상 결과·출시·FDA·규제·핵심 공시. **실적 발표·잠정실적 PR·분기 보고**면 `outlook{call, why}`를 넣는다: call `호재 가능`·`그저 그럼`·`악재 가능`, why 한 줄 근거(직전 분기·연간 매출 추이, 가이던스 대비, 흑자 여부, going concern·자기자본 노출, 정정·손상 이슈). 없으면 페이지가 데이터로 추정(*)한다. when은 분기 근사 허용(`2026-Q4`). 시점 미정이면 `""`.

## 날짜 형식
`YYYY-MM-DD` 확정 / `YYYY-MM` 월 / `YYYY-Q1`~`Q4` 분기 / `YYYY-H1`·`H2` 반기 / `YYYY` 연 / `""` 미정. 근사는 화면에 "경 ≈D-xx"로 표시.

## 강도 (페이지가 자동 계산 — 입력하지 않음)
가장 급한 시한(목적 until·이벤트 when 중 resolved 아닌 것): ≤14일 4 / ≤30 3 / ≤90 2 / ≤180 1
+ 런웨이(monthsNet, 없으면 months): ≤1개월 3 / ≤3 2 / ≤6 1
합계 0~1 → 1, 2 → 2, 3~4 → 3, 5 → 4, 6~7 → 5

## 정리본 → 필드
| 스캔 리포트 | 필드 |
|---|---|
| §1 회사 | name·exchange·price·mcap·about |
| §3-A/B/C 발행·유통 주식수 · §8 역분할 반복 | shares · splits |
| §2 런웨이(현금·월 소모·부채 반영 실질 런웨이) | runway |
| §3 락업·미등록·워런트·전환사채 | purposes(물량 출회·워런트 행사·부채 주식결제)의 how·then |
| §5 ATM/ELOC · §6 baby shelf | purposes `현금 조달` |
| §7 부채 결제 구조 | purposes `부채 주식결제` / runway.debt |
| §8 상장유지(🔴 통지·🟠 $1 미만일 때만) | purposes `상장 유지` |
| §9 M&A·임상 · §10 포워드 이벤트 | events |
| §13 부양 목적 분류·한 줄 결론 | main 선택·verdict |

## 예시
```json
{
 "ticker": "ONMD", "name": "OneMedNet Corp", "exchange": "Nasdaq CM", "price": 5.20, "priceDate": "2026-09-29", "mcap": "≈$31M", "updated": "2026-09-30",
 "atm": false, "eloc": true, "reaction": [],
 "shares": {"outstandingM": 6.01, "floatM": 3.0, "asOf": "2026-09-29", "note": "분할 후. 임원·이사 50.2% 제외"},
 "splits": [{"date": "2026-09-29", "ratio": "1:10", "note": ""}],
 "about": "의료영상·임상기록 비식별 RWD 공급사. 1H26 매출 $388K vs 원가 $1.54M. 2026-09-29 1:10 역분할.",
 "runway": {"cash": "$358K", "cashAsOf": "2026-06-30", "burn": "$0.57M/월", "months": 0.6, "monthsNet": 0, "debt": "유동 차입금 $569K", "runOut": "2026-09", "note": "9월 중 소진 — 이후 현금원은 SEPA 인출뿐"},
 "verdict": "10/2 인출금지 창이 끝나는 즉시 SEPA 인출이 유일한 길. **10월 초 PR·급등 뒤 인출** 패턴 반복 가능성 큼. 상장 유지는 역분할로 해결돼 펌핑 이유 아님.",
 "purposes": [
  {"code": "현금 조달", "main": true, "targetPrice": 6.60, "upto": "Exchange Cap 해제선", "until": "2026-10-02", "untilNote": "인출금지 창 종료",
   "how": "Yorkville SEPA $25M, 3일 최저 VWAP × 97%, 회당 최대 29.6만 주. 선례 2건 모두 PR 당월 인출.", "then": "인출분은 Yorkville이 즉시 매도."},
  {"code": "물량 출회", "targetPrice": 6.90, "upto": "~$8.49 — Kosasa·Yu 평단 구간", "until": "2027-01-30", "untilNote": "Kosasa 청약분 144 해제",
   "how": "Kosasa 등록분 평단 $8.49, Yu $7.97 — resale 유효.", "then": "평단 위에서 대주주 매도."},
  {"code": "상장 유지", "rule": "bid", "threshold": "$1 미만", "resolved": true, "targetPrice": 1.00, "upto": "$1 이상 10거래일", "until": "2026-10-12", "untilNote": "10영업일 충족 기한",
   "how": "🟠 $1 미달 → 9/29 역분할 1:10.", "then": "역분할로 사실상 충족. 못 넘기면 청문."}
 ],
 "events": [{"what": "Q3 10-Q — SEPA 인출 내역 확정", "when": "2026-11-12", "note": ""}]
}
```

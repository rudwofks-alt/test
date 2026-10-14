# 김곰 워치리스트 — 스킬 v2 (경로 전환)

## 2026-10-14 누락 사고 원인
워치리스트 페이지는 v2로 바뀌면서 `analysis`·`track`·`feed`·`status`·`reports`·`research`만 읽는다.
그런데 계정에 설치된 스킬은 옛 버전(포렌식 v1.4.33 · pump-watch-sync v3.8)이라
진행 기록을 `pendingReg`, 등록을 `tickers`에 썼다 → 저장은 성공했지만 화면에 안 나옴 (ILAG·JBDI·JYD·IZM·YJ).
「v2 티커 분석」 루틴은 포렌식 v2.0.0 · pump-watch-sync v4.0을 요구하지만 그 판이 업로드되지 않은 상태였다.

## 고친 것
| 위치 | 내용 |
|---|---|
| `skills/sec-dilution-forensic-scan` v2.0.0 | 시작·완료 기록 → `status/<T>`, 조사 대기 `research/<T>` 상태 갱신, 리포트 원문 `reports/<T>_<YYYYMMDD>`, 등록 후 v2 검증, 시각은 `date -u`만, 「등록 모드」 신설. 분석 절차는 v1.4.33과 같음 |
| `skills/pump-watch-sync` v4.0 | 저장을 `analysis·track·feed·status`로 (`pw.py split2`), 리포트 문서(`pw.py report`), v2 검증(`pw.py verify2`), 버전 이력 `verHist`. 옛 `split`·`verify`는 호출하면 오류로 멈춤 |
| 워치리스트 페이지 (artifact 버전 482) | 안전장치 — 소유자가 열 때 최근 21일 안에 옛 경로 `tickers`에만 저장된 종목을 v2로 자동 이전 (v2가 더 새로우면 건드리지 않음) |

## 설치 (사용자가 해야 하는 일)
claude.ai → 설정 → 기능(Capabilities) → 스킬에서 기존 `sec-dilution-forensic-scan`·`pump-watch-sync`를
`dist/sec-dilution-forensic-scan.zip`·`dist/pump-watch-sync.zip`(또는 `dist/skills_v2.zip`)으로 교체 업로드.

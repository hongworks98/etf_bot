# DSS User Manual — 매일 사용 가이드

**버전:** v1.0.0  
**대상:** 투자 결정에 DSS를 사용하는 모든 사용자

---

## DSS란?

DSS(Decision Support System)는 미국 ETF 섹터 투자를 위한 의사결정 지원 시스템이다.  
매일 아침 5분 안에 다음을 확인할 수 있다:

- 오늘 BUY / SELL / HOLD 결정
- 어떤 섹터 ETF를 얼마나 보유해야 하는지
- 시장 상황 (거시경제, 시장 폭, 섹터 로테이션)
- 내 결정 기록 (Decision Journal)

---

## 매일 사용 순서

### 1단계. Dashboard 접속 (0분)

URL 접속 → 화면 상단의 **Market Status 카드** 확인

```
🟢 US Market Open          → 장중 (매수/매도 가능)
🟡 US Pre-Market           → 장 시작 전
🟡 US After-Hours          → 장 마감 후
🔴 US Market Closed        → 장 닫힘 (주말/휴장)
🟡 US Market Open — FOMC Day → FOMC 발표일 (변동성 주의)
```

이벤트 표시 (FOMC, CPI, NFP, Quad Witching)가 있으면 해당 날 변동성에 주의한다.

---

### 2단계. 🏠 Today 탭 — 오늘 결정 확인 (1분)

**Decision Hero 카드** (화면 상단 큰 카드):
```
BUY  (초록) → 비중 확대 신호
SELL (빨강) → 비중 축소 신호
HOLD (주황) → 현재 유지
WAIT (주황) → 관망
```

**신뢰도 (Confidence):** 65% 이상이면 신뢰할 수 있는 신호

**Why Now?** 섹션에서 결정 이유 확인:
- 거시경제 상태 (Expansion / Recession / Stagflation)
- 시장 폭 상태 (Healthy / Degraded / Critical)
- 상위 기회 ETF (XLK, XLC 등)

**Morning Checklist** — 오늘 해야 할 것들

---

### 3단계. 📊 Market 탭 — 시장 분석 (1분)

**Macro Score:** 거시경제 점수 (0~100)
- 65 이상 → Expansion 국면 (위험자산 비중 확대)
- 45~65 → 중립
- 45 미만 → 경기 둔화 주의

**Breadth Score:** 시장 폭 (참여 종목 수)
- Healthy → 시장 전반적 상승
- Degraded → 일부 종목만 상승 (주의)
- Critical → 시장 폭 매우 좁음 (경고)

**Sector RS (상대강도):** 10개 섹터 ETF 점수 비교
- 높을수록 → 해당 섹터가 시장 대비 강세

---

### 4단계. 💼 Portfolio 탭 — 포트폴리오 확인 (1분)

**Target Allocation:** 오늘의 목표 배분
- 파이차트로 섹터별 목표 비중 표시

**Rebalance Signal:** 리밸런싱 필요 여부
- This Week → 이번 주 안에 리밸런싱 권장
- This Month → 이번 달 안에
- No Action → 현재 유지

**Cash Recommendation:** 현금 비중 권장
- 5% 이상이면 현금 보유 권장

---

### 5단계. 📅 History 탭 — 기록 확인 (30초)

**오늘 vs 어제 비교:** 결정이 바뀌었는지 확인
**최근 30일 기록:** 결정 패턴 확인 (BUY가 많으면 Bullish 국면)

---

### 6단계. 🔧 Diagnostics 탭 — 시스템 확인 (30초)

**Daily Operation Checklist** 7항목:
- 모두 ✅이면 정상
- ⚠️ 항목이 있으면 해당 항목 확인

문제가 있으면 상단 **🔄** 버튼 클릭으로 Engine 재실행

---

## ETF 검색 방법

🔍 **Discover 탭** → 검색창에 티커 입력 (예: XLK)

- RS 점수, 신뢰도 확인
- ⭐ 즐겨찾기 / 👁 관심 종목 추가 가능

---

## 알림 / 경고 확인

⚙️ **System 탭** → **Notification Center** 에서 경고 메시지 확인

---

## 자주 묻는 질문

**Q. 결정이 매일 바뀌나요?**  
아니다. 거시 지표가 크게 변하지 않으면 며칠간 같은 결정이 유지된다.

**Q. HOLD가 나오면 아무것도 안 해도 되나요?**  
맞다. HOLD는 현재 포지션을 유지하라는 신호다.

**Q. 신뢰도가 낮으면 어떻게 하나요?**  
50% 미만이면 결정에 확신이 부족한 상태다. 리스크를 줄이거나 관망하는 것이 좋다.

**Q. 데이터가 오래된 것 같아요.**  
🔄 새로고침 버튼을 클릭한다. 5분마다 자동 갱신된다.

**Q. 모바일에서 탭이 잘 안 보여요.**  
탭 영역을 좌우로 스크롤하면 모든 탭을 볼 수 있다.

# DSS Release Notes

## v1.0.0 — 2026-06-29 (Production Release)

### 핵심 기능

**5개 Analysis Engine**
- MacroEngine — 거시경제 점수 (GDP, CPI, 금리, 고용)
- MarketBreadthEngine — 시장 폭 분석 (ADV/DEC, McClellan)
- RelativeStrengthEngine — 10개 섹터 ETF 상대강도
- RotationSignalEngine — 섹터 로테이션 신호 + Lifecycle
- PortfolioDecisionEngine — BUY/SELL/HOLD/WAIT 결정

**포트폴리오 최적화**
- PortfolioOptimizationEngine — 목표 배분 + Monte Carlo
- 리밸런싱 신호 + 긴급도 (This Week / This Month / No Action)

**ValidationEngine**
- 백테스트 (Walk-Forward, Full Backtest)
- Monte Carlo 시뮬레이션
- 신뢰도 보정 (Calibration)
- Engine 건강도 점수

**Decision Intelligence Dashboard (7탭)**
- 🏠 Today — BUY/SELL/HOLD 결정 + XAI 설명 + Morning Checklist
- 📊 Market — 거시경제 + 시장 폭 + 섹터 RS
- 💼 Portfolio — 배분 + 리밸런싱 + 리스크
- 📅 History — 결정 일지 + 비교 분석
- 🔍 Discover — ETF 검색 + 관심 종목
- ⚙️ System — Engine 상태 + 알림
- 🔧 Diagnostics — 시스템 진단 + 운영 체크리스트

**Operation Validation (STEP 7)**
- Market Calendar — NYSE 개장/휴장/이벤트 (외부 API 없음)
- Today's Market Status 카드 (FOMC/CPI/NFP/Quad Witching 표시)
- Daily Operation Checklist (7항목 자동 판별)
- RotatingFileHandler (5MB × 5 로그 로테이션)

### 테스트
- 754개 테스트 전부 PASS (0 failures)
- Engine 단위 테스트, Integration 테스트, UI 테스트, 운영 테스트 포함

### 아키텍처
- DataBridge Pattern — UI는 계산 없음, 모든 계산은 DataBridge
- Demo 폴백 — Pipeline 실패 시 자동 Demo 데이터 사용
- Mobile-First CSS — 5분 운영 확인 가능
- Config-Driven — YAML 파일로 가중치/테마 조정 가능

---

## 이전 버전 (개발 이력)

| 단계 | 내용 |
|------|------|
| STEP 1 | MacroEngine 구현 |
| STEP 2 | PortfolioDecisionEngine |
| STEP 3 | MarketBreadthEngine |
| STEP 4 | RelativeStrengthEngine |
| STEP 5 | RotationSignalEngine |
| STEP 6 | PortfolioOptimizationEngine |
| STEP 7 | Decision Intelligence Dashboard |
| STEP 8 | ValidationEngine |
| Web Step 1 | DSS Integration Layer + EngineMonitor |
| Web Step 2 | Mobile Dashboard (7탭) |
| Web Step 3 | Journal/Watchlist/Search/History |
| RC | Release Candidate 준비 (714 Tests) |
| STEP 7 Op | Operation Validation (754 Tests) |
| STEP 9 | Production Deployment (현재) |

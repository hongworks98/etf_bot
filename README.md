# DSS — ETF Decision Support System

모바일 우선 ETF 투자 의사결정 지원 시스템.
매일 아침 5분 안에 투자 의사결정을 끝낼 수 있는 AI 기반 Dashboard.

---

## 빠른 시작

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 실행
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 열기.

---

## 프로젝트 소개

DSS는 8개 분석 Engine을 순서대로 실행하고, 그 결과를 모바일 최적화 Dashboard로 보여주는 시스템입니다.

**핵심 원칙:**
- Engine은 독립적으로 유지 — 언제든 교체 가능 (Loose Coupling)
- UI는 계산하지 않는다 — DataBridge가 모든 변환 담당
- 모든 데이터는 DSSResult 하나에서 온다

---

## 설치 방법

### 필수 요구사항
- Python 3.12+
- pip

### 의존성 설치

```bash
pip install -r requirements.txt
```

**필수 패키지:**

| 패키지 | 버전 | 용도 |
|--------|------|------|
| streamlit | >=1.35.0 | Web Dashboard |
| PyYAML | >=6.0.1 | Engine 설정 파일 로딩 |

**선택 패키지 (없어도 동작):**

| 패키지 | 버전 | 용도 |
|--------|------|------|
| plotly | >=5.20.0 | 포트폴리오 차트 |
| psutil | >=5.9.0 | Engine 성능 모니터링 |

---

## 실행 방법

```bash
# 기본 실행
streamlit run app.py

# 포트 지정
streamlit run app.py --server.port 8502

# 모바일 테스트 (외부 접속 허용)
streamlit run app.py --server.address 0.0.0.0
```

---

## 폴더 구조

```
dss/
├── app.py                          ← ★ Entry Point (여기만 실행)
├── requirements.txt
├── README.md
├── .gitignore
│
├── web/                            ← Dashboard (Streamlit)
│   ├── app.py                      ← 6탭 Dashboard 메인
│   ├── components/                 ← 탭별 UI 컴포넌트
│   │   ├── home.py                 ← Today 탭
│   │   ├── market.py               ← Market 탭
│   │   ├── portfolio.py            ← Portfolio 탭
│   │   ├── checklist.py            ← Morning Checklist + Timeline
│   │   ├── history.py              ← Decision History (계산 없음 — DataBridge)
│   │   ├── search.py               ← Smart Search + Watchlist
│   │   ├── notification.py         ← Notification Center
│   │   ├── backtest.py             ← Backtest 결과
│   │   ├── system.py               ← System 모니터 (계산 없음 — DataBridge)
│   │   └── diagnostics.py          ← 🔧 Diagnostics 탭 (신규)
│   ├── utils/
│   │   ├── data_bridge.py          ← DSSResult → ViewData 변환
│   │   ├── journal.py              ← Decision Journal (자동 저장)
│   │   ├── watchlist.py            ← Favorites / Watchlist
│   │   └── state_manager.py        ← Session State 관리
│   ├── styles/
│   │   └── theme.py                ← CSS / 색상 / 모바일 레이아웃
│   └── data/                       ← 런타임 데이터 (자동 생성)
│       ├── journal.json
│       └── watchlist.json
│
├── dss_integration/                ← Pipeline 오케스트레이터
│   ├── core/
│   │   ├── dss_pipeline.py         ← 8개 Engine 순서 실행
│   │   └── dss_result.py           ← DSSResult (최상위 결과)
│   ├── monitor/
│   │   ├── engine_monitor.py       ← 실행시간/메모리/CPU 기록
│   │   └── monitor_models.py       ← EngineMonitorResult 모델
│   ├── adapters/                   ← Engine ↔ Pipeline 인터페이스
│   ├── data/
│   │   └── synthetic_loader.py     ← 시뮬레이션 데이터 (네트워크 불필요)
│   └── config/
│       └── settings.py             ← Engine 설정
│
├── engines/                        ← 분석 Engine (독립 모듈)
│   ├── breadth/                    ← Market Breadth Engine
│   ├── decision/                   ← Portfolio Decision Engine
│   ├── portfolio_optimizer/        ← Portfolio Optimization Engine
│   ├── relative_strength/          ← Relative Strength Engine
│   └── rotation/                   ← Rotation Signal Engine
│
├── validation/                     ← Validation Engine
├── dashboard/                      ← Dashboard Engine
│
├── config/                         ← 설정 파일 (YAML)
│   ├── theme.yaml                  ← Dashboard 테마 (색상/폰트/레이아웃)
│   ├── app_config.yaml             ← 앱 설정 (임계값/알림/캐시)
│   ├── breadth_weights.yaml        ← Engine 가중치 설정
│   ├── decision_weights.yaml
│   ├── portfolio_weights.yaml
│   ├── rotation_weights.yaml
│   └── rs_weights.yaml
│
├── tests/                          ← 전체 테스트 (697개)
│   ├── test_market_breadth.py
│   ├── test_portfolio_decision.py
│   ├── test_portfolio_optimizer.py
│   ├── test_relative_strength.py
│   ├── test_rotation_signal.py
│   ├── test_validation.py
│   ├── test_dashboard.py
│   ├── test_web2.py                ← Web Step 2 테스트 (102개)
│   └── test_web3.py                ← Web Step 3 + Architecture 100 테스트 (107개)
│
├── data/                           ← 데이터 가이드
├── models/                         ← 모델 가이드
└── utils/                          ← 유틸 가이드
```

---

## Engine 설명

DSS는 8개 Engine을 아래 순서로 실행합니다.

```
SyntheticDataLoader (데이터 로드)
        ↓
1. Macro Engine           — 거시경제 분석 (GDP, 금리, 물가)
        ↓
2. Market Breadth Engine  — 시장 폭 분석 (A/D, 신고가/신저가)
        ↓
3. Relative Strength Engine — 섹터 상대강도 분석
        ↓
4. Rotation Signal Engine   — 섹터 순환 분석
        ↓
5. Portfolio Decision Engine — 투자 의사결정 (BUY/SELL/HOLD)
        ↓
6. Portfolio Optimization Engine — 포트폴리오 최적화 (비중 배분)
        ↓
7. Validation Engine       — 백테스팅 / 성과 검증
        ↓
8. Dashboard Engine        — Dashboard 집계 / 신뢰도 산출
        ↓
DSSResult (최종 통합 결과)
```

**Engine 독립성:** 각 Engine은 독립 패키지로 분리되어 있으며,
Pipeline은 Adapter를 통해 Engine을 호출합니다.
Engine 내부 로직 수정 없이 언제든 교체 가능합니다.

---

## Dashboard 설명

7개 탭으로 구성된 모바일 우선 Dashboard:

| 탭 | 내용 |
|----|------|
| 🏠 Today | 오늘의 투자 결정 (BUY/SELL/HOLD) + Morning Checklist + AI 설명 |
| 📊 Market | 거시경제 + 시장 폭 + 섹터 RS + 순환 |
| 💼 Portfolio | 포트폴리오 배분 + 몬테카를로 시뮬레이션 |
| 📅 History | 어제 vs 오늘 비교 + Decision Journal (avg_conf / 액션 분포) |
| 🔍 Discover | ETF 검색 + 즐겨찾기 + 관심 ETF |
| ⚙️ System | Engine 상태 + 실행 시간 Bar + 알림 설정 |
| 🔧 Diagnostics | Python 버전 + Config 파일 상태 + Pipeline 진단 |

**Explainable AI (XAI):**
- Why — 왜 이 결정인가
- Why Now — 왜 지금인가
- Why This ETF — 왜 이 ETF인가
- Why This Allocation — 왜 이 비중인가

**Decision Journal:**
매일 자동 저장 (최대 30일). 향후 Validation Engine과 연결하여 실제 성과 추적 가능.

---

## 테스트 실행

```bash
# 전체 테스트
pytest tests/

# 특정 테스트
pytest tests/test_web3.py -v

# 커버리지 포함
pytest tests/ --tb=short -q
```

**테스트 현황:** 714개 전체 통과 ✅

---

## 문제 해결 (FAQ)

**Q: `ModuleNotFoundError: No module named 'yaml'`**
```bash
pip install PyYAML
```

**Q: `ModuleNotFoundError: No module named 'streamlit'`**
```bash
pip install streamlit
```

**Q: 차트가 표시되지 않음**
```bash
pip install plotly
```
(plotly 없이도 동작하지만 파이 차트는 텍스트로 대체됩니다)

**Q: Engine Monitor에서 메모리/CPU가 None으로 표시됨**
```bash
pip install psutil
```
(psutil 없이도 tracemalloc으로 메모리 측정 가능)

**Q: `streamlit run app.py` 실행 후 빈 화면**

Streamlit 버전이 낮을 수 있습니다:
```bash
pip install --upgrade streamlit
```

**Q: 포트 충돌**
```bash
streamlit run app.py --server.port 8502
```

**Q: 데이터 초기화 (Journal/Watchlist 리셋)**
```bash
rm web/data/journal.json web/data/watchlist.json
```

---

## 아키텍�
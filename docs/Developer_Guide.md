# DSS Developer Guide

**버전:** v1.0.0  
**대상:** 유지보수 및 기능 추가 개발자

---

## 프로젝트 구조

```
dss-dashboard/
├── app.py                      ← Streamlit Entry Point (수정 금지)
├── requirements.txt
├── runtime.txt
├── VERSION
│
├── web/                        ← Dashboard Layer (UI)
│   ├── app.py                  ← 메인 앱 (탭 구성, Pipeline 호출)
│   ├── components/             ← 탭별 컴포넌트
│   │   ├── home.py             ← 🏠 Today 탭
│   │   ├── market.py           ← 📊 Market 탭
│   │   ├── portfolio.py        ← 💼 Portfolio 탭
│   │   ├── history.py          ← 📅 History 탭
│   │   ├── search.py           ← 🔍 Discover 탭
│   │   ├── system.py           ← ⚙️ System 탭
│   │   ├── diagnostics.py      ← 🔧 Diagnostics 탭
│   │   ├── checklist.py        ← Morning Checklist
│   │   ├── notification.py     ← 알림 센터
│   │   └── backtest.py         ← 백테스트 (미래 확장)
│   ├── utils/
│   │   ├── data_bridge.py      ← 핵심: 모든 ViewData 생성
│   │   ├── market_calendar.py  ← NYSE 캘린더
│   │   ├── journal.py          ← Decision Journal
│   │   ├── watchlist.py        ← 관심 종목
│   │   └── state_manager.py    ← Session State 관리
│   └── styles/
│       └── theme.py            ← CSS + 색상 상수
│
├── engines/                    ← Analysis Engine Layer (수정 금지)
│   ├── macro/                  ← 거시경제 분석
│   ├── breadth/                ← 시장 폭 분석
│   ├── rs/                     ← 상대강도
│   ├── rotation/               ← 섹터 로테이션
│   ├── portfolio/              ← 포트폴리오 결정
│   └── optimizer/              ← 포트폴리오 최적화
│
├── validation/                 ← ValidationEngine Layer
├── dss_integration/            ← Integration Layer
│   ├── core/dss_pipeline.py    ← Pipeline 오케스트레이터
│   ├── monitor/engine_monitor.py ← Engine 모니터링
│   ├── data/synthetic_loader.py  ← Demo 데이터
│   └── utils/logger.py         ← RotatingFileHandler 로거
│
├── config/                     ← YAML 설정 파일
│   ├── app_config.yaml         ← 앱 전반 설정
│   ├── theme.yaml              ← 색상/UI 설정
│   ├── decision_weights.yaml   ← 결정 가중치
│   ├── breadth_weights.yaml    ← 시장 폭 가중치
│   └── ...
│
└── tests/                      ← 754개 테스트
    ├── test_operation.py       ← 운영 검증
    ├── test_web2.py            ← UI 검증
    ├── test_web3.py            ← 유틸리티 검증
    └── ...
```

---

## 핵심 패턴: DataBridge

**원칙:** UI는 계산하지 않는다. 모든 데이터 변환은 DataBridge에서.

```python
# web/utils/data_bridge.py

class DataBridge:
    def __init__(self, result: DSSResult):
        self._r = result

    def home_data(self) -> HomeViewData:
        # DSSResult → HomeViewData 변환
        ...

    def market_status(self) -> MarketStatusViewData:
        # MarketCalendar 호출 → MarketStatusViewData
        ...
```

컴포넌트는 ViewData를 받아 렌더링만 한다:
```python
# web/components/home.py
def render(data: HomeViewData) -> None:
    st.markdown(f"## {data.action}")  # 계산 없음, 표시만
```

---

## Data Flow

```
SyntheticDataLoader / 실시간 API
         ↓
    DSSPipeline.run()
         ↓
    DSSResult (dataclass)
         ↓
    DataBridge.__init__(result)
         ↓
    DataBridge.home_data()  →  HomeViewData  →  home.render()
    DataBridge.market_data() → MarketViewData → market.render()
    DataBridge.market_status() → MarketStatusViewData → _render_market_status_card()
    ...
```

---

## ViewData 목록

| ViewData | 생성 메서드 | 사용 컴포넌트 |
|----------|------------|--------------|
| HomeViewData | home_data() | home.py |
| MarketViewData | market_data() | market.py |
| PortfolioViewData | portfolio_data() | portfolio.py |
| HistorySummaryViewData | history_summary() | history.py |
| DiagnosticsViewData | diagnostics_data() | diagnostics.py |
| MarketStatusViewData | market_status() | app.py (카드) |
| DailyOpCheckViewData | daily_op_check() | diagnostics.py |
| ETFSearchResult | search_etf() | search.py |
| WatchlistViewData | watchlist_data() | search.py |

---

## 새로운 탭 추가 방법

1. `web/components/new_tab.py` 생성
2. `DataBridge`에 ViewData 타입 + 메서드 추가
3. `web/app.py`에서 탭 추가:
   ```python
   tabs = st.tabs([..., "🆕 New"])
   with tabs[N]:
       new_tab.render(bridge.new_data())
   ```
4. 테스트 작성 후 기존 754개 PASS 확인

---

## 새로운 Engine 추가 방법

1. `engines/new_engine/` 폴더 생성
2. Engine 클래스 구현 (기존 Engine 패턴 참고)
3. `dss_integration/adapters/new_adapter.py` 생성
4. `dss_integration/core/dss_pipeline.py`에 호출 추가
5. `DataBridge`에 결과 반영
6. 테스트 작성

---

## Config 추가 방법

`config/new_config.yaml` 생성 후 Engine에서 로드:
```python
import yaml
with open("config/new_config.yaml") as f:
    config = yaml.safe_load(f)
```

---

## 로깅

```python
from dss_integration.utils.logger import get_logger
log = get_logger(__name__)

log.info("Engine started")
log.error("Engine failed: %s", error)
```

로그 파일: `dss_integration/logs/dss.log` (5MB × 5 회전)

---

## 테스트 실행

```bash
# 전체 테스트
python -m pytest tests/ -q

# 특정 파일만
python -m pytest tests/test_operation.py -v

# 커버리지 포함
python -m pytest tests/ --cov=engines --cov=web
```

---

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

접속: http://localhost:8501

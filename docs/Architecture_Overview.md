# DSS Architecture Overview

**버전:** v1.0.0

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   User (Browser / Mobile)           │
└─────────────────────┬───────────────────────────────┘
                      │ HTTPS
┌─────────────────────▼───────────────────────────────┐
│              Streamlit Cloud (Web Server)            │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │           web/app.py  (Entry Point)         │    │
│  │                                             │    │
│  │  Market Status Card                         │    │
│  │  ┌──────┬──────┬───────┬──────┬──────┬────┐│    │
│  │  │Today │Market│Portf. │Hist. │Disc. │Sys.││    │
│  │  └──────┴──────┴───────┴──────┴──────┴────┘│    │
│  └──────────────────┬──────────────────────────┘    │
│                     │                               │
│  ┌──────────────────▼──────────────────────────┐    │
│  │         DataBridge (web/utils/)             │    │
│  │  DSSResult → ViewData (계산 없음 원칙)       │    │
│  └──────────────────┬──────────────────────────┘    │
│                     │                               │
│  ┌──────────────────▼──────────────────────────┐    │
│  │         DSS Integration Layer               │    │
│  │  DSSPipeline → EngineMonitor → DSSResult    │    │
│  └──────────────────┬──────────────────────────┘    │
│                     │                               │
│  ┌──────────────────▼──────────────────────────┐    │
│  │         Analysis Engine Layer               │    │
│  │  Macro → Breadth → RS → Rotation → Portfolio│    │
│  │  → Optimization → Validation               │    │
│  └──────────────────┬──────────────────────────┘    │
│                     │                               │
│  ┌──────────────────▼──────────────────────────┐    │
│  │         Data Layer                          │    │
│  │  SyntheticDataLoader / (미래: yfinance API) │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

---

## Engine Flow

```
MacroEngine
    → macro_score (0~100)
    → macro_state (Expansion/Stagflation/Recession/Recovery)
    → macro_direction (UP/DOWN/NEUTRAL)
           ↓
MarketBreadthEngine
    → breadth_score (0~100)
    → breadth_health (Healthy/Degraded/Critical)
    → breadth_trend (UP/DOWN/NEUTRAL)
           ↓
RelativeStrengthEngine (10개 섹터 ETF)
    → rs_score per sector
    → avg_rs_score
           ↓
RotationSignalEngine
    → dominant_rotation (최강 섹터)
    → rotation_forecast (%)
    → market_rotation_active (bool)
           ↓
PortfolioDecisionEngine
    → action (BUY/SELL/HOLD/WAIT)
    → decision_score (0~100)
           ↓
PortfolioOptimizationEngine
    → target_allocation {ticker: weight}
    → rebalance_signal (urgency, max_delta)
    → monte_carlo (expected return/vol)
           ↓
ValidationEngine (선택적)
    → validation_grade (A+/A/B/C/D/F)
    → backtest_results
```

---

## Decision Flow

```
macro_score + breadth_score + rs_score + rotation_forecast
              ↓ (가중 합산)
         decision_score (0~100)
              ↓
         decision_score >= 65  →  BUY
    45 <= decision_score < 65  →  HOLD
    30 <= decision_score < 45  →  WAIT
         decision_score < 30   →  SELL
```

가중치: `config/decision_weights.yaml`로 조정 가능

---

## Dashboard Flow

```
_run_pipeline()  [st.cache_data TTL=300초]
      ↓
DSSResult
      ↓
DataBridge(result)
      ↓
bridge.market_status()    → Market Status 카드
bridge.home_data()        → 🏠 Today 탭
bridge.market_data()      → 📊 Market 탭
bridge.portfolio_data()   → 💼 Portfolio 탭
bridge.comparison_data()  → 📅 History 탭
bridge.search_etf()       → 🔍 Discover 탭
bridge.system_data()      → ⚙️ System 탭
bridge.diagnostics_data() → 🔧 Diagnostics 탭
bridge.daily_op_check()   → ☑️ Op Checklist
```

---

## Module Dependency

```
web/app.py
  ├── web/utils/data_bridge.py
  │     ├── web/utils/market_calendar.py  (독립)
  │     └── dss_integration/...           (Pipeline)
  ├── web/components/*.py                 (DataBridge 의존)
  ├── web/styles/theme.py                 (독립)
  ├── web/utils/journal.py                (파일 I/O)
  ├── web/utils/watchlist.py              (파일 I/O)
  └── web/utils/state_manager.py          (Session State)

dss_integration/core/dss_pipeline.py
  ├── engines/macro/
  ├── engines/breadth/
  ├── engines/rs/
  ├── engines/rotation/
  ├── engines/portfolio/
  └── engines/optimizer/
```

---

## 확장 계획

### React/Next.js 전환 시 (미래)

DataBridge 패턴이 API 레이어로 자연스럽게 전환된다:

```
현재: DataBridge.home_data() → HomeViewData (Python)
미래: GET /api/home           → HomeViewData (JSON)
```

변경 없는 부분:
- Engine Layer (engines/) → 완전 불변
- ViewData 구조 → JSON 직렬화만 추가
- Business Logic → 완전 불변

### 실시간 데이터 연동 시

`dss_integration/data/synthetic_loader.py`를 실제 데이터 로더로 교체:

```python
# 현재
loader = SyntheticDataLoader(seed=42)

# 미래 (yfinance)
loader = YFinanceLoader(tickers=SECTOR_ETFS, period="1mo")
```

Engine 코드는 수정하지 않는다 — DataLoader 인터페이스만 구현하면 됨.

---

## 보안 고려사항

- API 키 → `.streamlit/secrets.toml` (`.gitignore`에 포함)
- 사용자 데이터 → `web/data/` (`.gitignore`에 포함)
- 로그 → `dss_integration/logs/` (`.gitignore`에 포함)
- 환경 변수 → `.env` (`.gitignore`에 포함)

현재 DSS v1.0.0은 외부 API 키 없이 동작한다 (SyntheticDataLoader 사용).

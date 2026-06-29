# DSS Maintenance Guide

**버전:** v1.0.0  
**대상:** 유지보수 담당자

---

## 절대 수정 금지 원칙

다음은 어떤 경우에도 수정하지 않는다:
- `engines/` — 모든 Analysis Engine
- Business Logic (점수 계산, 결정 로직)
- Decision Flow (BUY/SELL/HOLD 임계값)
- 기존 ViewData 타입 필드

수정 전 반드시:
1. 수정 파일 목록 작성
2. 영향 범위 분석
3. 테스트 실행 (754개 PASS 확인)
4. Rollback 방법 준비

---

## Config 파일 조정 방법

Engine 가중치 조정 — 코드 수정 없이 YAML로:

```yaml
# config/decision_weights.yaml 예시
macro_weight: 0.35      # 거시경제 가중치 (기본 0.35)
breadth_weight: 0.25    # 시장 폭 가중치
rs_weight: 0.20         # 상대강도 가중치
rotation_weight: 0.20   # 로테이션 가중치
```

테마 색상 조정:
```yaml
# config/theme.yaml
colors:
  buy: "#22c55e"    # BUY 색상
  sell: "#ef4444"   # SELL 색상
  hold: "#f97316"   # HOLD 색상
```

조정 후: `python -m pytest tests/ -q` 실행 → 754 PASS 확인

---

## 새로운 Engine 추가 방법

### 1. Engine 구현

```python
# engines/new_engine/new_engine.py
class NewEngine:
    def run(self, data) -> NewResult:
        ...
```

### 2. Adapter 작성

```python
# dss_integration/adapters/new_adapter.py
class NewAdapter(BaseAdapter):
    def adapt(self, raw_data) -> dict:
        ...
```

### 3. Pipeline 연결

```python
# dss_integration/core/dss_pipeline.py
# run() 메서드에 추가
new_result = self._run_engine(
    "NewEngine", NewEngine, new_data
)
result.new_result = new_result
```

### 4. DataBridge 확장

```python
# web/utils/data_bridge.py
@dataclass
class NewViewData:
    score: float
    label: str

# DataBridge 클래스 내에 추가
def new_data(self) -> NewViewData:
    nr = getattr(self._r, "new_result", None)
    return NewViewData(
        score=getattr(nr, "score", 0.0),
        label=getattr(nr, "label", "N/A"),
    )
```

### 5. 컴포넌트 추가

```python
# web/components/new_tab.py
def render(data: NewViewData) -> None:
    st.markdown(f"Score: {data.score}")
```

### 6. 탭 추가

```python
# web/app.py
tabs = st.tabs([..., "🆕 New"])
with tabs[-1]:
    new_tab_comp.render(bridge.new_data())
```

### 7. 테스트 작성 후 전체 확인

```bash
python -m pytest tests/ -q  # 754 + new tests PASS
```

---

## 새로운 Dashboard 탭 추가 방법

1. `web/components/new_tab.py` 생성
2. `DataBridge`에 ViewData + 메서드 추가 (Engine 없이 기존 데이터 활용 가능)
3. `web/app.py`에서 탭 추가
4. `web/styles/theme.py`에 필요한 CSS 추가
5. 테스트 작성

---

## Version 올리는 방법

1. `VERSION` 파일 수정:
   ```
   1.1.0
   ```

2. `Release_Notes.md` 업데이트 (상단에 새 버전 추가)

3. Git 태그 추가:
   ```bash
   git tag -a v1.1.0 -m "v1.1.0 Release"
   git push origin v1.1.0
   ```

4. GitHub Release:
   - GitHub Repository → **Releases** → **Create a new release**
   - Tag: v1.1.0
   - Release Notes 붙여넣기

---

## GitHub Release 절차

1. 모든 테스트 PASS 확인
2. `VERSION` 파일 업데이트
3. `Release_Notes.md` 업데이트
4. GitHub에 커밋 + 푸시
5. GitHub → Releases → New release
6. Tag version: `v1.1.0`
7. Release title: `DSS v1.1.0`
8. Description: Release Notes 내용
9. **Publish release**

---

## 의존성 업데이트 방법

```bash
# 현재 설치된 버전 확인
pip list | grep -E "streamlit|PyYAML|plotly|psutil"

# 최신 버전으로 업데이트
pip install --upgrade streamlit PyYAML plotly psutil

# requirements.txt 업데이트
pip freeze | grep -E "streamlit|PyYAML|plotly|psutil" > /tmp/new_req.txt

# 테스트
python -m pytest tests/ -q
```

업데이트 후 754개 PASS 확인 후 GitHub 반영.

---

## 로컬 개발 환경 세팅

```bash
# Python 3.12 가상환경
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
pip install pytest black mypy  # 개발 도구

# 실행
streamlit run app.py

# 테스트
python -m pytest tests/ -v
```

---

## 정기 점검 일정

| 주기 | 항목 |
|------|------|
| 매일 | Daily Checklist (Operations_Manual.md) |
| 매주 | 결정 패턴 리뷰, 이벤트 일정 확인 |
| 매월 | 가중치 검토, 로그 아카이브, 의존성 확인 |
| 분기 | 백테스트 결과 검토, 아키텍처 검토 |

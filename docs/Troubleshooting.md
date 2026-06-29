# DSS Troubleshooting Guide

문제 발생 시 이 순서로 진단하고 복구한다.

---

## 즉각 대응 절차 (1분 이내)

1. **🔄 새로고침 버튼** 클릭 → Engine 재실행
2. **브라우저 새로고침** (F5 또는 Ctrl+R)
3. **다른 브라우저**로 접속 시도
4. **5분 대기** 후 재접속 (Streamlit 자동 복구)

---

## 증상별 진단

### Dashboard가 아예 열리지 않음

```
진단 순서:
1. 인터넷 연결 확인
2. URL 정확성 확인 (YOUR_APP.streamlit.app)
3. Streamlit Cloud 상태 확인: https://status.streamlit.io
4. 앱이 sleep 상태 → "Yes, get this app back up!" 클릭
```

---

### "This app has encountered an error" 메시지

```
진단 순서:
1. 🔄 새로고침 → 해결되면 일시적 오류
2. Streamlit Cloud → Manage app → Logs 확인
3. 오류 메시지 종류 확인:
```

| 오류 메시지 | 원인 | 해결 |
|------------|------|------|
| ModuleNotFoundError | 패키지 미설치 | requirements.txt 확인 |
| AttributeError on DSSResult | Engine 버그 | Engine 로그 확인 |
| FileNotFoundError on config/ | config 파일 누락 | GitHub 업로드 확인 |
| MemoryError | 메모리 부족 | Streamlit Cloud 앱 재시작 |

---

### Engine 실패 (Diagnostics 탭 ❌ 표시)

```
진단 순서:
1. 🔄 새로고침 → Pipeline 재실행
2. 특정 Engine만 실패? → 해당 Engine 설정 파일(config/) 확인
3. 모든 Engine 실패? → SyntheticDataLoader 폴백 동작 중
   → Demo 데이터로 Dashboard는 계속 동작 (정상)
4. 로컬에서 재현: python -m pytest tests/ -q
```

---

### 데이터가 너무 오래됨 (Daily Op Check ⚠️ 데이터 최신)

```
진단 순서:
1. 🔄 새로고침 → 강제 재실행
2. run_id가 "DEMO"면 Demo 모드 → Pipeline 실패 상태
3. 로컬 실행으로 에러 확인:
   streamlit run app.py
4. 로그 확인: dss_integration/logs/dss.log
```

---

### Journal 저장 안 됨 (Daily Op Check ⚠️ Journal)

```
진단 순서:
1. web/data/ 폴더 존재 확인
2. web/data/journal.json 쓰기 권한 확인
3. Streamlit Cloud 환경에서는 재시작 시 journal 초기화됨
   → 로컬 백업 권장
```

---

### 모바일 화면 깨짐

```
진단 순서:
1. Chrome/Safari 최신 버전 사용 확인
2. 세로 모드로 접속
3. 브라우저 확대/축소 100% 확인
4. 강력 새로고침: Ctrl+Shift+R (모바일: 주소창 아래로 당기기)
```

---

### 탭이 너무 많아 보이지 않음 (모바일)

탭 영역을 좌우로 스크롤하면 숨겨진 탭을 볼 수 있다.

---

## 로그 분석

```bash
# 최근 오류 확인
grep "ERROR" dss_integration/logs/dss.log | tail -20

# 특정 날짜 로그
grep "2026-06-29" dss_integration/logs/dss.log

# Engine 실패 로그
grep "Pipeline failed\|Engine.*fail" dss_integration/logs/dss.log
```

---

## 복구 절차

### 복구 레벨 1 — 소프트 리셋 (1분)
```
Dashboard → 🔄 버튼 클릭
```

### 복구 레벨 2 — 앱 재시작 (3분)
```
Streamlit Cloud → Manage app → Reboot app
```

### 복구 레벨 3 — 재배포 (5분)
```
GitHub → 파일 재업로드 or 빈 커밋
→ Streamlit Cloud 자동 재배포
```

### 복구 레벨 4 — 로컬 실행 (즉시)
```bash
# Streamlit Cloud가 완전히 다운된 경우
pip install -r requirements.txt
streamlit run app.py
# localhost:8501에서 로컬 실행
```

---

## 알 수 없는 오류 발생 시

1. Streamlit Cloud Logs에서 전체 스택 트레이스 복사
2. 오류 발생 직전 수행한 작업 메모
3. `python -m pytest tests/ -q`로 기존 754개 테스트 확인
4. 테스트 실패 항목이 없으면 → 환경 문제
5. 테스트 실패가 있으면 → 코드 문제 (롤백 고려)

---

## Rollback 방법

GitHub에서 이전 커밋으로 돌아가기:
1. GitHub Repository → **Commits** 클릭
2. 정상 동작하던 커밋 찾기
3. **<>** (Browse files) 클릭
4. 해당 버전 파일 다운로드 후 재업로드

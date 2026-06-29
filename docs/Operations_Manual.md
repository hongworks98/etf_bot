# DSS Operations Manual

**버전:** v1.0.0  
**대상:** 시스템 운영자

---

## Daily Checklist

매일 아침 (9:00 KST 기준):

- [ ] Dashboard 접속 — URL 정상 동작 확인
- [ ] Market Status 카드 확인 (🟢/🟡/🔴)
- [ ] Today 탭 — BUY/SELL/HOLD 결정 확인
- [ ] 신뢰도(Confidence) 50% 이상 확인
- [ ] Diagnostics 탭 → ☑️ 체크리스트 7항목 확인
  - ✅ 데이터 최신
  - ✅ 모든 Engine 성공
  - ✅ Recommendation 생성
  - ✅ Journal 저장
  - ✅ Cache 정상
  - ✅ Engine Monitor 정상
  - ✅ Dashboard 정상
- [ ] 이상 항목 있으면 🔄 새로고침 후 재확인

---

## Weekly Checklist

매주 월요일:

- [ ] 지난 주 결정 패턴 확인 (History 탭)
- [ ] BUY/SELL 변환이 많았으면 Volatility 주의
- [ ] 시장 이벤트 확인 (FOMC, NFP 일정)
- [ ] Streamlit Cloud 앱 정상 동작 확인
- [ ] 로그 파일 크기 확인 (5MB 미만이면 정상)

---

## Monthly Checklist

매월 첫째 주:

- [ ] 지난 달 결정 정확도 검토 (History 탭)
- [ ] 장기 추세 확인 (Macro Score 방향)
- [ ] config/ YAML 가중치 검토 필요 여부 확인
- [ ] requirements.txt 패키지 버전 최신화 여부 확인
- [ ] GitHub Repository 정상 동작 확인

---

## Engine Health 확인

⚙️ **System 탭** → **Engine Monitor** 섹션:

| 상태 | 의미 | 조치 |
|------|------|------|
| ✅ OK | 정상 | 없음 |
| ⚠️ DEGRADED | 일부 기능 저하 | 다음 날 재확인 |
| ❌ FAILED | Engine 실패 | 🔄 즉시 재실행 |

모든 Engine이 FAILED면:
1. 🔄 새로고침 클릭
2. 5분 후 재접속
3. 그래도 실패면 Streamlit Cloud 앱 재시작

---

## Cache 확인

Diagnostics 탭 → **⑤ Cache 정상** 항목:
- ✅: TTL 300초 캐시 정상
- ⚠️: 데이터 갱신 안 됨 → 🔄 새로고침

캐시 강제 초기화: 🔄 버튼 클릭 (Engine 재실행 + 캐시 삭제)

---

## 로그 확인

로그 파일 위치: `dss_integration/logs/dss.log`

로컬 환경:
```bash
# 최근 100줄
tail -100 dss_integration/logs/dss.log

# 오류만
grep "ERROR\|WARNING" dss_integration/logs/dss.log

# 오늘 로그
grep "$(date +%Y-%m-%d)" dss_integration/logs/dss.log
```

로그 로테이션: 5MB 초과 시 자동 → dss.log.1 ~ dss.log.5

---

## 백업 방법

중요 데이터 파일:
```
web/data/journal.json    ← 결정 일지 (매일 자동 저장)
web/data/watchlist.json  ← 관심 종목
```

백업 방법 (로컬):
```bash
# 백업
cp web/data/journal.json backup/journal_$(date +%Y%m%d).json
cp web/data/watchlist.json backup/watchlist_$(date +%Y%m%d).json
```

Streamlit Cloud 배포 환경에서는 앱 재시작 시 데이터가 초기화될 수 있다.  
중요 기록은 주기적으로 로컬에 다운로드 권장.

---

## 업데이트 방법

1. 로컬에서 코드 수정
2. 테스트 실행: `python -m pytest tests/ -q`
3. 754개 모두 PASS 확인
4. GitHub에 수정 파일 업로드
5. Streamlit Cloud 자동 재배포 (약 1분)
6. 배포 후 Dashboard 정상 동작 확인

---

## Streamlit Cloud 앱 재시작 방법

1. https://share.streamlit.io 접속
2. 해당 앱 클릭
3. 우상단 메뉴(⋮) → **Reboot app**
4. 1~2분 후 재접속

---

## 알림 센터 관리

⚙️ **System 탭** → **Notification Center**:

- 🚨 CRITICAL: 즉시 조치 필요
- ⚠️ WARNING: 다음 날까지 확인
- ℹ️ INFO: 참고 사항

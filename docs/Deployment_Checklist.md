# DSS Deployment Checklist

## 사전 준비
- [ ] GitHub 계정 생성 완료
- [ ] Streamlit Cloud 계정 생성 완료
- [ ] DSS 프로젝트 폴더 준비 완료

## GitHub 업로드
- [ ] GitHub Repository 생성 (Public)
- [ ] Repository 이름 확인 (예: dss-dashboard)
- [ ] 코드 전체 업로드
- [ ] `.gitignore` 적용 확인 (.env, secrets.toml 미포함 확인)
- [ ] `app.py` 루트에 존재 확인
- [ ] `requirements.txt` 존재 확인
- [ ] `runtime.txt` 존재 확인 (python-3.12)
- [ ] `web/` 폴더 업로드 확인
- [ ] `engines/` 폴더 업로드 확인
- [ ] `config/` 폴더 업로드 확인

## Streamlit Cloud 배포
- [ ] Streamlit Cloud 로그인 (GitHub 계정 연동)
- [ ] New app 클릭
- [ ] Repository 선택 (YOUR_USERNAME/dss-dashboard)
- [ ] Branch: main 선택
- [ ] Main file path: app.py 입력
- [ ] Deploy! 클릭
- [ ] 배포 로그 오류 없음 확인
- [ ] 배포 완료 URL 확인

## 배포 후 확인
- [ ] URL 접속 성공
- [ ] 로딩 화면 표시 (DSS Engine 실행 중...)
- [ ] Market Status 카드 표시 (최상단)
- [ ] 🏠 Today 탭 — BUY/SELL/HOLD 결정 표시
- [ ] 📊 Market 탭 — 거시경제 + 시장 분석 표시
- [ ] 💼 Portfolio 탭 — 포트폴리오 배분 표시
- [ ] 📅 History 탭 — 결정 일지 표시
- [ ] 🔍 Discover 탭 — ETF 검색 기능 동작
- [ ] ⚙️ System 탭 — Engine 상태 표시
- [ ] 🔧 Diagnostics 탭 — 운영 체크리스트 표시
- [ ] 🔄 새로고침 버튼 동작

## 모바일 확인
- [ ] 스마트폰에서 URL 접속
- [ ] 화면 레이아웃 정상 (모바일 최적화)
- [ ] 탭 스크롤 동작
- [ ] BUY/SELL/HOLD 카드 표시
- [ ] 홈 화면에 추가 (북마크)

## 운영 준비
- [ ] 매일 접속 URL 공유 완료
- [ ] 모바일 북마크 저장
- [ ] `docs/User_Manual.md` 숙지
- [ ] `docs/Operations_Manual.md` 숙지
- [ ] 장애 시 대응: `docs/Troubleshooting.md` 저장

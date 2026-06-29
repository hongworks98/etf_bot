# DSS Deployment Guide
**대상:** 개발 경험 없는 사용자  
**목표:** GitHub 업로드 → Streamlit Cloud 배포 → 모바일 접속  
**소요 시간:** 약 20분

---

## 사전 준비

필요한 계정 2개:
1. **GitHub** — https://github.com (코드 저장소)
2. **Streamlit Cloud** — https://streamlit.io/cloud (무료 배포)

---

## STEP 1. GitHub 계정 만들기

1. https://github.com 접속
2. **Sign up** 클릭
3. 이메일 / 비밀번호 / 사용자명 입력
4. 이메일 인증 완료

[스크린샷 - GitHub Sign up 화면]

---

## STEP 2. GitHub Repository 만들기

1. 로그인 후 우상단 **+** → **New repository** 클릭
2. Repository name: `dss-dashboard` (소문자, 하이픈)
3. **Public** 선택 (Streamlit Cloud 무료 플랜 조건)
4. **Create repository** 클릭

[스크린샷 - GitHub Repository 생성 화면]

> 중요: Private 저장소는 Streamlit Cloud 무료 플랜에서 배포 불가

---

## STEP 3. 코드 업로드

### 방법 A. GitHub 웹 업로드 (권장)

1. Repository 페이지에서 **uploading an existing file** 클릭
2. DSS 프로젝트 폴더 전체를 드래그&드롭
3. **Commit changes** 클릭

[스크린샷 - GitHub 파일 업로드 화면]

### 방법 B. Git 명령어

```bash
cd /path/to/dss-project
git init
git add .
git commit -m "Initial commit: DSS v1.0.0"
git remote add origin https://github.com/YOUR_USERNAME/dss-dashboard.git
git push -u origin main
```

업로드 시 `.gitignore` 파일이 자동으로 민감 정보(.env, secrets.toml)를 제외한다.

---

## STEP 4. 업로드 확인

Repository에서 다음 파일 확인:

```
app.py             ← 실행 진입점
requirements.txt   ← 패키지 목록
runtime.txt        ← Python 버전
web/app.py         ← 메인 대시보드
engines/           ← 분석 엔진
config/            ← 설정 파일
```

[스크린샷 - GitHub Repository 파일 목록]

---

## STEP 5. Streamlit Cloud 가입

1. https://streamlit.io/cloud 접속
2. **Get started** 클릭
3. **Continue with GitHub** 선택
4. GitHub 접근 권한 승인

[스크린샷 - Streamlit Cloud 로그인 화면]

---

## STEP 6. 앱 배포

1. **New app** 클릭
2. 설정:
   - Repository: `YOUR_USERNAME/dss-dashboard`
   - Branch: `main`
   - Main file path: `app.py`
3. **Deploy!** 클릭 (1~3분 소요)

[스크린샷 - Streamlit Cloud 배포 설정 화면]

[스크린샷 - 배포 로그 화면]

---

## STEP 7. 배포 완료 확인

```
https://YOUR_APP_NAME.streamlit.app
```

- [ ] URL 접속 성공
- [ ] Dashboard 화면 표시
- [ ] Market Status 카드 표시
- [ ] 7개 탭 모두 동작

[스크린샷 - 배포 완료 화면]

---

## STEP 8. 모바일 확인

스마트폰에서 URL 접속 후 홈 화면에 추가하면 앱처럼 사용 가능하다.

[스크린샷 - 모바일 화면]

---

## 업데이트 방법

GitHub에 수정 파일 업로드 → Streamlit Cloud 자동 재배포 (약 1분)

---

문제가 생기면 `docs/Deployment_FAQ.md` 참조

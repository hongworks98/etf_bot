# DSS Deployment FAQ

자주 발생하는 배포 문제와 해결 방법.

---

## 빌드 오류

### Q. ModuleNotFoundError: No module named 'streamlit'

**원인:** requirements.txt가 누락되었거나 업로드되지 않음  
**해결:**
1. GitHub Repository에 `requirements.txt` 존재 확인
2. 파일 내용에 `streamlit>=1.35.0` 포함 확인
3. Streamlit Cloud에서 **Reboot app** 클릭

---

### Q. ModuleNotFoundError: No module named 'yaml'

**원인:** PyYAML 미설치  
**해결:** `requirements.txt`에 다음 추가:
```
PyYAML>=6.0.1
```

---

### Q. Build 실패 — "Python version not supported"

**원인:** `runtime.txt`의 Python 버전 오류  
**해결:** `runtime.txt` 내용 확인:
```
python-3.12
```
형식 정확히 지켜야 함 (공백 없음, 소문자)

---

### Q. Build 시 오류 로그에 "No module named 'engines'"

**원인:** `engines/` 폴더가 GitHub에 업로드되지 않음  
**해결:**
1. GitHub Repository에서 `engines/` 폴더 존재 확인
2. 없으면 폴더 전체 다시 업로드
3. `__init__.py` 파일 포함 확인

---

## 실행 오류

### Q. 앱이 흰 화면만 표시됨

**원인:** JavaScript 로딩 지연 또는 브라우저 캐시 문제  
**해결:**
1. 브라우저 강력 새로고침: `Ctrl+Shift+R` (Windows) / `Cmd+Shift+R` (Mac)
2. 시크릿 모드로 접속
3. 다른 브라우저로 시도

---

### Q. "This app has encountered an error" 메시지

**원인:** Python 런타임 오류  
**해결:**
1. Streamlit Cloud 대시보드에서 해당 앱 클릭
2. **Manage app** → **Logs** 에서 오류 내용 확인
3. 오류 메시지를 `docs/Troubleshooting.md`와 대조

---

### Q. Cache 오류 — 데이터가 너무 오래됨

**원인:** Streamlit 캐시(TTL 5분)가 예상보다 오래 유지됨  
**해결:** Dashboard에서 **🔄** 버튼 클릭 (강제 새로고침)

---

### Q. Session 오류 — "Session state not found"

**원인:** 장시간 비활성 후 세션 만료  
**해결:** 브라우저 페이지 새로고침 (F5)

---

## GitHub 연결 오류

### Q. GitHub 계정 연결이 안 됨

**원인:** Streamlit Cloud의 GitHub OAuth 권한 문제  
**해결:**
1. https://github.com/settings/applications 접속
2. **Authorized OAuth Apps**에서 Streamlit 확인
3. 없으면 Streamlit Cloud에서 재로그인

---

### Q. Repository를 찾을 수 없음

**원인:** Repository가 Private으로 설정됨  
**해결:**
1. GitHub Repository → **Settings** → **General**
2. **Danger Zone** → **Change repository visibility** → **Public**

---

## Secrets 오류

### Q. "Secret not found" 또는 API 키 오류

**원인:** `.streamlit/secrets.toml` 파일이 배포에 포함되지 않음  
**해결 (Streamlit Cloud 환경 변수 설정):**
1. Streamlit Cloud 앱 대시보드 → **Settings** → **Secrets**
2. `secrets.toml` 내용 그대로 붙여넣기

현재 DSS v1.0.0은 외부 API 키 없이 동작하므로 이 오류는 발생하지 않는다.

---

## 앱 속도 문제

### Q. 앱이 너무 느림

**원인:** Streamlit Cloud 무료 플랜의 메모리/CPU 제한  
**해결:**
- 5분 TTL 캐시가 적용되어 있으므로 처음 로딩 후에는 빠름
- 첫 로딩만 1~3초 소요되는 것은 정상

---

### Q. 앱이 자동으로 잠듦 (Sleep)

**원인:** Streamlit Cloud 무료 플랜에서 일정 시간 미접속 시 자동 sleep  
**해결:** URL 접속 후 **Yes, get this app back up!** 클릭 (30초 소요)

---

## 기타

### Q. 모바일에서 화면이 깨짐

**원인:** 구형 브라우저 또는 시스템 브라우저 사용  
**해결:** Chrome 또는 Safari 최신 버전으로 접속

---

### Q. 업데이트 후 변경사항이 반영되지 않음

**원인:** 브라우저 캐시  
**해결:**
1. `Ctrl+Shift+R` 강력 새로고침
2. 또는 URL 끝에 `?v=2` 추가 후 접속

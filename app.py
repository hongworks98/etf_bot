"""
app.py — DSS Decision Support System
Entry Point (유일한 실행 파일)

실행:
    pip install -r requirements.txt
    streamlit run app.py

★★★★★ 원칙:
- Business Logic 없음
- Engine 호출 없음
- web/app.py 에 완전 위임
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# web/app.py 실행
# st.set_page_config()는 web/app.py 모듈 레벨에서 호출되므로
# import 시 자동으로 첫 번째 Streamlit 명령어로 실행됩니다.
from web.app import main
main()

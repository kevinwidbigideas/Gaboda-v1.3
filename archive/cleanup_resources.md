# Gaboda 리소스 정리 가이드

이 가이드는 Gaboda 애플리케이션의 **랜딩 페이지**와 **테스트 화면**만 실행하는 데 필요한 필수 리소스 목록입니다. 이외의 파일들은 환경을 단순화하기 위해 삭제하거나 보관할 수 있습니다.

## 1. 핵심 필수 파일 (삭제 금지)
Flask 서버를 시작하고 랜딩 및 테스트 페이지를 렌더링하는 데 반드시 필요한 파일들입니다.

*   **`main.py`**: 애플리케이션의 진입점입니다.
*   **`app.py`**: Flask 앱 초기화 및 데이터베이스 설정 파일입니다.
*   **`utils.py`**: 두 페이지 모두에서 사용하는 헬퍼 함수(헤더, 푸터, 공통 헤드 등)가 포함되어 있습니다.
*   **`requirements.txt`**: Python 종속성 목록(Flask 등)입니다.
*   **`travis.db`**: SQLite 데이터베이스 (없으면 자동 생성되지만, 세션 관리에 필요합니다).

## 2. 블루프린트 파일 (라우트 경로)
*   **`blueprints/__init__.py`**: 블루프린트 패키지 초기화 파일입니다.
*   **`blueprints/home.py`**: 랜딩 페이지(` / `)를 처리합니다.
*   **`blueprints/test.py`**: 테스트 화면(` /test `)을 처리합니다.
*   **`blueprints/api.py`**: **필수**. 헤더의 로그인/세션 확인 로직(` /api/session_user `)을 처리합니다. 삭제 시 브라우저 콘솔에 네트워크 오류가 발생할 수 있습니다.

## 3. 템플릿 및 정적 자산
*   **`templates/index.html`**: 랜딩 페이지용 HTML 템플릿입니다.
*   **`static/`**:
    *   `static/section1_img/`: 랜딩 페이지 그리드에 사용되는 이미지들 (`bali_sunset.png`, `effel.png` 등).
    *   `static/4travellers_wide.png`: "How It Works" 섹션에 사용됩니다.
    *   `static/carda.png`: (사용 여부 확인 후 삭제 가능).

## 4. 제거 / 보관 가능한 파일 (랜딩 + 테스트만 필요한 경우)

다음 파일들은 랜딩 페이지나 테스트 페이지를 *화면에 띄우는 데*는 필요하지 않습니다.

> **주의:** `result.py`와 모델 파일들을 삭제하면 테스트 마지막의 **"제출(Submit)"** 기능이 작동하지 않습니다. 테스트 페이지 로딩과 문항 선택은 가능하지만, 마지막 문항에서 "제출" 클릭 시 오류가 발생합니다.

### 로직 및 백엔드 (결과 페이지가 필요 없다면 삭제 가능)
*   `blueprints/result.py`: 테스트 제출 및 결과 계산을 처리합니다.
*   `blueprints/result/`: 중복/구 버전 폴더 (삭제 안전).
*   `rf_travel_model.joblib`: 여행 페르소나 분석용 랜덤 포레스트 모델 (대용량 파일).
*   `rf_travel_model_metadata.json`: 모델 메타데이터.
*   `travis_final_1000_personas_20260128.csv`: 원본 데이터 파일.
*   `utils_back.py`, `utils_j.py`: 백업/구 버전 유틸리티 파일.

### 유지보수 및 개발 스크립트 (삭제 안전)
*   `check_env.py`
*   `check_friends_db.py`
*   `cleanup_call_llm.py`
*   `cleanup_mock.py`
*   `fix_mock_function.py`
*   `test_import.py`
*   `test_edit.md`
*   `downgradeguide.md`
*   `requirement.md`
*   `run_server.bat` (편의상 유지 가능하나 코드 실행에는 필수 아님)
*   `llm_prompts.txt`, `llm_response.txt`
*   `캡처.PNG`

## 5. `main.py` 수정 (Result 제거 시 필수)
`blueprints/result.py`를 삭제하기로 결정했다면, 반드시 `main.py`와 `blueprints/__init__.py`에서 `result_bp` 관련 코드를 수정해야 합니다.

**`main.py` 수정 예시:**
```python
from app import app, init_db
from blueprints import home_bp, test_bp, api_bp # result_bp 제거

app.register_blueprint(home_bp)
app.register_blueprint(test_bp)
app.register_blueprint(api_bp)
# app.register_blueprint(result_bp) # 제거됨
```

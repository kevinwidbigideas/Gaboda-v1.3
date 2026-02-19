# Gaboda v1.3 Downgrade Guide

이 문서는 TraVTI 서비스(여행 성향 테스트)의 핵심 기능인 **메인 화면 -> 테스트 진행 -> 결과 화면** 흐름만 남기고, 복잡한 LLM 연동 및 여행 계획 생성 기능을 제거하여 가볍게 만들기 위한 가이드입니다.
목적: 유저 Demand Check용 (실제 기능보다는 서비스 컨셉 전달 및 성향 분석 결과 제공에 초점)

---

## 1. 파일 구조 및 역할 설명 (현재 상태)

### 핵심 실행 파일
| 파일명 | 역할 | 연결성 |
| :--- | :--- | :--- |
| `app.py` | Flask 앱 초기화, 데이터베이스(`travis.db`) 연결 설정, 세션 관리 | 모든 블루프린트 및 DB 접근의 기초 |
| `main.py` | 앱의 진입점. 각종 블루프린트(`home`, `test`, `result` 등)를 등록하고 서버 실행 | `app.py`와 `blueprints/` 폴더 내 모듈들을 연결 |

### Blueprints (기능 모듈)
`blueprints/` 폴더 내의 주요 파일들입니다.

| 파일명 | 역할 | Downgrade 시 필요 여부 | 비고 |
| :--- | :--- | :--- | :--- |
| `home.py` | **메인 화면**. 서비스 소개 및 '테스트 시작하기' 버튼 제공 | **필수** | 수정 없이 사용 가능 |
| `test.py` | **테스트(설문) 화면**. 20개 문항 제공 및 응답 수집 | **필수** | 설문 로직 및 UI 포함 |
| `result.py` | **결과 화면**. MBTI/성향 분석 결과 표시 및 친구 추가 기능 | **필수** | 단, OCR(티켓 인식) 및 복잡한 일정 생성 로직은 제거 필요 |
| `api.py` | 공통 API (유저 정보 조회, 로그인/로그아웃 등) | **필수 (일부분)** | 성향 분석 결과 조회 API는 유지, LLM 추천 API는 제거 |
| `my_plans.py` | 내 여행 일정 목록 조회 | **삭제 권장** | 결과 화면 이후의 심화 기능임 |
| `itinerary.py` | 상세 일정표 보기 및 수정 | **삭제 권장** | LLM이 생성한 일정 보는 곳 |
| `entry_upload.py` | 여행 일정 업로드 (PDF/이미지) | **삭제 권장** | OCR 기능과 연동됨 |
| `entry_fill.py` | 여행 일정 수동 입력 | **삭제 권장** | - |
| `llm_api.py` | LLM 관련 API 처리 | **삭제 권장** | - |
| `llm_client.py` | LLM 호출 클라이언트 | **삭제 권장** | - |

### 기타 중요 파일/폴더
| 파일명 | 역할 | Downgrade 시 필요 여부 |
| :--- | :--- | :--- |
| `utils.py` | 공통 헤더/CSS(`COMMON_HEAD`), 네비게이션 바 생성 등 헬퍼 함수 | **필수** | UI 통일성을 위해 필요 |
| `utils_j.py` | (구) 유틸리티 파일 | **삭제 가능** | utils.py로 통합됨 (archive 이동) |
| `static/` | 이미지, CSS, JS 등 정적 파일 | **필수** | 디자인 요소 유지 |
| `rf_travel_model.joblib` | 성향 분석(TraVTI Label)을 위한 머신러닝 모델 | **삭제 가능** | Rule-based 로직으로 대체됨 (archive 이동) |
| `rf_travel_model_metadata.json` | 모델 메타데이터 | **삭제 가능** | - (archive 이동) |
| `travis.db` | 사용자 데이터 및 친구 데이터 저장소 (시드 데이터) | **삭제 가능** | 기본 설문 기능은 자동 생성된 DB 사용 (archive 이동) |
| `ocr/` | 광학 문자 인식 관련 코드 | **삭제 가능** | 티켓 인식 기능 제외 시 불필요 |
| `llm_resource/` | LLM 프롬프트 및 리소스 | **삭제 가능** | - |

---

## 2. Downgrade를 위한 핵심 파일 및 수정 가이드

단순히 **메인 -> 테스트 -> 결과** 흐름만 남기기 위해 남겨야 할 핵심 파일과 수정 사항입니다.

### 1) 남겨야 할 폴더 및 파일 리스트
- `app.py`, `main.py`
- `utils.py` (헤더 등 공통 UI)
- `blueprints/`
  - `__init__.py`
  - `home.py`
  - `test.py`
  - `result.py`
  - `api.py`
- `static/` (전체 유지)
- `requirements.txt`

### 2) 파일별 수정 가이드 (Diet Plan)

#### [main.py]
- 불필요한 블루프린트 등록 코드 제거 또는 주석 처리
  - `my_plans_bp`, `entry_upload_bp`, `entry_fill_bp`, `itinerary_bp`, `llm_api_bp` 등등 import 및 `app.register_blueprint` 삭제.
  - 오직 `home_bp`, `test_bp`, `result_bp`, `api_bp` 만 남김.

#### [blueprints/result.py]
- **목적**: 결과(TraVTI Label)를 보여주고, 친구들과 공유하는 화면까지만 제공.
- **제거 대상**:
  - `ocr` 관련 import (`from ocr.ocr_utils ...`) 및 `/api/analyze-itinerary` 라우트.
  - "일정 생성하기" 버튼 클릭 시 동작하는 복잡한 로직. (단순히 "참여해주셔서 감사합니다" 알림으로 대체하거나 제거)
  - 파일 업로드 기능 (`ticket-depart-input` 등 HTML 요소 및 관련 JS).
- **유지 대상**:
  - `/submit-answers` (성향 분석 및 DB 저장)
  - `/result` (분석된 결과 페이지 렌더링)
  - 친구 카드 드래그앤드롭 기능 (시각적 재미 요소)

#### [blueprints/api.py]
- **목적**: 프론트엔드에서 필요한 유저 정보 제공.
- **제거 대상**:
  - `/generate-personal-recommendations` (LLM 호출 로직 포함됨 -> 삭제).
- **유지 대상**:
  - `/get_member_stats`, `/login_random`, `/session_user` 등 기본 유저 정보 조회 API.

---

## 3. 요약: Downgrade 작업 순서

1.  **백업**: 현재 프로젝트를 통째로 백업해둡니다.
2.  **삭제**: `blueprints` 폴더에서 `home.py`, `test.py`, `result.py`, `api.py`, `__init__.py`를 제외한 모든 `.py` 파일을 삭제(혹은 `_backup` 폴더로 이동)합니다.
3.  **정리**:
    - `main.py`에서 삭제된 블루프린트 import 구문을 지웁니다.
    - `result.py`에서 `ocr` 관련 import와 코드를 지웁니다.
    - `api.py`에서 `llm` 관련 코드를 지웁니다.
4.  **테스트**: `python main.py`를 실행하여 웹사이트가 뜨는지 확인합니다.
    - 메인 화면 접속 -> 테스트 시작 -> 문항 응답 -> 결과 화면 출력 확인.

이 가이드를 따라 진행하면 가벼운 Demand Check용 버전이 완성됩니다.

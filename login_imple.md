# Gaboda Auth Integration Guide (Google/Kakao & Supabase)

이 문서는 Gaboda 프로젝트에 Google 및 Kakao 소셜 로그인을 적용하고, Supabase를 이용해 유저 DB를 관리하는 방법을 설명합니다.

---

## 1. Supabase 프로젝트 설정 (User DB & Auth)
Supabase는 Firebase의 오픈소스 대안으로, 인증(Authentication)과 데이터베이스(PostgreSQL)를 모두 제공합니다.

### 1.1 프로젝트 생성
1. [Supabase](https://supabase.com/) 회원가입 및 로그인.
2. `New Project` 클릭 -> `Gaboda_Auth` 이름으로 생성.
3. Database Password 설정 (꼭 기억하세요).
4. Region은 `Seoul` (또는 가까운 곳) 선택.
5. `Create new project` 클릭.

### 1.2 API URL & Key 확인
1. 프로젝트 대시보드 -> 좌측 메뉴 `Settings` (톱니바퀴) -> `API`.
2. `Project URL` 복사 (예: `https://xyz.supabase.co`).
-> https://utsairuqlvobwzzofetk.supabase.co
3. `Project API keys` -> `anon` key `public` 복사.
-> eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV0c2FpcnVxbHZvYnd6em9mZXRrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzOTQwMDYsImV4cCI6MjA4Njk3MDAwNn0.6K3ceF0obC3TTJCZBg6I_qY3EDrw-VNlI4w4CzdqZfw

   - **주의:** `service_role` 키는 절대 클라이언트에 노출하면 안 됩니다.

### 1.3 Table 생성 (Service DB)
Supabase의 `auth.users` 테이블은 인증 정보(이메일, 비밀번호 등)만 관리합니다. 실제 서비스 데이터는 `public` 스키마에 별도 테이블로 관리하는 것이 확장성과 보안에 좋습니다.

#### A. 유저 프로필 테이블 (`travis_user_data`)
- **목적:** 로그인 시 보여줄 기본 정보 및 최종 성향 결과.
- **Columns:**
   - `id`: `uuid`, Primary Key, FK -> `auth.users.id`.
   - `email`: `text`.
   - `name`: `text`.
   - `mbti`: `text` (예: ESTJ).
   - `travti_label`: `text` (예: 경로 대장).
   - `vector_score`: `jsonb` (상세 점수 저장).
   - `gender`: `text` (예: M/F, 선택 사항).
   - `birth_date`: `date` (예: 1995-05-20, 선택 사항).
   - `created_at`: `timestamptz`.

#### B. 설문 응답 테이블 (`survey_responses`) (권장)
- **목적:** 상세 분석, 3인 이상 그룹 리포트, 알고리즘 개선용 원본 데이터.
- **Columns:**
   - `id`: `bigint`, Primary Key (Auto Increment).
   - `user_id`: `uuid`, FK -> `travis_user_data.id`.
   - `session_id`: `text` (비회원/게스트 응답 추적용).
   - `responses`: `jsonb` ({"q1": 1, "q2": -1...} 형태).
   - `created_at`: `timestamptz`.

#### C. RLS (Row Level Security) 설정
- 두 테이블 모두 `Enable RLS` 체크.
- Policy 추가: `Authenticated users can select/insert their own data`.

---

## 2. Google 로그인 설정 (OAuth)

### 2.1 Google Cloud Console 설정
1. [Google Cloud Console](https://console.cloud.google.com/) 접속.
2. 새 프로젝트 생성 (`Gaboda-Login`).
3. `API 및 서비스` -> `OAuth 동의 화면` (OAuth Consent Screen).
   - `User Type`: `External` (외부) 선택.
   - 앱 정보 입력 (이름, 이메일 등).
4. `사용자 인증 정보` (Credentials) -> `사용자 인증 정보 만들기` -> `OAuth 클라이언트 ID`.
   - 애플리케이션 유형: `웹 애플리케이션`.
   - 이름: `Supabase Login`.
   - **승인된 리디렉션 URI** (Authorized redirect URIs):
     - Supabase 대시보드 -> `Authentication` -> `Providers` -> `Google` 섹션에 있는 `Callback URL`을 복사하여 여기에 붙여넣기.
     - (보통 `https://<YOUR-PROJECT-ID>.supabase.co/auth/v1/callback` 형태).
5. 생성 후 `Client ID`와 `Client Secret` 복사.

### 2.2 Supabase에 연동
1. Supabase 대시보드 -> `Authentication` -> `Providers`.
2. `Google` 선택 -> `Enabled` 활성화.
3. 2.1에서 복사한 `Client ID`와 `Client Secret` 입력.
4. `Save`.

---

## 3. Kakao 로그인 설정 (OAuth)

### 3.1 Kakao Developers 설정
1. [Kakao Developers](https://developers.kakao.com/) 접속 및 로그인.
2. `내 애플리케이션` -> `애플리케이션 추가하기`.
3. 좌측 메뉴 `플랫폼` -> `Web` 등록.
   - 사이트 도메인: `http://localhost:5000` (개발 환경), `https://your-production-url.com` (배포 환경).
   - **중요:** Supabase의 Auth URL 도메인(`https://<YOUR-PROJECT-ID>.supabase.co`)도 추가해야 할 수 있음.
4. 좌측 메뉴 `카카오 로그인`.
   - 상태를 `ON`으로 변경.
   - **Redirect URI** 등록:
     - Supabase 대시보드 -> `Authentication` -> `Providers` -> `Kakao` 섹션의 `Callback URL`을 복사하여 붙여넣기.
5. 좌측 메뉴 `앱 키`.
   - `REST API 키` 복사.

### 3.2 Supabase에 연동
1. Supabase 대시보드 -> `Authentication` -> `Providers`.
2. `Kakao` 선택 -> `Enabled` 활성화.
3. `REST API Key` 입력 (Client Secret은 선택 사항이거나 Admin Key 사용, 보통 REST API Key를 Client ID란에 입력).
   - *Supabase 설정 화면의 안내를 따르세요. 보통 `Client ID` 필드에 REST API Key를 넣습니다.*
4. `Save`.

---

## 4. 구현 과정 (Code Implementation Plan)

### 4.1 Frontend (utils.py & HTML)
- Supabase JS 라이브러리 추가 (`CDN`).
- 로그인 버튼 클릭 시 `supabase.auth.signInWithOAuth({ provider: 'google' })` 호출.
- 로그인 성공 시 Supabase가 세션(JWT)을 반환.

### 4.2 Backend (Flask)
- 클라이언트가 받은 JWT(Access Token)를 백엔드 API로 전송.
- 백엔드에서 Supabase Python Client(`supabase-py`)를 사용해 토큰 검증 또는 유저 정보 조회.
- 검증 성공 시 Flask `session`에 `user_id` 저장 (로그인 유지).

### 4.3 데이터 동기화
- 로그인 시점(`onAuthStateChange`)에 Supabase `travis_user_data` 테이블에 유저 정보가 없으면 기본 레코드 생성.
- 설문 결과 제출 시 이 테이블 업데이트.

---

## 5. 전달해 주셔야 할 정보 (For Developer)
구현을 위해 다음 정보들을 `.env` 파일이나 채팅으로 알려주셔야 합니다.

1. **Supabase Project URL**: `https://...`
2. **Supabase Project API Key (anon/public)**: `eyJ...`
3. (선택) **Google Client ID** (Frontend 전용 구현 시 필요할 수 있음)



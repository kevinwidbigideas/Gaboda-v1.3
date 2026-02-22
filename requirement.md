# 프로젝트 요구사항 (Project Requirements)

이 문서는 **TraVTI** 프로젝트를 실행하기 위해 필요한 최소한의 환경과 라이브러리 목록입니다.

## 1. 시스템 환경 (System Environment)
- **Python Version**: Python 3.8 이상

## 2. 필수 라이브러리 (Core Dependencies)
애플리케이션 실행을 위해 반드시 설치해야 하는 패키지입니다.

| 라이브러리 | 설명 |
|---|---|
| **Flask** | 웹 애플리케이션 프레임워크 |
| **Supabase** | 사용자 인증 및 데이터베이스 클라이언트 |
| **python-dotenv** | 환경 변수(.env) 로드 |
| **Requests** | HTTP 통신 (Supabase 의존성) |

## 3. 설치 방법
프로젝트 루트 경로에서 다음 명령어를 실행하세요.

```bash
pip install -r requirements.txt
```

## 4. 환경 변수 설정
`.env` 파일을 생성하고 다음 정보를 입력해야 합니다. (Supabase 대시보드 참고)

```ini
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
FLASK_SECRET_KEY=your_secret_key
```

## 5. 실행 방법

```bash
python main.py
```

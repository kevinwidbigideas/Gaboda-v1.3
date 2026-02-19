# 프로젝트 요구사항 (Project Requirements)

이 문서는 현재 프로젝트(**TraVTI**)를 실행하고 개발하기 위해 필요한 환경과 라이브러리 목록을 정의합니다.

## 1. 시스템 환경 (System Environment)

- **OS**: Windows (권장), macOS, Linux
- **Python Version**: Python 3.9 이상
  - 머신러닝 라이브러리 호환성 및 관리를 위해 **Anaconda** 또는 **Miniconda** 환경 사용을 권장합니다.

## 2. 필수 라이브러리 (Core Dependencies)

현재 웹 애플리케이션(`app.py`, `main.py` 등)을 실행하기 위해 반드시 필요한 패키지입니다.

| 라이브러리 | 버전(권장) | 용도 |
|---|---|---|
| **Flask** | 최신 버전 | 웹 애플리케이션 프레임워크 및 라우팅 |

설치 명령어:
```bash
pip install flask
```

## 3. 데이터 및 ML 관련 (Optional / Legacy Model)

프로젝트 내에 머신러닝 모델(`rf_travel_model.joblib`) 및 백업 스크립트(`main_backup.py`, `blueprints/result/result.py`)가 포함되어 있습니다.
이러한 레거시 기능이나 ML 모델을 다시 활성화/사용하거나 분석 스크립트를 실행하려면 다음 라이브러리가 필요합니다.

| 라이브러리 | 용도 |
|---|---|
| **pandas** | 데이터 처리 및 분석 |
| **numpy** | 수치 연산 및 행렬 처리 |
| **scikit-learn** | 머신러닝 모델 로드 및 예측 |
| **joblib** | 학습된 모델 파일(`.joblib`) 로드 |
| **openai** | (구) 여행 일정 생성 기능 등 |

설치 명령어 (한 번에 설치):
```bash
pip install pandas numpy scikit-learn joblib openai
```

## 4. 향후 계획된 요구사항 (Planned Features)

`login_imple.md`에 기술된 로그인 및 친구 관리 기능을 구현하기 위해 다음 서비스/라이브러리가 추가될 예정입니다.

- **Supabase**: 사용자 인증(Auth) 및 데이터베이스 관리
  - Python 라이브러리: `supabase`
  - 설치: `pip install supabase`

## 5. 프로젝트 실행 방법

1. 가상환경 생성 및 활성화 (Anaconda 권장)
   ```bash
   conda create -n Travis_env python=3.9
   conda activate Travis_env
   ```

2. 라이브러리 설치
   ```bash
   pip install flask
   # 필요 시 ML 라이브러리 추가 설치
   # pip install pandas numpy scikit-learn joblib
   ```

3. 서버 실행
   ```bash
   python main.py
   ```
   또는
   ```bash
   flask run
   ```

4. 브라우저 접속
   - 주소: `http://localhost:5000`

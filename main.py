"""
Flask 애플리케이션 메인 진입점 (블루프린트 구조)
"""
from app import app
from blueprints import home_bp, test_bp, result_bp, api_bp, auth_prompt_bp, auth_bp, chemistry_bp

# 블루프린트 등록
app.register_blueprint(home_bp)
app.register_blueprint(test_bp)
app.register_blueprint(result_bp)
app.register_blueprint(api_bp)
app.register_blueprint(auth_prompt_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(chemistry_bp)



if __name__ == '__main__':
    # 자동 재시작(Reloader) 활성화 및 무한 재시작 방지를 위한 예외 폴더 설정
    app.run(debug=True, port=5000, use_reloader=True, exclude_patterns=['Travis_env/*', '.git/*', '__pycache__/*'])

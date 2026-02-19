"""
Flask 애플리케이션 메인 진입점 (블루프린트 구조)
"""
from app import app, init_db
from blueprints import home_bp, test_bp, result_bp, api_bp, auth_prompt_bp

# 블루프린트 등록
app.register_blueprint(home_bp)
app.register_blueprint(test_bp)
app.register_blueprint(result_bp)
app.register_blueprint(api_bp)
app.register_blueprint(auth_prompt_bp)

# DB 초기화
init_db()

if __name__ == '__main__':
    # OneDrive 내 가상환경(Travis_env) 감지로 인한 무한 재시작 방지
    app.run(debug=True, port=5000, use_reloader=False)

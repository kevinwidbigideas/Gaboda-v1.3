"""
Blueprints 패키지
"""
from blueprints.home import home_bp
from blueprints.test import test_bp
from blueprints.result import result_bp
from blueprints.api import api_bp
from blueprints.auth_prompt import auth_prompt_bp

__all__ = ['home_bp', 'test_bp', 'result_bp', 'api_bp', 'auth_prompt_bp']

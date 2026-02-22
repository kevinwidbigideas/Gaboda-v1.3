"""
홈페이지 라우트
"""
from flask import Blueprint, render_template, url_for
from utils import COMMON_HEAD, get_header

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def index():
    """메인 랜딩 페이지"""
    return render_template('index.html', 
                         common_head=COMMON_HEAD, 
                         header=get_header('home'))

from flask import Blueprint, render_template, session, redirect, url_for
import os
from utils import COMMON_HEAD, get_header


auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
@auth_bp.route('/signup')
def login_page():
    """로그인 및 회원가입 페이지"""
    if session.get('user_id'):
        return redirect('/')
    return render_template('login.html', 
                         common_head=COMMON_HEAD, 
                         header=get_header('login'),
                         supabase_url=os.environ.get('SUPABASE_URL'),
                         supabase_key=os.environ.get('SUPABASE_KEY'))

@auth_bp.route('/my-travti')
def my_travti():
    """마이페이지: TraVTI 결과 및 여행 계획"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login_page'))
    
    user_name = session.get('user_name', '여행자')
    travti_label = None
    mbti_type = None
    scores = {'ei': 0, 'sn': 0, 'tf': 0, 'jp': 0}
    my_plans = []
    travti_icon = None

    try:
        from flask import current_app
        import os
        from supabase import create_client
        
        supabase = getattr(current_app, 'supabase', None)
        db_client = supabase
        
        if supabase:
            access_token = session.get('access_token')
            refresh_token = session.get('refresh_token') or ""
            if access_token:
                try:
                    db_client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
                    db_client.auth.set_session(access_token, refresh_token)
                except Exception as se:
                    print(f"Set session warn in my_travti: {se}")

            # 1. Fetch User Profile & Scores (travis_user_data)
            try:
                # Assuming Supabase returns columns in lowercase or as defined. 
                # Attempting to fetch both casing styles just in case, or relying on lowercase which is standard Postgres storage
                res = db_client.table('travis_user_data').select('*').eq('id', user_id).execute()
                
                if res.data:
                    profile = res.data[0]
                    # Map fields - trying case-insensitive get if possible, but dict is case sensitive.
                    # Commonly Supabase returns lowercase keys unless quoted in creation.
                    user_name = profile.get('name') or profile.get('Name') or user_name
                    travti_label = profile.get('travti_label') or profile.get('TraVTI_Label')
                    
                    mbti_type = profile.get('mbti')
                    vector_score = profile.get('vector_score') or {}
                    
                    # Store scores
                    scores['ei'] = float(vector_score.get('ei') or 0)
                    scores['sn'] = float(vector_score.get('sn') or 0)
                    scores['tf'] = float(vector_score.get('tf') or 0)
                    scores['jp'] = float(vector_score.get('jp') or 0)

                    # Derive MBTI if not found
                    if not mbti_type:
                        mbti_e = "E" if scores['ei'] > 0 else "I"
                        mbti_s = "S" if scores['sn'] > 0 else "N"
                        mbti_t = "T" if scores['tf'] > 0 else "F"
                        mbti_j = "J" if scores['jp'] > 0 else "P"
                        mbti_type = f"{mbti_e}{mbti_s}{mbti_t}{mbti_j}"
                    
            except Exception as e:
                print(f"Supabase Profile Fetch Error: {e}")

            # (tb_occasion_info feature removed)
        else:
             print("Supabase client not initialized")

    except Exception as e:
        print(f"My Page Error: {e}")
        
    travti_icons = {
        "팀 조율자": "groups", "영감 수집가": "palette", "경로 대장": "route", "발굴 요원": "explore",
        "친절 가이드": "handshake", "분위기 메이커": "celebration", "계획 관리자": "checklist", "액티브 탐험가": "hiking",
        "사색 유랑자": "spa", "낭만 여행가": "favorite", "테마 기획자": "lightbulb", "효율 전문가": "trending_up",
        "안전 파수꾼": "verified_user", "감성 휴양가": "nights_stay", "꼼꼼한 기록자": "photo_camera", "현장 해결사": "build"
    }
    if travti_label:
        travti_icon = travti_icons.get(travti_label, "emoji_people")

    # Determine Passport Type from Auth Provider
    user_provider = session.get('user_provider', 'email')
    passport_type = 'PM'
    if 'google' in str(user_provider).lower():
        passport_type = 'PG'
    elif 'kakao' in str(user_provider).lower():
        passport_type = 'PK'

    # Current Date for Issued logic
    from datetime import datetime
    today = datetime.now()
    issue_date = today.strftime("%d %b %Y").upper()
    
    # +10 years for Expiry Date
    expiry_date = today.replace(year=today.year + 10).strftime("%d %b %Y").upper() 
    
    # Date string for MRZ info (YYMMDD)
    mrz_date = today.strftime("%y%m%d")

    return render_template('my_travti.html',
                         common_head=COMMON_HEAD,
                         header=get_header('mypage'),
                         user_name=user_name,
                         passport_type=passport_type,
                         travti_label=travti_label,
                         mbti_type=mbti_type,
                         scores=scores,
                         issue_date=issue_date,
                         expiry_date=expiry_date,
                         mrz_date=mrz_date,
                         my_plans=my_plans,
                         travti_icon=travti_icon)

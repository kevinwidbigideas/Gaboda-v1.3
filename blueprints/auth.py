from flask import Blueprint, render_template, session, redirect, url_for, request, current_app
import os
from utils import COMMON_HEAD, get_header
from reports.content_data import get_analysis_data


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
            # Always fetch fresh data from DB to reflect accurate vector_score
            access_token = session.get('access_token')
            refresh_token = session.get('refresh_token') or ""
            try:
                # Try with user's auth token first (respects RLS)
                db_client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
                if access_token:
                    db_client.auth.set_session(access_token, refresh_token)
                
                res = db_client.table('travis_user_data').select('*').eq('id', user_id).execute()
                print(f"[DEBUG] Query result from DB: {res.data}")
                
                if res.data:
                    profile = res.data[0]
                    user_name = profile.get('name') or user_name
                    travti_label = profile.get('travti_label')
                    mbti_type = profile.get('mbti')
                    vector_score = profile.get('vector_score') or {}
                    
                    survey_res = db_client.table('survey_response').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(1).execute()
                    if survey_res.data and 'responses' in survey_res.data[0]:
                        responses = survey_res.data[0]['responses']
                        raw_ei, raw_sn, raw_tf, raw_jp = 0.0, 0.0, 0.0, 0.0
                        stamina_score = 0.5
                        alcohol_score = 0.5
                        
                        for q_idx_str, idx in responses.items():
                            q_num = int(q_idx_str) + 1
                            val_plus, val_minus = 1.0, -1.0
                            if q_num in [1, 2, 3]: raw_jp += (val_plus if idx == 0 else val_minus)
                            elif q_num in [5, 8, 12]: raw_ei += (val_plus if idx == 0 else val_minus)
                            elif q_num == 6:
                                stamina_map = [0.25, 0.5, 0.75, 1.0]
                                stamina_score = stamina_map[idx] if 0 <= idx < len(stamina_map) else 0.25
                            elif q_num in [7, 9, 18]: raw_sn += (val_plus if idx == 0 else val_minus)
                            elif q_num == 10: raw_sn += (1.5 if idx == 0 else -1.5)
                            elif q_num in [11, 15, 17]: raw_tf += (val_plus if idx == 0 else val_minus)
                            elif q_num == 13:
                                alc_map = [0.9, 0.5, 0.1]
                                alcohol_score = alc_map[idx] if 0 <= idx < len(alc_map) else 0.5
                            elif q_num == 14: raw_jp += (1.5 if idx == 0 else -1.5)
                            elif q_num == 16: raw_tf += (1.5 if idx == 0 else -1.5)
                            elif q_num == 19: raw_ei += (1.5 if idx == 0 else -1.5)
                            
                        scores['ei'] = max(-1.0, min(1.0, raw_ei / 4.5))
                        scores['sn'] = max(-1.0, min(1.0, raw_sn / 4.5))
                        scores['tf'] = max(-1.0, min(1.0, raw_tf / 4.5))
                        scores['jp'] = max(-1.0, min(1.0, raw_jp / 4.5))
                        scores['stamina'] = vector_score.get('manual_stamina', stamina_score)
                        scores['alcohol'] = vector_score.get('manual_alcohol', alcohol_score)
                        scores['food_restrictions'] = vector_score.get('food_restrictions', '')
                    else:
                        scores['ei'] = float(vector_score.get('ei') or 0)
                        scores['sn'] = float(vector_score.get('sn') or 0)
                        scores['tf'] = float(vector_score.get('tf') or 0)
                        scores['jp'] = float(vector_score.get('jp') or 0)
                        scores['stamina'] = float(vector_score.get('manual_stamina', vector_score.get('stamina') or 0.5))
                        scores['alcohol'] = float(vector_score.get('manual_alcohol', vector_score.get('alcohol') or 0.5))
                        scores['food_restrictions'] = vector_score.get('food_restrictions', '')
                    
                    # Derive MBTI if not found
                    if not mbti_type:
                        mbti_e = "E" if scores['ei'] > 0 else "I"
                        mbti_s = "S" if scores['sn'] > 0 else "N"
                        mbti_t = "T" if scores['tf'] > 0 else "F"
                        mbti_j = "J" if scores['jp'] > 0 else "P"
                        mbti_type = f"{mbti_e}{mbti_s}{mbti_t}{mbti_j}"
                else:
                    print(f"[DEBUG] No profile data found in DB for user {user_id}")
            except Exception as db_e:
                import traceback
                print(f"[DEBUG] DB fetch failed: {db_e}")
                traceback.print_exc()

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

    
    analysis_data = get_analysis_data(scores, user_name=user_name)

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
                         travti_icon=travti_icon,
                         analysis_data=analysis_data)


@auth_bp.route('/my-info-edit', methods=['GET', 'POST'])
def my_info_edit():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login_page'))

    current_name = session.get('user_name', '여행자')
    current_mbti = session.get('user_mbti')
    current_travti = session.get('user_travti_label')

    if request.method == 'POST':
        new_name = (request.form.get('user_name') or '').strip()
        if new_name:
            session['user_name'] = new_name
            current_name = new_name

            try:
                supabase = getattr(current_app, 'supabase', None)
                if supabase:
                    supabase.table('travis_user_data').update({'name': new_name}).eq('id', user_id).execute()
            except Exception as e:
                print(f"my_info_edit update warn: {e}")

        return redirect(url_for('auth.my_info_edit', saved='1'))

    saved = request.args.get('saved') == '1'
    return render_template(
        'my_info_edit.html',
        common_head=COMMON_HEAD,
        header=get_header('mypage'),
        user_name=current_name,
        mbti_type=current_mbti,
        travti_label=current_travti,
        saved=saved,
    )

from flask import Blueprint, render_template, request, session, current_app, redirect, url_for
from utils import COMMON_HEAD, get_header

chemistry_bp = Blueprint('chemistry', __name__)

@chemistry_bp.route('/chemistry')
def chemistry_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login_page'))
    
    # Check current user's info
    user_name = session.get('user_name', '여행자')
    travti_label = session.get('user_travti_label')
    mbti_type = session.get('user_mbti')
    vector_score = session.get('user_travti_vector')
    
    if not travti_label or not vector_score:
        # Check DB again just in case session is stale
        try:
            supabase = getattr(current_app, 'supabase', None)
            if supabase:
                res = supabase.table('travis_user_data').select('travti_label, mbti, vector_score').eq('id', user_id).execute()
                if res.data:
                    travti_label = res.data[0].get('travti_label')
                    mbti_type = res.data[0].get('mbti')
                    vector_score = res.data[0].get('vector_score')
                    session['user_travti_label'] = travti_label
                    session['user_mbti'] = mbti_type
                    session['user_travti_vector'] = vector_score
        except Exception as e:
            print(f"Chemistry DB fetch error: {e}")
            
    if not travti_label:
        # Still no label -> needs to take the test
        return redirect(url_for('test.test'))

    # If clicked from shared link, we auto-load the friend
    friend_id_from_query = request.args.get('friend', '')

    import json
    # Use fallback if vector_score is somewhat missing
    safe_vector_score = json.dumps(vector_score or {})

    return render_template('chemistry.html', 
                           common_head=COMMON_HEAD,
                           header=get_header('result'),
                           my_id=user_id,
                           my_name=user_name,
                           my_label=travti_label,
                           my_mbti=mbti_type,
                           my_vector_score=safe_vector_score,
                           friend_id_query=friend_id_from_query)

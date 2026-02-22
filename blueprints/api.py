"""
API 라우트 블루프린트
"""
from flask import Blueprint, request, jsonify, session, current_app


api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/get_member_stats')
def get_member_stats():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'missing_user_id'}), 400
    try:
        supabase = getattr(current_app, 'supabase', None)
        if not supabase:
            return jsonify({'error': 'supabase_not_configured'}), 500

        res = supabase.table('travis_user_data').select('id, name, vector_score').eq('id', user_id).execute()
        if not res.data:
            return jsonify({'error': 'not_found'}), 404
        
        row = res.data[0]
        vector_score = row.get('vector_score') or {}
        
        return jsonify({
            'id': row.get('id'),
            'name': row.get('name'),
            'Score_EI': vector_score.get('ei'),
            'Score_SN': vector_score.get('sn'),
            'Score_TF': vector_score.get('tf'),
            'Score_JP': vector_score.get('jp'),
            'Stamina': vector_score.get('stamina'),
            'Alcohol': vector_score.get('alcohol'),
        })
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500



@api_bp.route('/login', methods=['POST'])
def login():
    """Supabase Auth Login & Sync"""
    supabase = getattr(current_app, 'supabase', None)
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    data = request.json
    access_token = data.get('access_token')
    if not access_token:
        return jsonify({'error': 'Missing access token'}), 400

    try:
        user_res = supabase.auth.get_user(access_token)
        user = user_res.user
        if not user:
            return jsonify({'error': 'Invalid token'}), 401

        # Session Setup
        session['user_id'] = user.id
        session['email'] = user.email
        session['access_token'] = access_token
        session['refresh_token'] = data.get('refresh_token') or ""
        session['user_provider'] = (user.app_metadata or {}).get('provider', 'email')
        
        # User Metadata
        user_meta = user.user_metadata or {}
        name = user_meta.get('name') or user_meta.get('full_name') or user.email.split('@')[0]
        session['user_name'] = name 

        # Sync/Fetch from travis_user_data using user context to satisfy RLS
        try:
            import os
            from supabase import create_client
            # Initialize request-scoped client for user
            user_client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
            refresh_token = data.get('refresh_token') or ""
            try:
                user_client.auth.set_session(access_token, refresh_token)
            except Exception as se:
                print(f"Set session warn: {se}")

            res = user_client.table('travis_user_data').select('*').eq('id', user.id).execute()
            if res.data:
                # User exists, load profile
                profile = res.data[0]
                session['user_mbti'] = profile.get('mbti')
                session['user_travti_label'] = profile.get('travti_label')
                session['user_travti_vector'] = profile.get('vector_score')
            else:
                # Create default
                new_user = {
                    'id': user.id,
                    'name': name,
                    'email': user.email
                }
                user_client.table('travis_user_data').insert(new_user).execute()
        except Exception as db_e:
            import traceback
            traceback.print_exc()
            print(f"DB Sync Error: {db_e}")



        return jsonify({'success': True, 'user_id': user.id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/login_random', methods=['POST'])
def login_random():
    # Deprecated or Dev-only
    try:
        supabase = getattr(current_app, 'supabase', None)
        if not supabase:
            return jsonify({'error': 'no_supabase'}), 500
        res = supabase.table('travis_user_data').select('id, name, travti_label, mbti').eq('id', 'TRV-NEW-1000').execute()
        if not res.data:
            return jsonify({'error': 'no_user'}), 404
        
        row = res.data[0]
        user_id = row.get('id')
        name = row.get('name')
        travti_label = row.get('travti_label')
        travti_vector = row.get('mbti')
        actual_label = None
        
        session['user_id'] = user_id
        session['user_name'] = name
        session['user_actual_label'] = actual_label
        session['user_travti_label'] = travti_label
        session['user_travti_vector'] = travti_vector
        return jsonify({
            'user_id': user_id,
            'name': name,
            'actual_label': actual_label,
            'travti_label': travti_label
        })
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/session_user')
def session_user():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'logged_in': False})
    return jsonify({
        'logged_in': True,
        'user_id': user_id,
        'name': session.get('user_name'),
        'actual_label': session.get('user_actual_label'),
        'travti_label': session.get('user_travti_label')
    })


@api_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@api_bp.route('/check_actual_label')
def check_actual_label():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error':'missing_user_id'}), 400
    try:
        supabase = getattr(current_app, 'supabase', None)
        has_actual = False # Not supported in Supabase schema right now
        has_travti = False
        if supabase:
            res = supabase.table('travis_user_data').select('travti_label').eq('id', user_id).execute()
            if res.data and res.data[0].get('travti_label'):
                has_travti = True
        return jsonify({'has_actual_label': has_actual, 'has_travti_label': has_travti})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/get_travti_label')
def get_travti_label():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error':'missing_user_id'}), 400
    try:
        supabase = getattr(current_app, 'supabase', None)
        travti = None
        if supabase:
            res = supabase.table('travis_user_data').select('travti_label').eq('id', user_id).execute()
            if res.data:
                travti = res.data[0].get('travti_label')
        return jsonify({'travti_label': travti})
    except Exception as e:
        return jsonify({'error':'db_error','message': str(e)}), 500


@api_bp.route('/get_travti_answers')
def get_travti_answers():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'missing_user_id'}), 400
    try:
        supabase = getattr(current_app, 'supabase', None)
        answers = None
        if supabase:
            res = supabase.table('survey_response').select('responses').eq('user_id', user_id).order('created_at', desc=True).limit(1).execute()
            if res.data and res.data[0].get('responses'):
                resp_json = res.data[0].get('responses')
                answers = {f"Q{i+1}": (resp_json.get(str(i)) if str(i) in resp_json else '') for i in range(20)}
        return jsonify({'answers': answers})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500




@api_bp.route('/get_friend_name')
def get_friend_name():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'missing_user_id'}), 400
    try:
        supabase = getattr(current_app, 'supabase', None)
        name = None
        if supabase:
            res = supabase.table('travis_user_data').select('name').eq('id', user_id).execute()
            if res.data:
                name = res.data[0].get('name')
        return jsonify({'name': name})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/get_user_identity')
def get_user_identity():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'missing_user_id'}), 400
    try:
        supabase = getattr(current_app, 'supabase', None)
        name = None
        mbti = None
        travti_label = None
        vector_score = None
        if supabase:
            res = supabase.table('travis_user_data').select('name, mbti, travti_label, vector_score').eq('id', user_id).execute()
            if res.data:
                name = res.data[0].get('name')
                mbti = res.data[0].get('mbti')
                travti_label = res.data[0].get('travti_label')
                vector_score = res.data[0].get('vector_score')
        return jsonify({'name': name, 'mbti': mbti, 'travti_label': travti_label, 'vector_score': vector_score})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/search_user')
def search_user():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'results': []})
    
    try:
        supabase = getattr(current_app, 'supabase', None)
        if not supabase:
            return jsonify({'error': 'db_error', 'message': 'Supabase not initialized'}), 500
        
        # Searching by name or email
        # using ilike for case-insensitive partial match
        res = supabase.table('travis_user_data').select('id, name, email, travti_label, mbti, vector_score').or_(f"name.ilike.%{query}%,email.ilike.%{query}%").limit(10).execute()
        
        results = []
        if res.data:
            for row in res.data:
                results.append({
                    'id': row.get('id'),
                    'name': row.get('name') or '여행자',
                    'email': row.get('email'),
                    'travti_label': row.get('travti_label'),
                    'mbti': row.get('mbti'),
                    'vector_score': row.get('vector_score')
                })
        return jsonify({'results': results})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'db_error', 'message': str(e)}), 500

"""
API 라우트 블루프린트
"""
from flask import Blueprint, request, jsonify, session, current_app
import os
from datetime import datetime, timezone
from supabase import create_client


api_bp = Blueprint('api', __name__, url_prefix='/api')


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _get_user_client_or_error():
    user_id = session.get('user_id')
    access_token = session.get('access_token')
    refresh_token = session.get('refresh_token') or ''
    if not user_id or not access_token:
        return None, None, (jsonify({'error': 'unauthorized'}), 401)

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        return None, None, (jsonify({'error': 'supabase_not_configured'}), 500)

    try:
        user_client = create_client(supabase_url, supabase_key)
        user_client.auth.set_session(access_token, refresh_token)
        return user_client, user_id, None
    except Exception as e:
        return None, None, (jsonify({'error': 'auth_session_error', 'message': str(e)}), 401)


def _fetch_profiles(supabase_client, user_ids):
    if not user_ids:
        return {}
    ids = list({str(user_id) for user_id in user_ids if user_id})
    if not ids:
        return {}
    res = supabase_client.table('travis_user_data').select('id, name, email, travti_label, mbti, vector_score').in_('id', ids).execute()
    rows = res.data or []
    return {str(row.get('id')): row for row in rows}

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
        session['email'] = user.email  # Can be None for Kakao
        session['access_token'] = access_token
        session['refresh_token'] = data.get('refresh_token') or ""
        session['user_provider'] = (user.app_metadata or {}).get('provider', 'email')
        
        # User Metadata - Handle Kakao (no email) case
        user_meta = user.user_metadata or {}
        # Kakao: profile_nickname, Google/Email: name, full_name, email
        name = (user_meta.get('name') or 
                user_meta.get('full_name') or 
                user_meta.get('profile_nickname') or 
                (user.email.split('@')[0] if user.email else None) or
                f"User_{user.id[:8]}")
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
                # Create default - email can be None for Kakao
                new_user = {
                    'id': user.id,
                    'name': name,
                    'email': user.email  # None is OK, column is nullable
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
        'travti_label': session.get('user_travti_label'),
        'mbti': session.get('user_mbti')
    })


@api_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@api_bp.route('/profile/update', methods=['POST'])
def profile_update():
    user_client, me, err = _get_user_client_or_error()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    manual_stamina = body.get('stamina')
    manual_alcohol = body.get('alcohol')
    food_restrictions = body.get('food_restrictions')

    try:
        # Fetch current vector_score
        res = user_client.table('travis_user_data').select('vector_score').eq('id', me).execute()
        if not res.data:
            return jsonify({'error': 'user_not_found'}), 404
        
        vector_score = res.data[0].get('vector_score') or {}
        
        # Update specific fields
        if manual_stamina is not None:
            vector_score['manual_stamina'] = float(manual_stamina)
        if manual_alcohol is not None:
            vector_score['manual_alcohol'] = float(manual_alcohol)
        if food_restrictions is not None:
            vector_score['food_restrictions'] = str(food_restrictions).strip()

        # Save back to db
        update_res = user_client.table('travis_user_data').update({'vector_score': vector_score}).eq('id', me).execute()
        if not update_res.data:
            return jsonify({'error': 'update_failed'}), 500

        return jsonify({'success': True, 'vector_score': vector_score})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


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


@api_bp.route('/friends/request', methods=['POST'])
def friend_request():
    user_client, me, err = _get_user_client_or_error()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    target_user_id = str(body.get('target_user_id', '')).strip()
    if not target_user_id:
        return jsonify({'error': 'missing_target_user_id'}), 400
    if target_user_id == me:
        return jsonify({'error': 'cannot_add_self'}), 400

    try:
        relation_res = user_client.table('friend_relations').select('*').or_(
            f"and(requester_id.eq.{me},addressee_id.eq.{target_user_id}),and(requester_id.eq.{target_user_id},addressee_id.eq.{me})"
        ).limit(1).execute()
        existing = (relation_res.data or [])

        if existing:
            row = existing[0]
            status = row.get('status')
            requester_id = row.get('requester_id')
            addressee_id = row.get('addressee_id')

            if status == 'accepted':
                return jsonify({'success': True, 'status': 'already_friends', 'message': '이미 친구입니다.', 'relation': row})
            if status == 'pending':
                if requester_id == me and addressee_id == target_user_id:
                    return jsonify({'success': True, 'status': 'already_requested', 'message': '이미 친구 요청을 보냈습니다.', 'relation': row})
                return jsonify({'success': False, 'status': 'incoming_request_exists', 'message': '상대방이 이미 친구 요청을 보냈습니다.', 'relation': row}), 409

            return jsonify({'success': False, 'status': 'relation_exists', 'message': '이미 관계가 존재합니다.', 'relation': row}), 409

        insert_payload = {
            'requester_id': me,
            'addressee_id': target_user_id,
            'status': 'pending'
        }
        inserted = user_client.table('friend_relations').insert(insert_payload).execute()
        row = (inserted.data or [{}])[0]
        return jsonify({'success': True, 'status': 'pending', 'relation': row})
    except Exception as e:
        error_str = str(e).lower()
        # PostgreSQL duplicate key error handling
        if 'duplicate' in error_str or 'unique' in error_str or '23505' in error_str:
            return jsonify({'error': 'already_requested', 'message': '이미 친구 요청을 보냈거나 관계가 존재합니다.'}), 409
        return jsonify({'error': 'db_error', 'message': '요청 처리 중 오류가 발생했습니다.'}), 500


@api_bp.route('/friends/respond', methods=['POST'])
def friend_respond():
    user_client, me, err = _get_user_client_or_error()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    requester_id = str(body.get('requester_id', '')).strip()
    action = str(body.get('action', '')).strip().lower()

    if not requester_id:
        return jsonify({'error': 'missing_requester_id'}), 400
    if action not in ('accept', 'reject'):
        return jsonify({'error': 'invalid_action'}), 400

    next_status = 'accepted' if action == 'accept' else 'rejected'
    payload = {
        'status': next_status,
        'responded_at': _utc_now_iso()
    }

    try:
        updated = user_client.table('friend_relations').update(payload).eq('requester_id', requester_id).eq('addressee_id', me).eq('status', 'pending').execute()
        rows = updated.data or []
        if not rows:
            return jsonify({'error': 'request_not_found'}), 404
        return jsonify({'success': True, 'status': next_status, 'relation': rows[0]})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/friends/list')
def friend_list():
    user_client, me, err = _get_user_client_or_error()
    if err:
        return err

    try:
        rel_res = user_client.table('friend_relations').select('id, requester_id, addressee_id, status, created_at, responded_at').eq('status', 'accepted').or_(
            f"requester_id.eq.{me},addressee_id.eq.{me}"
        ).execute()
        relations = rel_res.data or []
        friend_ids = []
        for row in relations:
            requester_id = str(row.get('requester_id', ''))
            addressee_id = str(row.get('addressee_id', ''))
            friend_ids.append(addressee_id if requester_id == me else requester_id)

        profiles = _fetch_profiles(user_client, friend_ids)
        result = []
        for row in relations:
            requester_id = str(row.get('requester_id', ''))
            addressee_id = str(row.get('addressee_id', ''))
            friend_id = addressee_id if requester_id == me else requester_id
            profile = profiles.get(friend_id, {})
            result.append({
                'relation_id': row.get('id'),
                'friend_id': friend_id,
                'name': profile.get('name') or '여행자',
                'email': profile.get('email'),
                'travti_label': profile.get('travti_label'),
                'mbti': profile.get('mbti'),
                'vector_score': profile.get('vector_score'),
                'created_at': row.get('created_at'),
                'responded_at': row.get('responded_at')
            })

        return jsonify({'friends': result})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/friends/requests')
def friend_requests():
    user_client, me, err = _get_user_client_or_error()
    if err:
        return err

    try:
        incoming_res = user_client.table('friend_relations').select('id, requester_id, created_at').eq('addressee_id', me).eq('status', 'pending').order('created_at', desc=True).execute()
        outgoing_res = user_client.table('friend_relations').select('id, addressee_id, created_at').eq('requester_id', me).eq('status', 'pending').order('created_at', desc=True).execute()

        incoming = incoming_res.data or []
        outgoing = outgoing_res.data or []

        incoming_ids = [row.get('requester_id') for row in incoming]
        outgoing_ids = [row.get('addressee_id') for row in outgoing]
        profiles = _fetch_profiles(user_client, incoming_ids + outgoing_ids)

        incoming_result = []
        for row in incoming:
            requester_id = str(row.get('requester_id', ''))
            profile = profiles.get(requester_id, {})
            incoming_result.append({
                'relation_id': row.get('id'),
                'requester_id': requester_id,
                'name': profile.get('name') or '여행자',
                'email': profile.get('email'),
                'travti_label': profile.get('travti_label'),
                'created_at': row.get('created_at')
            })

        outgoing_result = []
        for row in outgoing:
            addressee_id = str(row.get('addressee_id', ''))
            profile = profiles.get(addressee_id, {})
            outgoing_result.append({
                'relation_id': row.get('id'),
                'addressee_id': addressee_id,
                'name': profile.get('name') or '여행자',
                'email': profile.get('email'),
                'travti_label': profile.get('travti_label'),
                'created_at': row.get('created_at')
            })

        return jsonify({'incoming': incoming_result, 'outgoing': outgoing_result})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/friends/delete', methods=['POST'])
def friend_delete():
    user_client, me, err = _get_user_client_or_error()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    friend_id = str(body.get('friend_id', '')).strip()
    if not friend_id:
        return jsonify({'error': 'missing_friend_id'}), 400
    if friend_id == me:
        return jsonify({'error': 'invalid_friend_id'}), 400

    try:
        relation_res = user_client.table('friend_relations').select('id').eq('status', 'accepted').or_(
            f"and(requester_id.eq.{me},addressee_id.eq.{friend_id}),and(requester_id.eq.{friend_id},addressee_id.eq.{me})"
        ).limit(1).execute()
        rows = relation_res.data or []
        if not rows:
            return jsonify({'error': 'friend_relation_not_found'}), 404

        relation_id = rows[0].get('id')
        deleted = user_client.table('friend_relations').delete().eq('id', relation_id).execute()
        deleted_rows = deleted.data or []
        if not deleted_rows:
            return jsonify({'error': 'friend_relation_not_found'}), 404

        return jsonify({'success': True, 'deleted_relation_id': relation_id})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/groups/create', methods=['POST'])
def create_group():
    user_client, me, err = _get_user_client_or_error()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    group_name = str(body.get('group_name', '')).strip()
    description = str(body.get('description', '')).strip() or None
    member_ids = body.get('member_ids') or []
    if isinstance(member_ids, str):
        member_ids = [member_ids]

    if not group_name:
        return jsonify({'error': 'missing_group_name'}), 400

    try:
        group_payload = {
            'owner_id': me,
            'group_name': group_name,
            'description': description
        }
        group_res = user_client.table('travel_groups').insert(group_payload).execute()
        group = (group_res.data or [{}])[0]
        group_id = group.get('id')
        if not group_id:
            return jsonify({'error': 'group_create_failed'}), 500

        owner_member = {
            'group_id': group_id,
            'user_id': me,
            'role': 'owner',
            'invite_status': 'joined',
            'invited_by': me,
            'joined_at': _utc_now_iso()
        }
        user_client.table('group_members').insert(owner_member).execute()

        clean_member_ids = []
        for member_id in member_ids:
            member_id_str = str(member_id).strip()
            if member_id_str and member_id_str != me:
                clean_member_ids.append(member_id_str)
        clean_member_ids = list(dict.fromkeys(clean_member_ids))

        inserted_ids = []
        if clean_member_ids:
            invite_rows = []
            for member_id in clean_member_ids:
                invite_rows.append({
                    'group_id': group_id,
                    'user_id': member_id,
                    'role': 'member',
                    'invite_status': 'invited',
                    'invited_by': me
                })
            try:
                ins_res = user_client.table('group_members').insert(invite_rows).execute()
                inserted_ids = [str(row.get('user_id')) for row in (ins_res.data or []) if row.get('user_id')]
            except Exception:
                pass

        return jsonify({
            'success': True,
            'group': group,
            'invited_member_ids': inserted_ids
        })
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/groups/delete', methods=['POST'])
def delete_group():
    user_client, me, err = _get_user_client_or_error()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    group_id = str(body.get('group_id', '')).strip()

    if not group_id:
        return jsonify({'error': 'missing_group_id'}), 400

    try:
        # Check if user is owner
        group_res = user_client.table('travel_groups').select('owner_id').eq('id', group_id).execute()
        rows = group_res.data or []
        if not rows:
            return jsonify({'error': 'group_not_found'}), 404
        
        owner_id = str(rows[0].get('owner_id'))
        
        if owner_id == me:
            # User is owner, delete entire group
            user_client.table('travel_groups').delete().eq('id', group_id).execute()
            return jsonify({'success': True, 'action': 'deleted'})
        else:
            # User is not owner, just leave the group
            user_client.table('group_members').delete().eq('group_id', group_id).eq('user_id', me).execute()
            return jsonify({'success': True, 'action': 'left'})

    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/groups/list')
def group_list():
    user_client, me, err = _get_user_client_or_error()
    if err:
        return err

    try:
        member_rows = user_client.table('group_members').select('group_id, role, invite_status, joined_at').eq('user_id', me).order('created_at', desc=True).execute().data or []
        if not member_rows:
            return jsonify({'groups': []})

        group_ids = list({row.get('group_id') for row in member_rows if row.get('group_id')})
        groups_res = user_client.table('travel_groups').select('id, owner_id, group_name, description, created_at, updated_at').in_('id', group_ids).order('created_at', desc=True).execute()
        groups = groups_res.data or []
        member_map = {str(row.get('group_id')): row for row in member_rows}

        results = []
        for group in groups:
            group_id = str(group.get('id'))
            member_info = member_map.get(group_id, {})
            results.append({
                'id': group_id,
                'group_name': group.get('group_name'),
                'description': group.get('description'),
                'owner_id': group.get('owner_id'),
                'created_at': group.get('created_at'),
                'my_role': member_info.get('role'),
                'my_invite_status': member_info.get('invite_status'),
                'joined_at': member_info.get('joined_at')
            })

        return jsonify({'groups': results})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/groups/members')
def group_members_list():
    user_client, me, err = _get_user_client_or_error()
    if err:
        return err

    group_id = request.args.get('group_id')
    if not group_id:
        return jsonify({'error': 'missing_group_id'}), 400

    try:
        member_rows = user_client.table('group_members').select('user_id, role, invite_status').eq('group_id', group_id).execute().data or []
        if not member_rows:
            return jsonify({'members': []})

        user_ids = [str(row.get('user_id')) for row in member_rows if row.get('user_id')]
        
        # We need _fetch_profiles logic but we can query travis_user_data directly
        profiles_res = user_client.table('travis_user_data').select('id, name, email, travti_label, mbti, vector_score').in_('id', user_ids).execute()
        profiles = {str(p.get('id')): p for p in (profiles_res.data or [])}

        results = []
        for row in member_rows:
            uid = str(row.get('user_id'))
            prof = profiles.get(uid, {})
            results.append({
                'id': uid,
                'role': row.get('role'),
                'invite_status': row.get('invite_status'),
                'name': prof.get('name', '여행자'),
                'email': prof.get('email', ''),
                'travti_label': prof.get('travti_label'),
                'mbti': prof.get('mbti'),
                'vector_score': prof.get('vector_score') or {}
            })

        return jsonify({'members': results})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/groups/invite', methods=['POST'])
def group_invite():
    user_client, me, err = _get_user_client_or_error()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    group_id = str(body.get('group_id', '')).strip()
    user_ids = body.get('user_ids') or []
    if isinstance(user_ids, str):
        user_ids = [user_ids]

    if not group_id:
        return jsonify({'error': 'missing_group_id'}), 400

    targets = []
    for user_id in user_ids:
        user_id_str = str(user_id).strip()
        if user_id_str and user_id_str != me:
            targets.append(user_id_str)
    targets = list(dict.fromkeys(targets))
    if not targets:
        return jsonify({'error': 'missing_user_ids'}), 400

    try:
        group_res = user_client.table('travel_groups').select('id, owner_id').eq('id', group_id).limit(1).execute()
        rows = group_res.data or []
        if not rows:
            return jsonify({'error': 'group_not_found'}), 404
        if str(rows[0].get('owner_id')) != me:
            return jsonify({'error': 'forbidden'}), 403

        existing_res = user_client.table('group_members').select('user_id').eq('group_id', group_id).in_('user_id', targets).execute()
        existing_ids = {str(row.get('user_id')) for row in (existing_res.data or []) if row.get('user_id')}
        invite_targets = [user_id for user_id in targets if user_id not in existing_ids]

        inserted_ids = []
        if invite_targets:
            payload = [{
                'group_id': group_id,
                'user_id': user_id,
                'role': 'member',
                'invite_status': 'invited',
                'invited_by': me
            } for user_id in invite_targets]
            ins = user_client.table('group_members').insert(payload).execute()
            inserted_ids = [str(row.get('user_id')) for row in (ins.data or []) if row.get('user_id')]

        return jsonify({'success': True, 'inserted_user_ids': inserted_ids, 'skipped_user_ids': list(existing_ids)})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/groups/invites')
def group_invites():
    user_client, me, err = _get_user_client_or_error()
    if err:
        return err

    try:
        invite_rows = user_client.table('group_members').select('group_id, invited_by, created_at').eq('user_id', me).eq('invite_status', 'invited').order('created_at', desc=True).execute().data or []
        if not invite_rows:
            return jsonify({'invites': []})

        group_ids = list({row.get('group_id') for row in invite_rows if row.get('group_id')})
        groups = user_client.table('travel_groups').select('id, owner_id, group_name, description, created_at').in_('id', group_ids).execute().data or []
        group_map = {str(group.get('id')): group for group in groups}

        results = []
        for row in invite_rows:
            group_id = str(row.get('group_id'))
            group = group_map.get(group_id, {})
            results.append({
                'group_id': group_id,
                'group_name': group.get('group_name'),
                'description': group.get('description'),
                'owner_id': group.get('owner_id'),
                'invited_by': row.get('invited_by'),
                'invited_at': row.get('created_at')
            })
        return jsonify({'invites': results})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/groups/invite/respond', methods=['POST'])
def group_invite_respond():
    user_client, me, err = _get_user_client_or_error()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    group_id = str(body.get('group_id', '')).strip()
    action = str(body.get('action', '')).strip().lower()
    if not group_id:
        return jsonify({'error': 'missing_group_id'}), 400
    if action not in ('accept', 'decline'):
        return jsonify({'error': 'invalid_action'}), 400

    next_status = 'joined' if action == 'accept' else 'declined'
    payload = {'invite_status': next_status}
    if next_status == 'joined':
        payload['joined_at'] = _utc_now_iso()

    try:
        updated = user_client.table('group_members').update(payload).eq('group_id', group_id).eq('user_id', me).eq('invite_status', 'invited').execute()
        rows = updated.data or []
        if not rows:
            return jsonify({'error': 'invite_not_found'}), 404
        return jsonify({'success': True, 'invite_status': next_status, 'membership': rows[0]})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500

"""
API 라우트 블루프린트
"""
from flask import Blueprint, request, jsonify, session
from app import get_db

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/get_member_stats')
def get_member_stats():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'missing_user_id'}), 400
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            SELECT ID, Name, Score_EI, Score_SN, Score_TF, Score_JP, Stamina, Alcohol
            FROM travis_data
            WHERE ID = ?
        """, (user_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'not_found'}), 404
        return jsonify({
            'id': row[0],
            'name': row[1],
            'Score_EI': row[2],
            'Score_SN': row[3],
            'Score_TF': row[4],
            'Score_JP': row[5],
            'Stamina': row[6],
            'Alcohol': row[7],
        })
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500



@api_bp.route('/login_random', methods=['POST'])
def login_random():
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('SELECT ID, Name, Actual_Label, TraVTI_Label, TraVTI_Vector FROM travis_data WHERE ID = ?', ('TRV-NEW-1000',))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'no_user'}), 404
        user_id, name, actual_label, travti_label, travti_vector = row
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
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_actual_label', None)
    session.pop('user_travti_label', None)
    session.pop('user_travti_vector', None)
    return jsonify({'success': True})

@api_bp.route('/check_actual_label')
def check_actual_label():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error':'missing_user_id'}), 400
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('SELECT Actual_Label, TraVTI_Label FROM survey_responses WHERE ID = ?', (user_id,))
        row = cur.fetchone()
        has_actual = False
        has_travti = False
        if row:
            actual_val = row[0]
            travti_val = row[1] if len(row) > 1 else None
            if actual_val not in (None, '', 'NULL'):
                has_actual = True
            if travti_val not in (None, '', 'NULL'):
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
        db = get_db()
        cur = db.cursor()
        cur.execute('SELECT TraVTI_Label FROM survey_responses WHERE ID = ?', (user_id,))
        row = cur.fetchone()
        travti = row[0] if row and row[0] not in (None, '', 'NULL') else None
        return jsonify({'travti_label': travti})
    except Exception as e:
        return jsonify({'error':'db_error','message': str(e)}), 500


@api_bp.route('/get_travti_answers')
def get_travti_answers():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'missing_user_id'}), 400
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, "
            "q11, q12, q13, q14, q15, q16, q17, q18, q19, q20 "
            "FROM survey_responses WHERE ID = ?",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({'answers': None})
        answers = {f"Q{i+1}": (row[i] if row[i] not in (None, '', 'NULL') else '') for i in range(20)}
        return jsonify({'answers': answers})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500




@api_bp.route('/get_friend_name')
def get_friend_name():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'missing_user_id'}), 400
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('SELECT Name FROM travis_data WHERE ID = ?', (user_id,))
        row = cur.fetchone()
        name = row[0] if row and row[0] not in (None, '', 'NULL') else None
        return jsonify({'name': name})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500


@api_bp.route('/get_user_identity')
def get_user_identity():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'missing_user_id'}), 400
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('SELECT Name, Actual_Label FROM travis_data WHERE ID = ?', (user_id,))
        row = cur.fetchone()
        name = row[0] if row and row[0] not in (None, '', 'NULL') else None
        actual_label = row[1] if row and row[1] not in (None, '', 'NULL') else None
        return jsonify({'name': name, 'actual_label': actual_label})
    except Exception as e:
        return jsonify({'error': 'db_error', 'message': str(e)}), 500



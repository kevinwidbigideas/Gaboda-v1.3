"""
답변 제출 및 결과 라우트 블루프린트
"""
import json
import html
import re
import sqlite3
import time
from flask import Blueprint, request, render_template_string, session, jsonify
from app import get_db
from utils import COMMON_HEAD, get_header, generate_next_id


result_bp = Blueprint('result', __name__)


@result_bp.route('/api/save-occasion', methods=['POST'])
def save_occasion():
    """Save trip occasion info to tb_occasion_info."""
    print("save_occasion called")
    user_id = session.get('user_id')
    if not user_id:
        # Generate guest user ID if not logged in
        import time
        user_id = f"guest_{int(time.time())}"
        session['user_id'] = user_id
        print(f"[save_occasion] No user_id in session, generated guest ID: {user_id}")

    payload = request.get_json() or {}
    trip_hotel_address = payload.get('trip_hotel_address')
    trip_start = payload.get('trip_start')
    trip_end = payload.get('trip_end')
    trip_destination = payload.get('trip_destination')
    trip_member = payload.get('trip_member')
    member_stats = payload.get('member_stats') or {}
    anchor_id = payload.get('anchor_id')
    trip_start_time = payload.get('trip_start_time')
    trip_end_time = payload.get('trip_end_time')

    print(f"save_occasion payload: {payload}")

    name = session.get('user_name') or payload.get('name')
    if trip_destination:
        session['trip_destination'] = trip_destination
    if trip_hotel_address:
        session['trip_hotel_address'] = trip_hotel_address
    if trip_start:
        session['trip_start'] = trip_start
    if trip_end:
        session['trip_end'] = trip_end
    if anchor_id:
        session['trip_anchor'] = anchor_id
    if trip_start_time:
        session['trip_start_time'] = trip_start_time
    if trip_end_time:
        session['trip_end_time'] = trip_end_time
    if isinstance(trip_member, list):
        session['itinerary_member_ids'] = [m.get('user_id') for m in trip_member if m.get('user_id')]
    if isinstance(member_stats, dict):
        session['itinerary_member_stats'] = member_stats

    db = get_db()
    cursor = db.cursor()
    for attempt in range(3):
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tb_occasion_info'")
            table_exists = cursor.fetchone() is not None
            if not table_exists:
                cursor.execute("""
                    CREATE TABLE tb_occasion_info (
                        user_id TEXT PRIMARY KEY,
                        name TEXT,
                        trip_destination TEXT,
                        trip_hotel_address TEXT,
                        trip_start TEXT,
                        trip_end TEXT,
                        trip_member TEXT,
                        updated_at TEXT
                    )
                """)

            cursor.execute("PRAGMA table_info(tb_occasion_info)")
            table_info = cursor.fetchall()
            cols = [row[1] for row in table_info]
            pk_cols = {row[1] for row in table_info if row[5] == 1}

            if 'user_id' not in cols:
                cursor.execute("ALTER TABLE tb_occasion_info ADD COLUMN user_id TEXT")

            # Ensure user_id is not unique to allow accumulation
            cursor.execute("DROP INDEX IF EXISTS idx_tb_occasion_info_user_id")

            # If user_id is primary key, migrate to auto-increment ID table
            if 'user_id' in pk_cols:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tb_occasion_info_new (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        name TEXT,
                        trip_destination TEXT,
                        trip_hotel_address TEXT,
                        trip_start TEXT,
                        trip_end TEXT,
                        trip_member TEXT,
                        updated_at TEXT
                    )
                """)
                cursor.execute("""
                    INSERT INTO tb_occasion_info_new (user_id, name, trip_destination, trip_hotel_address, trip_start, trip_end, trip_member, updated_at)
                    SELECT user_id, name, NULL, trip_hotel_address, trip_start, trip_end, trip_member, updated_at
                    FROM tb_occasion_info
                """)
                cursor.execute("DROP TABLE tb_occasion_info")
                cursor.execute("ALTER TABLE tb_occasion_info_new RENAME TO tb_occasion_info")

            for col in ['name', 'trip_destination', 'trip_hotel_address', 'trip_start', 'trip_end', 'trip_member', 'updated_at']:
                if col not in cols:
                    cursor.execute(f"ALTER TABLE tb_occasion_info ADD COLUMN {col} TEXT")

            members = trip_member if isinstance(trip_member, list) else []
            if not trip_hotel_address or not trip_start or not trip_end:
                return jsonify({'error': 'missing_trip_fields'}), 400
            missing_member_ids = [m for m in members if not m.get('user_id')]
            if missing_member_ids:
                return jsonify({'error': 'missing_member_id'}), 400

            cursor.execute(
                """
                INSERT INTO tb_occasion_info (
                    user_id, name, trip_destination, trip_hotel_address, trip_start, trip_end, trip_member, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (user_id, name, trip_destination, trip_hotel_address, trip_start, trip_end, json.dumps(members, ensure_ascii=False)),
            )
            return jsonify({'success': True})
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower() and attempt < 2:
                time.sleep(0.2 * (attempt + 1))
                continue
            print(f"save_occasion error: {e}")
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            print(f"save_occasion error: {e}")
            return jsonify({'error': str(e)}), 500




@result_bp.route('/submit-answers', methods=['POST'])
def submit_answers():
    """모든 답변 제출 및 TraVTI 결과 계산"""
    try:
        data = request.get_json() or {}
        answers = data.get('answers', [])
        answer_indices = data.get('answer_indices', [])

        session['answers'] = answers
        user_id = session.get('user_id')
        
        if not answers or len(answers) != 19:
            return {'success': False, 'error': f'Invalid answers count: {len(answers)}'}, 400

        # 1. 답변 파싱 및 점수 매핑 (Option Index: 0 or 1 etc.)
        # answers/answer_indices are 0-indexed. Q1 is at index 0.
        
        # Initialize raw trait scores
        raw_ei = 0.0
        raw_sn = 0.0
        raw_tf = 0.0
        raw_jp = 0.0
        
        # Stamina / Alcohol
        stamina_score = 0.0
        alcohol_score = 0.0

        for q_idx in range(19):
            q_num = q_idx + 1
            idx = answer_indices[q_idx] if len(answer_indices) > q_idx and isinstance(answer_indices[q_idx], int) else 0
            
            # Helper for +1 / -1 logic (Option 0 -> +1, Option 1 -> -1 usually)
            # Check travti_scoring.md for specific mapping
            
            val_plus = 1.0
            val_minus = -1.0
            
            # Q1: J/P. 1(+1, J), 2(-1, P) => Opt 0=+1, Opt 1=-1
            if q_num == 1: raw_jp += (val_plus if idx == 0 else val_minus)
            elif q_num == 2: raw_jp += (val_plus if idx == 0 else val_minus)
            elif q_num == 3: raw_jp += (val_plus if idx == 0 else val_minus)
            
            # Q4: Food (Filtering) - No Score
            
            # Q5: E/I. 1(+1, E), 2(-1, I)
            elif q_num == 5: raw_ei += (val_plus if idx == 0 else val_minus)
            
            # Q6: Stamina. 1(0.25), 2(0.5), 3(0.75), 4(1.0)
            elif q_num == 6:
                stamina_map = [0.25, 0.5, 0.75, 1.0]
                stamina_score = stamina_map[idx] if 0 <= idx < len(stamina_map) else 0.25
                
            # Q7: S/N. 1(+1, S), 2(-1, N)
            elif q_num == 7: raw_sn += (val_plus if idx == 0 else val_minus)
            
            # Q8: E/I. 1(+1, E), 2(-1, I)
            elif q_num == 8: raw_ei += (val_plus if idx == 0 else val_minus)
            
            # Q9: S/N. 1(+1, S), 2(-1, N)
            elif q_num == 9: raw_sn += (val_plus if idx == 0 else val_minus)
            
            # Q10: S/N (x1.5). 1(+1.5, S), 2(-1.5, N). 
            elif q_num == 10: raw_sn += (1.5 if idx == 0 else -1.5)
            
            # Q11: T/F. 1(+1, T), 2(-1, F)
            elif q_num == 11: raw_tf += (val_plus if idx == 0 else val_minus)
            
            # Q12: E/I. 1(+1, E), 2(-1, I). (Note: MD says Q12 is E/I)
            elif q_num == 12: raw_ei += (val_plus if idx == 0 else val_minus)
            
            # Q13: Alcohol. 1(0.9), 2(0.5), 3(0.1)
            elif q_num == 13:
                alc_map = [0.9, 0.5, 0.1]
                alcohol_score = alc_map[idx] if 0 <= idx < len(alc_map) else 0.5
                
            # Q14: J/P (x1.5). 1(+1.5, J), 2(-1.5, P)
            elif q_num == 14: raw_jp += (1.5 if idx == 0 else -1.5)
            
            # Q15: T/F. 1(+1, T), 2(-1, F). 
            elif q_num == 15: raw_tf += (val_plus if idx == 0 else val_minus)
            
            # Q16: T/F (x1.5). 1(+1.5, T), 2(-1.5, F)
            elif q_num == 16: raw_tf += (1.5 if idx == 0 else -1.5)
            
            # Q17: T/F. 1(+1, T), 2(-1, F)
            elif q_num == 17: raw_tf += (val_plus if idx == 0 else val_minus)
            
            # Q18: S/N (x1.5). 1(+1.5, S), 2(-1.5, N)
            elif q_num == 18: raw_sn += (1.5 if idx == 0 else -1.5)
            
            # Q19: E/I (x1.5). 1(+1.5, E), 2(-1.5, I)
            elif q_num == 19: raw_ei += (1.5 if idx == 0 else -1.5)


        # 2. 정규화 (Normalization)
        # Raw Sum Range: -4.5 ~ +4.5
        # Target Range: -1.0 ~ +1.0
        # Formula: Score = Raw Sum / 4.5
        
        score_ei = raw_ei / 4.5
        score_sn = raw_sn / 4.5
        score_tf = raw_tf / 4.5
        score_jp = raw_jp / 4.5
        
        # Clamp just in case (Floating point errors)
        score_ei = max(-1.0, min(1.0, score_ei))
        score_sn = max(-1.0, min(1.0, score_sn))
        score_tf = max(-1.0, min(1.0, score_tf))
        score_jp = max(-1.0, min(1.0, score_jp))

        # 3. MBTI Determination
        # Positive = E, S, T, J
        # Negative = I, N, F, P
        mbti_e = "E" if score_ei > 0 else "I"
        mbti_s = "S" if score_sn > 0 else "N"
        mbti_t = "T" if score_tf > 0 else "F"
        mbti_j = "J" if score_jp > 0 else "P"
        
        mbti_result = mbti_e + mbti_s + mbti_t + mbti_j
        
        # 4. TraVTI Mapping
        # TODO: Update this mapping with the real one
        mbti_to_travti = {
            "ISTJ": "계획 관리자",
            "ISFJ": "친절 가이드",
            "INFJ": "사색 유랑자",
            "INTJ": "효율 전문가",
            "ISTP": "현장 해결사",
            "ISFP": "영감 수집가",
            "INFP": "감성 휴양가",
            "INTP": "꼼꼼한 기록자",
            "ESTP": "액티브 탐험가",
            "ESFP": "분위기 메이커",
            "ENFP": "낭만 여행가",
            "ENTP": "발굴 요원",
            "ESTJ": "경로 대장",
            "ESFJ": "팀 조율자",
            "ENFJ": "테마 기획자",
            "ENTJ": "안전 파수꾼"
        }
        
        travti_label = mbti_to_travti.get(mbti_result, "알 수 없음")
        
        # Define survey_id BEFORE using it
        survey_id = user_id if user_id else f'guest_{int(time.time())}'
        session['survey_id'] = survey_id
        
        # Save to temp JSON for testing without DB
        try:
            temp_data = {
                "survey_id": survey_id,
                "travti_label": travti_label,
                "base_mbti": mbti_result,
                "scores": {
                    "ei": score_ei,
                    "sn": score_sn,
                    "tf": score_tf,
                    "jp": score_jp,
                    "stamina": stamina_score,
                    "alcohol": alcohol_score
                },
                "timestamp": time.time()
            }
            with open("temp_test_result.json", "w", encoding="utf-8") as f:
                json.dump(temp_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Temp JSON Save Error: {e}")

        # Database logic temporarily disabled as requested
        # try:
        #     db = get_db()
        #     ...
        # except Exception as e:
        #     print(f"DB Save Error: {e}")
        
        
        # 로그인 상태 확인 후 리다이렉트 분기
        next_page = '/result'
        if not user_id:  # 로그인하지 않은 경우 프롬프트 페이지로
            next_page = '/auth-prompt'
            
        return {'success': True, 'redirect': next_page, 'survey_id': survey_id}, 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}, 500



@result_bp.route('/result')
def result():
    """결과 페이지"""
    survey_id = session.get('survey_id')
    user_id = session.get('user_id')
    current_user_name = session.get('user_name') or "Me"
    travti_label = "UNKNOWN"
    result_description = "당신의 여행 스타일을 분석 중입니다."
    
    # Descriptions map
    descriptions = {
        "팀 조율자": "팀을 이끌며 조화로운 여행을 만드는 당신\n'The Team Coordinator'\n함께하는 모든 이의 의견을 귀 기울여 듣고, 최고의 경험을 만들어내죠.",
        "영감 수집가": "세상의 아름다움을 놓치지 않는 예술가\n'The Inspiration Collector'\n골목의 한 모서리, 낡은 카페의 구석까지 감각 있게 담아내죠.",
        "경로 대장": "최적의 동선으로 완벽하게 계획하는 당신\n'The Route Master'\n지도를 손에 들고 효율적인 경로를 짜는 것이 당신의 즐거움이죠.",
        "발굴 요원": "숨겨진 보석을 찾아내는 탐험가\n'The Discovery Agent'\n가이드북에 없는 로컬 명소, 당신의 손끝에서 빛을 발하죠.",
        "친절 가이드": "현지인처럼 따뜻하게 맞이하는 당신\n'The Kindness Guide'\n낯선 곳에서도 웃음이 끊이지 않는 이유는 당신 때문이죠.",
        "분위기 메이커": "모든 순간을 설렘으로 채우는 당신\n'The Vibe Maker'\n밋밋한 일정도 당신의 손에서는 최고의 추억이 되죠.",
        "계획 관리자": "디테일한 계획으로 여행을 완성하는 당신\n'The Plan Manager'\n시간 낭비 없이, 놓친 것 없이, 완벽하게 진행되는 여행이죠.",
        "액티브 탐험가": "어디든 달려가고 싶은 에너지 넘치는 당신\n'The Active Explorer'\n아침부터 밤까지 온 힘을 다해 여행을 즐기는 모습이 멋져 보여요.",
        "사색 유랑자": "혼자의 시간을 소중히 여기는 명상가\n'The Contemplative Wanderer'\n조용한 거리를 걸으며 자신과 대화하는 당신의 여행이 진짜네요.",
        "낭만 여행가": "감정과 직관으로 움직이는 낭만가\n'The Romantic Traveler'\n계획은 없어도 괜찮아요, 그 순간의 설렘이 최고의 가이드니까요.",
        "테마 기획자": "각 날을 특별한 테마로 채우는 당신\n'The Theme Planner'\n오늘은 맛집 투어, 내일은 미술관 순례, 매일이 새로워요.",
        "효율 전문가": "시간과 비용을 똑똑하게 쓰는 당신\n'The Efficiency Expert'\n최소한의 움직임으로 최대의 경험을 만드는 전략가시죠.",
        "안전 파수꾼": "모든 것을 미리 체크하고 떠나는 당신\n'The Safety Guardian'\n만의 하나에 대비하는 꼼꼼함이 팀을 든든하게 만들어요.",
        "감성 휴양가": "휴식과 여유를 최우선으로 하는 당신\n'The Sensibility Vacationer'\n바쁜 일정보다는 맘 편히 쉴 수 있는 순간을 위해 여행을 가죠.",
        "꼼꼼한 기록자": "매 순간을 추억으로 남기는 당신\n'The Meticulous Recorder'\n사진과 기록으로 남겨진 당신의 여행이 가장 생생해요.",
        "현장 해결사": "예상 밖의 상황도 즉시 해결하는 당신\n'The On-the-Spot Problem Solver'\n변수가 생겨도 걱정 없어요, 당신이 있으니까요."
    }

    mbti_type = ""
    # Try loading from temp JSON for testing first
    try:
        import os
        if os.path.exists("temp_test_result.json"):
            with open("temp_test_result.json", "r", encoding="utf-8") as f:
                temp_data = json.load(f)
                # Check if it's recent (e.g., within last minute) or just use it
                if temp_data.get("survey_id") == survey_id:
                    travti_label = temp_data.get("travti_label", "UNKNOWN")
                    mbti_type = temp_data.get("base_mbti", "")
    except Exception as e:
        print(f"Temp JSON Load Error: {e}")

    # Fallback to DB if temp JSON didn't work or didn't match
    if travti_label == "UNKNOWN" and survey_id:
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT TraVTI_Label, Base_MBTI FROM survey_responses WHERE ID = ?", (survey_id,))
            row = cursor.fetchone()
            if row:
                if row[0]:
                    travti_label = row[0]
                if row[1]:
                    mbti_type = row[1]
        except Exception as e:
            print(f"DB 조회 오류: {e}")
            # Fallback if DB fails
            travti_label = "낭만 여행가"
    
    if travti_label == "UNKNOWN":
         # Fallback if everything fails
         travti_label = "낭만 여행가"
         
    display_label = f"{travti_label}"
    if mbti_type:
        display_label += f" <span class='text-3xl text-slate-400'>({mbti_type})</span>"

    result_description = descriptions.get(travti_label, "여행을 사랑하는 당신\n'The Traveler'\n새로운 경험과 만남을 즐기는 당신의 여행이 기대되네요.")
    
    # result_description 파싱 (comparison logic 전에 먼저 파싱해야 함)
    desc_lines = result_description.split('\n')
    if len(desc_lines) >= 2:
        result_description_title = ' '.join(desc_lines[:2])
        result_description_detail = '\n'.join(desc_lines[2:])
    else:
        result_description_title = result_description
        result_description_detail = ""

    # --- Comparison Text Logic ---
    comp_result_text = ""
    try:
        import os
        if os.path.exists("comp_test_result.json") and os.path.exists("temp_test_result.json"):
            # ... (comparison logic stays same, just verify indentation)
            with open("temp_test_result.json", "r", encoding="utf-8") as f:
                my_data = json.load(f)
            with open("comp_test_result.json", "r", encoding="utf-8") as f:
                comp_data = json.load(f)
            
            # Scores
            my_s = my_data.get("scores", {})
            comp_s = comp_data.get("scores", {})
            
            # 1. Trait Score Calculation
            # Diff calculation function
            def get_case_score(diff):
                # Cases from travti_scoring.md
                if diff == 0: return 18
                if diff <= 0.22: return 16
                if diff <= 0.44: return 14
                if diff <= 0.67: return 12
                if diff <= 0.89: return 10
                if diff <= 1.11: return 8
                if diff <= 1.33: return 6
                if diff <= 1.56: return 4
                return 2 # Case 9
            
            diff_ei = abs(my_s.get("ei", 0) - comp_s.get("ei", 0))
            diff_sn = abs(my_s.get("sn", 0) - comp_s.get("sn", 0))
            diff_tf = abs(my_s.get("tf", 0) - comp_s.get("tf", 0))
            diff_jp = abs(my_s.get("jp", 0) - comp_s.get("jp", 0))
            
            s_ei = get_case_score(diff_ei)
            s_sn = get_case_score(diff_sn)
            s_tf = get_case_score(diff_tf)
            s_jp = get_case_score(diff_jp)
            
            # Weighted Sum for 65 points
            trait_score = (s_ei * 0.35) + (s_sn * 0.25) + (s_tf * 0.20) + (s_jp * 0.20)
            
            # Scale to 65 points
            trait_score_scaled = trait_score * (65.0 / 18.0)
            
            # 2. Stamina Score (25 points)
            my_stamina = my_s.get("stamina", 0)
            comp_stamina = comp_s.get("stamina", 0)
            diff_stamina = abs(my_stamina - comp_stamina)
            
            stamina_score_val = 10 # Default Case 4
            if diff_stamina == 0: stamina_score_val = 25
            elif diff_stamina <= 0.25: stamina_score_val = 20
            elif diff_stamina <= 0.5: stamina_score_val = 15
            
            # 3. Alcohol Score (10 points)
            my_alc = my_s.get("alcohol", 0.5)
            comp_alc = comp_s.get("alcohol", 0.5)
            
            alc_score_val = 2
            s_set = {my_alc, comp_alc}
            
            if my_alc == comp_alc:
                if my_alc == 0.9: alc_score_val = 10
                elif my_alc == 0.1: alc_score_val = 10
                else: alc_score_val = 8
            else:
                if 0.9 in s_set and 0.1 in s_set: alc_score_val = 2
                elif 0.9 in s_set and 0.5 in s_set: alc_score_val = 4
                elif 0.5 in s_set and 0.1 in s_set: alc_score_val = 6
            
            total_score = trait_score_scaled + stamina_score_val + alc_score_val
            
            comp_result_text = f"""
            <div class="mt-8 p-6 bg-white rounded-xl shadow-sm border border-slate-200 text-left">
                <h3 class="text-xl font-bold text-slate-800 mb-4">🤝 페르소나 매칭 테스트</h3>
                <div class="flex items-center justify-between mb-4">
                    <div class="text-center">
                        <div class="text-sm text-slate-500">나 ({mbti_type})</div>
                        <div class="font-bold text-blue-600">{travti_label}</div>
                    </div>
                    <div class="text-2xl text-slate-300">VS</div>
                    <div class="text-center">
                        <div class="text-sm text-slate-500">상대방 ({comp_data.get('base_mbti')})</div>
                        <div class="font-bold text-slate-700">{comp_data.get('travti_label')}</div>
                    </div>
                </div>
                <div class="space-y-3 text-sm">
                    <div class="flex justify-between">
                        <span class="text-slate-600">성향 점수 (65점)</span>
                        <span class="font-mono font-bold">{trait_score_scaled:.1f}점</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-slate-600">체력 점수 (25점)</span>
                        <span class="font-mono font-bold">{stamina_score_val}점</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-slate-600">음주 점수 (10점)</span>
                        <span class="font-mono font-bold">{alc_score_val}점</span>
                    </div>
                    <div class="border-t border-slate-100 pt-3 flex justify-between items-center">
                        <span class="font-bold text-slate-800">최종 궁합 점수</span>
                        <span class="text-2xl font-bold text-blue-600">{total_score:.1f}점</span>
                    </div>
                </div>
            </div>
            """
            
            result_description_detail += comp_result_text
            
    except Exception as e:
        print(f"Comparison Error: {e}")

    # TraVTI별 아이콘 매핑
    travti_icons = {
        "팀 조율자": "groups",
        "영감 수집가": "palette",
        "경로 대장": "route",
        "발굴 요원": "explore",
        "친절 가이드": "handshake",
        "분위기 메이커": "celebration",
        "계획 관리자": "checklist",
        "액티브 탐험가": "hiking",
        "사색 유랑자": "spa",
        "낭만 여행가": "favorite",
        "테마 기획자": "lightbulb",
        "효율 전문가": "trending_up",
        "안전 파수꾼": "verified_user",
        "감성 휴양가": "nights_stay",
        "꼼꼼한 기록자": "photo_camera",
        "현장 해결사": "build"
    }
    travti_icon = travti_icons.get(travti_label, "restaurant")
    # Load current user display info
    if user_id:
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT Name, TraVTI_Label FROM survey_responses WHERE ID = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                if row[0]:
                    current_user_name = row[0]
                if row[1]:
                    travti_label = row[1]
        except Exception as e:
            print(f"현재 유저 정보 조회 오류: {e}")
    
    all_mbti_types = ["INTP", "ESTJ", "ENFP", "INFJ", "ENTP", "ISFP", "ISTJ", "ESFP"]
    mbti_buttons = "".join([f'<button onclick="addMbti(\'{m}\')" class="py-2 bg-slate-50 hover:bg-blue-50 rounded-lg font-bold border border-slate-200">{m}</button>' for m in all_mbti_types])

    def _safe_dom_id(value):
        return re.sub(r'[^a-zA-Z0-9_-]', '-', value)

    friend_cards = ""
    try:
        db = get_db()
        cursor = db.cursor()
        # Check if table exists to avoid crash
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='travis_data'")
        if cursor.fetchone():
            cursor.execute("""
                SELECT ID, Name, Actual_Label
                FROM travis_data
                WHERE ID LIKE 'TRV-NEW-%' AND Name IS NOT NULL AND Name != ''
                ORDER BY RANDOM()
                LIMIT 4
            """)
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    friend_id = str(row[0]) if row and row[0] is not None else ""
                    friend_name = str(row[1]) if row and row[1] is not None else "Unknown"
                    actual_label = str(row[2]) if row and row[2] is not None else ""
                    dom_key = _safe_dom_id(friend_id or friend_name)
                    safe_id = html.escape(friend_id or friend_name)
                    safe_name = html.escape(friend_name)
                    safe_label = html.escape(actual_label)
                    display_text = html.escape(f"{friend_name}({actual_label})") if actual_label else html.escape(friend_name)

                    friend_cards += f"""
                        <div id="friend-{dom_key}" data-user-id="{safe_id}" data-display-name="{safe_name}" data-travti="{safe_label}" draggable="true" ondragstart="handleDragStart(event, '{dom_key}')" onclick="addCompanionByClick('{dom_key}')" style="padding: 12px 14px; background: #f9fafb; border: 1.5px solid #e5e7eb; border-radius: 12px; text-align: center; font-weight: 600; font-size: 15px; color: #1f2937; cursor: grab; transition: all 0.2s; user-select: none; box-shadow: 0 1px 3px rgba(0,0,0,0.05);" onmouseenter="if(!this.dataset.disabled) this.style.background='#dbeafe'" onmouseleave="if(!this.dataset.disabled) this.style.background='#f9fafb'">{display_text}</div>
                    """
            else:
                friend_cards = '<div class="text-sm text-slate-400 text-center">친구 데이터가 없습니다</div>'
        else:
             friend_cards = '<div class="text-sm text-slate-400 text-center">친구 기능을 사용할 수 없습니다</div>'
    except Exception as e:
        print(f"친구 목록 조회 오류: {e}")
        friend_cards = '<div class="text-sm text-slate-400 text-center">친구 목록을 불러오지 못했습니다</div>'
    
    html_template = f"""<!DOCTYPE html><html><head>{COMMON_HEAD}<title>Your Result</title></head>
    <body class="bg-slate-50 min-h-screen">
        {get_header('result')}
        <!-- 메인 콘텐츠 -->
        <main class="max-w-2xl mx-auto px-6 py-16">
            <!-- 결과 섹션 -->
            <section class="text-center mb-16">
                <!-- 결과 아이콘 -->
                <div class="inline-block p-4 bg-blue-50 rounded-full mb-6 text-blue-500"><span class="material-symbols-outlined text-6xl">{travti_icon}</span></div>
                <!-- 결과 제목 -->
                <h2 class="text-lg font-semibold text-blue-500 mb-2">당신의 여행 스타일은</h2>
                <h1 class="text-5xl font-bold mb-6">{display_label}</h1>
                <div class="text-xl text-blue-500 font-semibold mb-4">{result_description_title}</div>
                <div class="text-base text-slate-600 mb-16 whitespace-pre-line">{result_description_detail}</div>
                


                <!-- 업로드 섹션 제거 -->



                <!-- 분석 UI 제거 -->


                <!-- 리더 선정 안내 -->


            <!-- MBTI 선택 박스 -->

            <!-- 일정 생성하기 -->

        </main>



        <!-- 결과 페이지 스크립트 -->
        <script>
            const addedMbti = ["{travti_label}"];
            const allMbtiTypes = {json.dumps(all_mbti_types)};
            let hasReservation = true;
            const memberStatsMap = {{}};

            const friendIdMap = {{}};

            function buildFriendIdMap() {{
                const items = document.querySelectorAll('#floating-panel-container [id^="friend-"]');
                items.forEach(item => {{
                    const userId = item.dataset.userId || '';
                    const displayName = item.dataset.displayName || item.textContent || '';
                    if (userId && displayName) {{
                        friendIdMap[displayName.trim()] = userId;
                    }}
                }});
            }}

            window.addEventListener('load', function() {{
                updateMbtiButtons();
                updateFloatingPanelPosition();
                updateCurrentUserFromSession();
                buildFriendIdMap();
                const meCard = document.getElementById('me-card');
                if (meCard && meCard.dataset.userId) {{
                    fetchMemberStats(meCard.dataset.userId);
                }}
            }});

            window.addEventListener('scroll', function() {{
                updateFloatingPanelPosition();
            }});

            function toggleReservation(isYes) {{
                hasReservation = isYes;
            }}

            function updateCurrentUserFromSession() {{
                fetch('/api/session_user')
                    .then(res => res.json())
                    .then(data => {{
                        if (!data || !data.logged_in) return;
                        const nameEl = document.getElementById('current-user-name');
                        const labelEl = document.getElementById('current-user-label');
                        const meCard = document.getElementById('me-card');
                        const displayName = data.name ? data.name : 'UNKNOWN';

                        if (nameEl) nameEl.textContent = displayName;
                        if (meCard) {{
                            meCard.dataset.userId = data.user_id || 'me';
                            const currentLabel = labelEl ? labelEl.textContent : '';
                            meCard.dataset.travti = currentLabel || 'UNKNOWN';
                            meCard.dataset.travtiMissing = (currentLabel === '' || currentLabel === 'UNKNOWN') ? 'true' : 'false';
                            if (data.user_id) {{
                                fetchMemberStats(data.user_id, displayName, currentLabel || null);
                            }}
                        }}
                    }})
                    .catch(() => {{}});
            }}

            function updateFloatingPanelPosition() {{
                const panel = document.getElementById('floating-panel-container');
                if (panel) {{
                    const scrollY = window.scrollY;
                    const viewportHeight = window.innerHeight;
                    const targetY = scrollY + (viewportHeight / 2) - 150;
                    panel.style.top = targetY + 'px';
                }}
            }}



            function handleDragStart(e, name) {{
                e.dataTransfer.setData('text/plain', name);
            }}

            function allowDrop(e) {{
                e.preventDefault();
            }}

            function handleDrop(e) {{
                e.preventDefault();
                const name = e.dataTransfer.getData('text/plain');
                if (!name) return;
                addCompanionCard(name);
            }}

            // 여행 일정(박/일) 조절
            let tripNights = 1;
            function adjustTripDays(delta) {{
                tripNights = Math.max(1, tripNights + delta);
                const label = document.getElementById('trip-nights-label');
                if (label) {{
                    label.textContent = `${{tripNights}}박 ${{tripNights + 1}}일`;
                }}
            }}

            let selectedLeaderId = null;

            function selectLeader(userId) {{
                const card = userId === 'me' ? document.getElementById('me-card') : document.querySelector(`[data-user-id="${{userId}}"]`);
                if (!card) return;
                
                const travtiLabel = card.dataset.travti;
                const isMissing = card.dataset.travtiMissing === 'true';
                
                // TraVTI_Label이 없는 경우 카드에 에러 메시지 표시
                if (isMissing || !travtiLabel || travtiLabel === '결과 없음' || travtiLabel === '로딩...' || travtiLabel === '불러오기 실패') {{
                    // 기존 에러 메시지 제거
                    const existingError = card.querySelector('.leader-error-msg');
                    if (existingError) existingError.remove();
                    
                    // 에러 메시지 추가
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'leader-error-msg absolute bottom-2 left-2 right-2 bg-red-50 border border-red-300 text-red-600 text-xs font-semibold px-3 py-2 rounded text-center';
                    errorMsg.textContent = 'TraVTI 검사 결과가 없어 리더로 선정할 수 없습니다';
                    card.appendChild(errorMsg);
                    
                    // 3초 후 메시지 제거
                    setTimeout(() => {{
                        if (errorMsg.parentNode === card) {{
                            errorMsg.remove();
                        }}
                    }}, 3000);
                    return;
                }}
                
                // 기존 에러 메시지 제거 (있다면)
                const existingError = card.querySelector('.leader-error-msg');
                if (existingError) existingError.remove();
                
                // 이전 리더 해제
                if (selectedLeaderId) {{
                    const prevCard = selectedLeaderId === 'me' ? document.getElementById('me-card') : document.querySelector(`[data-user-id="${{selectedLeaderId}}"]`);
                    if (prevCard) {{
                        prevCard.classList.remove('border-red-500');
                        prevCard.classList.add('border-slate-100');
                        const prevBadge = prevCard.querySelector('.leader-badge');
                        if (prevBadge) prevBadge.remove();
                    }}
                }}
                
                // 새 리더 설정
                selectedLeaderId = userId;
                card.classList.remove('border-slate-100');
                card.classList.add('border-red-500');
                
                // 리더 배지 추가
                const existingBadge = card.querySelector('.leader-badge');
                if (!existingBadge) {{
                    const badge = document.createElement('div');
                    badge.className = 'leader-badge absolute top-2 left-2 bg-red-500 text-white text-xs font-bold px-2 py-1 rounded';
                    badge.textContent = '리더';
                    card.appendChild(badge);
                }}
            }}

            function addCompanionCard(name) {{
                if (addedMbti.includes(name)) return;
                addedMbti.push(name);
                updateFloatingFriendState(name);

                const grid = document.getElementById('mbti-grid');
                const newCard = document.createElement('div');
                newCard.className = 'bg-white p-6 rounded-2xl shadow-md border border-slate-100 flex items-center gap-6 relative';
                newCard.dataset.travtiMissing = 'false';
                newCard.style.cursor = 'pointer';
                const friendEl = document.getElementById('friend-' + name);
                const userId = friendEl ? friendEl.dataset.userId : null;
                const displayName = friendEl ? (friendEl.dataset.displayName || friendEl.textContent || name) : name;
                const mappedId = friendIdMap[displayName] || '';
                const actualLabel = friendEl ? (friendEl.dataset.travti || '') : '';
                const labelId = 'travti-label-' + Date.now();
                const requestId = 'travti-request-' + Date.now();
                const resolvedId = userId || mappedId || '';
                newCard.dataset.userId = resolvedId;
                newCard.onclick = function() {{ selectLeader(userId || name); }};

                newCard.innerHTML = `
                    <div class="flex flex-col items-center shrink-0">
                        <div class="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center text-blue-500 mb-3">
                            <span class="material-symbols-outlined text-3xl">account_circle</span>
                        </div>
                        <div class="text-sm text-slate-500">${{displayName}}</div>
                    </div>
                    <div class="text-center flex-1">
                        <h4 id="${{labelId}}" class="font-black text-2xl text-blue-500">로딩...</h4>
                        <button id="${{requestId}}" class="mt-1 text-xs text-slate-400 hover:text-blue-500 underline decoration-dotted hidden" onclick="requestTravti('${{requestId}}')">TraVTI 검사 요청</button>
                    </div>
                    <button onclick="deleteMbti('${{name}}', this.closest('div'))" class="absolute top-2 right-2 text-gray-400 hover:text-red-500 transition-colors">X</button>
                `;

                const addButton = document.getElementById('add-button');
                grid.insertBefore(newCard, addButton);

                if (resolvedId) {{
                    fetchMemberStats(resolvedId, displayName, actualLabel);
                }}
                if (actualLabel) {{
                    const el = document.getElementById(labelId);
                    const requestEl = document.getElementById(requestId);
                    if (el) el.textContent = actualLabel;
                    if (requestEl) requestEl.classList.add('hidden');
                    newCard.dataset.travtiMissing = 'false';
                    newCard.dataset.travti = actualLabel;
                    updateTravtiMissingWarning();
                }} else if (userId) {{
                    fetch('/api/get_travti_label?user_id=' + encodeURIComponent(userId))
                        .then(res => res.json())
                        .then(data => {{
                            const el = document.getElementById(labelId);
                            const requestEl = document.getElementById(requestId);
                            if (data && data.travti_label) {{
                                if (el) el.textContent = data.travti_label;
                                if (requestEl) requestEl.classList.add('hidden');
                                newCard.dataset.travtiMissing = 'false';
                                newCard.dataset.travti = data.travti_label;
                            }} else {{
                                if (el) el.textContent = '결과 없음';
                                if (requestEl) requestEl.classList.remove('hidden');
                                newCard.dataset.travtiMissing = 'true';
                                newCard.dataset.travti = '결과 없음';
                            }}
                            updateTravtiMissingWarning();
                        }})
                        .catch(err => {{
                            const el = document.getElementById(labelId);
                            const requestEl = document.getElementById(requestId);
                            if (el) el.textContent = '불러오기 실패';
                            if (requestEl) requestEl.classList.add('hidden');
                            newCard.dataset.travtiMissing = 'true';
                            newCard.dataset.travti = '불러오기 실패';
                            updateTravtiMissingWarning();
                        }});
                }} else {{
                    const el = document.getElementById(labelId);
                    const requestEl = document.getElementById(requestId);
                    if (el) el.textContent = '결과 없음';
                    if (requestEl) requestEl.classList.remove('hidden');
                    newCard.dataset.travtiMissing = 'true';
                    newCard.dataset.travti = '결과 없음';
                    updateTravtiMissingWarning();
                }}
            }}

            function addCompanionByClick(name) {{
                addCompanionCard(name);
            }}

            function fetchMemberStats(userId, nameOverride, labelOverride) {{
                if (!userId) return;
                if (memberStatsMap[userId]) return;
                fetch('/api/get_member_stats?user_id=' + encodeURIComponent(userId))
                    .then(res => res.json())
                    .then(data => {{
                        if (data && !data.error) {{
                            memberStatsMap[userId] = {{
                                id: data.id,
                                name: data.name || nameOverride || data.id,
                                Score_EI: data.Score_EI,
                                Score_SN: data.Score_SN,
                                Score_TF: data.Score_TF,
                                Score_JP: data.Score_JP,
                                Stamina: data.Stamina,
                                Alcohol: data.Alcohol,
                                label: labelOverride || null
                            }};
                        }}
                    }})
                    .catch(() => {{}});
            }}

            function requestTravti(requestId) {{
                const el = document.getElementById(requestId);
                if (!el || el.dataset.requested === 'true') return;
                el.dataset.requested = 'true';
                el.textContent = '요청됨';
                el.classList.remove('hover:text-blue-500', 'underline', 'decoration-dotted');
                el.classList.add('text-slate-400');
                el.style.pointerEvents = 'none';
            }}

            function updateFloatingFriendState(name) {{
                const friendEl = document.getElementById('friend-' + name);
                if (friendEl) {{
                    friendEl.dataset.disabled = 'true';
                    friendEl.style.background = '#d1d5db';
                    friendEl.style.color = '#9ca3af';
                    friendEl.style.cursor = 'not-allowed';
                    friendEl.style.opacity = '0.6';
                    friendEl.draggable = false;
                    friendEl.onclick = null;
                }}
            }}

            function enableFloatingFriendState(name) {{
                const friendEl = document.getElementById('friend-' + name);
                if (friendEl) {{
                    friendEl.dataset.disabled = '';
                    friendEl.style.background = '#f9fafb';
                    friendEl.style.color = '#1f2937';
                    friendEl.style.cursor = 'grab';
                    friendEl.style.opacity = '1';
                    friendEl.draggable = true;
                    friendEl.onclick = function() {{ addCompanionByClick(name); }};
                }}
            }}

            function updateMbtiButtons() {{
                const container = document.getElementById('mbti-buttons-container');
                container.innerHTML = '';
                
                allMbtiTypes.forEach(mbti => {{
                    const button = document.createElement('button');
                    button.textContent = mbti;
                    button.className = 'py-2 rounded-lg font-bold border border-slate-200';
                    
                    if (addedMbti.includes(mbti)) {{
                        button.className += ' bg-gray-200 text-gray-400 cursor-not-allowed';
                        button.disabled = true;
                    }} else {{
                        button.className += ' bg-slate-50 hover:bg-blue-50';
                        button.onclick = function() {{ addMbti(mbti); }};
                    }}
                    
                    container.appendChild(button);
                }});
            }}

            function addMbti(type) {{
                if (addedMbti.includes(type)) {{
                    return;
                }}

                addedMbti.push(type);

                const grid = document.getElementById('mbti-grid');
                const newCard = document.createElement('div');
                newCard.className = 'bg-white p-6 rounded-2xl shadow-md border border-slate-100 flex items-center gap-5 relative';
                newCard.innerHTML = `
                    <div class="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center text-blue-500">
                        <span class="material-symbols-outlined text-3xl">account_circle</span>
                    </div>
                    <div class="text-left">
                        <h4 class="font-black text-2xl text-blue-500">${{type}}</h4>
                    </div>
                    <button onclick="deleteMbti('${{type}}', this.closest('div'))" class="absolute top-2 right-2 text-gray-400 hover:text-red-500 transition-colors">
                        <span class="material-symbols-outlined text-xl">close</span>
                    </button>
                `;
                
                const addButton = document.getElementById('add-button');
                grid.insertBefore(newCard, addButton);

                updateMbtiButtons();

                document.getElementById('selector-box').classList.add('hidden');
            }}

            function deleteMbti(type, cardElement) {{
                const index = addedMbti.indexOf(type);
                if (index > -1) {{
                    addedMbti.splice(index, 1);
                }}

                cardElement.remove();
                enableFloatingFriendState(type);
                updateMbtiButtons();
                updateTravtiMissingWarning();
            }}

            function updateTravtiMissingWarning() {{
                const warning = document.getElementById('travti-missing-warning');
                if (!warning) return;
                const missingCards = Array.from(document.querySelectorAll('#mbti-grid > div'))
                    .some(card => card.dataset && card.dataset.travtiMissing === 'true');
                if (missingCards) {{
                    warning.classList.remove('hidden');
                }} else {{
                    warning.classList.add('hidden');
                }}
            }}

            async function saveOccasion() {{
                const analyzedHotelEl = document.getElementById('analyzed-accommodation-input');
                const manualHotelEl = document.getElementById('trip-hotel-name-input');
                const analyzedDepartEl = document.getElementById('analyzed-departure-date');
                const manualDepartEl = document.getElementById('trip-departure-date');
                const analyzedArrivalEl = document.getElementById('analyzed-arrival-date');
                const manualArrivalEl = document.getElementById('trip-arrival-date');
                const analyzedDestinationEl = document.getElementById('analyzed-destination-input');
                const manualDestinationEl = document.getElementById('trip-destination-input');

                let tripHotelAddress = '';
                let tripStart = '';
                let tripEnd = '';
                let tripDestination = '';

                tripHotelAddress = manualHotelEl ? manualHotelEl.value : '';
                tripStart = manualDepartEl ? manualDepartEl.value : '';
                tripEnd = manualArrivalEl ? manualArrivalEl.value : '';
                tripDestination = manualDestinationEl ? manualDestinationEl.value : '';
                if (!tripDestination && typeof currentDestination !== 'undefined') {{
                    tripDestination = currentDestination;
                }}

                if (!tripHotelAddress || !tripStart || !tripEnd) {{
                    alert('호텔/출국/입국 정보를 모두 입력하거나 분석을 완료해주세요.');
                    return;
                }}

                const members = [];
                const cards = Array.from(document.querySelectorAll('#mbti-grid > div'))
                    .filter(card => card.id !== 'add-button');
                cards.forEach(card => {{
                    const nameEl = card.querySelector('.text-sm.text-slate-500');
                    const labelEl = card.querySelector('h4');
                    const name = nameEl ? nameEl.textContent.trim() : '';
                    const label = card.dataset && card.dataset.travti ? card.dataset.travti : (labelEl ? labelEl.textContent.trim() : '');
                    const userId = card.dataset && card.dataset.userId ? card.dataset.userId : (friendIdMap[name] || '');
                    if (name || label) {{
                        members.push({{ user_id: userId, name, label }});
                    }}
                }});
                const missingIds = members.filter(m => !m.user_id);
                if (missingIds.length > 0) {{
                    const names = missingIds.map(m => m.name || 'Unknown').join(', ');
                    alert(`구성원 ID가 없습니다: ${{names}}. 친구 목록에서 추가해주세요.`);
                    return;
                }}

                fetch('/api/save-occasion', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        trip_hotel_address: tripHotelAddress,
                        trip_start: tripStart,
                        trip_end: tripEnd,
                        trip_member: members,
                        member_stats: memberStatsMap,
                        trip_destination: tripDestination
                    }})
                }})
                    .then(res => res.json())
                    .then(data => {{
                        if (data && data.success) {{
                            alert('일정이 저장되었습니다. (Downgrade - End of Flow)');
                            // window.location.href = '/itinerary';
                            return;
                        }}
                        alert('일정 저장에 실패했습니다.');
                    }})
                    .catch(() => alert('일정 저장에 실패했습니다.'));
            }}
        </script>
    </body></html>
    """
    return render_template_string(html_template, mbti_buttons=mbti_buttons, all_mbti_types=all_mbti_types)


"""
답변 제출 및 결과 라우트 블루프린트
"""
import json
import sqlite3
import time
import joblib
import pandas as pd
from flask import Blueprint, request, render_template_string, session
from app import get_db
from utils import COMMON_HEAD, get_header, generate_next_id

result_bp = Blueprint('result', __name__)

@result_bp.route('/submit-answers', methods=['POST'])
def submit_answers():
    """모든 답변 제출"""
    data = request.get_json() or {}
    answers = data.get('answers', [])
    answer_indices = data.get('answer_indices', [])

    session['answers'] = answers

    if not answers or len(answers) != 20:
        return {'success': False, 'error': f'Invalid answers count: {len(answers)}'}, 400

    q_vals = []
    for q_num in range(1, 21):
        ans_text = answers[q_num - 1]
        idx = None
        if isinstance(answer_indices, list) and len(answer_indices) >= q_num:
            idx = answer_indices[q_num - 1]
        if q_num == 20:
            q_val = ans_text
        elif q_num == 6:
            stamina_map = [0.2, 0.5, 0.75, 1.0]
            q_val = stamina_map[int(idx)] if isinstance(idx, int) and 0 <= idx < len(stamina_map) else 0.2
        elif q_num == 15:
            alcohol_map = [0.9, 0.5, 0.1]
            q_val = alcohol_map[int(idx)] if isinstance(idx, int) and 0 <= idx < len(alcohol_map) else 0.5
        else:
            if isinstance(idx, int):
                q_val = 0 if idx == 0 else 1
            else:
                q_val = 0
        q_vals.append(q_val)

    q_vals_numeric = []
    for i, val in enumerate(q_vals):
        if i == 19:
            q_vals_numeric.append(val)
        else:
            try:
                q_vals_numeric.append(float(val))
            except Exception:
                q_vals_numeric.append(0.0)

    # 스코어 계산
    score_ei = (q_vals_numeric[4] + q_vals_numeric[7] + q_vals_numeric[13] + q_vals_numeric[18] * 1.5) / 4.5
    score_sn = (q_vals_numeric[6] + q_vals_numeric[8] + q_vals_numeric[9] * 1.5 + q_vals_numeric[16]) / 4.5
    score_tf = (q_vals_numeric[10] + q_vals_numeric[11] + q_vals_numeric[12] * 1.5 + q_vals_numeric[15]) / 4.5
    score_jp = (q_vals_numeric[0] + q_vals_numeric[1] + q_vals_numeric[2] + q_vals_numeric[17] * 1.5) / 4.5

    stamina = q_vals_numeric[5]
    alcohol = q_vals_numeric[14]

    survey_id = generate_next_id()
    db = get_db()
    cursor = db.cursor()

    # 모델 로드 및 예측
    try:
        with open('rf_travel_model_metadata.json', 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        rf_model = joblib.load('rf_travel_model.joblib')
        
        q_vals_for_pred = []
        for i in range(19):
            if i != 3:
                q_vals_for_pred.append(q_vals_numeric[i])
        
        feature_df = pd.DataFrame([q_vals_for_pred], columns=metadata['feature_columns'])
        prediction = rf_model.predict(feature_df)[0]
        travti_label = prediction
    except Exception as e:
        print(f"모델 예측 오류: {e}")
        travti_label = None

    insert_query = "INSERT INTO survey_responses (ID, Base_MBTI, Actual_Label, TraVTI_Label, TraVTI_Vector, Score_EI, Score_SN, Score_TF, Score_JP, Stamina, Alcohol, Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10, Q11, Q12, Q13, Q14, Q15, Q16, Q17, Q18, Q19, Q20, Q1_Val, Q2_Val, Q3_Val, Q4_Val, Q5_Val, Q6_Val, Q7_Val, Q8_Val, Q9_Val, Q10_Val, Q11_Val, Q12_Val, Q13_Val, Q14_Val, Q15_Val, Q16_Val, Q17_Val, Q18_Val, Q19_Val, Q20_Val) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    values = [
        survey_id,
        None, None, travti_label, None,
        round(score_ei, 3), round(score_sn, 3), round(score_tf, 3), round(score_jp, 3),
        stamina, alcohol
    ] + answers + q_vals_numeric

    for attempt in range(10):
        try:
            cursor.execute(insert_query, values)
            break
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed' in str(e) and attempt < 9:
                survey_id = generate_next_id()
                values[0] = survey_id
                time.sleep(0.1 * (attempt + 1))
                continue
            raise
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e).lower() and attempt < 9:
                time.sleep(0.2 * (attempt + 1))
                continue
            raise

    session['survey_id'] = survey_id
    return {'success': True, 'redirect': '/result', 'survey_id': survey_id}, 200


@result_bp.route('/result')
def result():
    """결과 페이지"""
    survey_id = session.get('survey_id')
    travti_label = "UNKNOWN"
    result_description = "당신의 여행 스타일을 분석 중입니다."
    
    if survey_id:
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT TraVTI_Label FROM survey_responses WHERE ID = ?", (survey_id,))
            row = cursor.fetchone()
            if row and row[0]:
                travti_label = row[0]
                descriptions = {
                    "INTP": "논리적 탐험가",
                    "ESTJ": "효율적 리더",
                    "ENFP": "자유로운 모험가",
                    "INFJ": "신비한 영혼의 여행객",
                    "ENTP": "도전적 발견자",
                    "ISFP": "감성적 여유로운 여행객",
                    "ISTJ": "계획적 방문객",
                    "ESFP": "사교적 축제 열정가"
                }
                result_description = descriptions.get(travti_label, "세련된 도시의 미식가\n'The Urban Foodie'")
        except Exception as e:
            print(f"DB 조회 오류: {e}")
    
    all_mbti_types = ["INTP", "ESTJ", "ENFP", "INFJ", "ENTP", "ISFP", "ISTJ", "ESFP"]
    mbti_buttons = "".join([f'<button onclick="addMbti(\'{m}\')" class="py-2 bg-slate-50 hover:bg-blue-50 rounded-lg font-bold border border-slate-200">{m}</button>' for m in all_mbti_types])
    
    html_template = f"""<!DOCTYPE html><html><head>{COMMON_HEAD}<title>Your Result</title></head>
    <body class="bg-slate-50 min-h-screen">
        {get_header('result')}
        <!-- 메인 콘텐츠 -->
        <main class="max-w-2xl mx-auto px-6 py-16">
            <!-- 결과 섹션 -->
            <section class="text-center mb-16">
                <!-- 결과 아이콘 -->
                <div class="inline-block p-4 bg-blue-50 rounded-full mb-6 text-blue-500"><span class="material-symbols-outlined text-6xl">restaurant</span></div>
                <!-- 결과 제목 -->
                <h2 class="text-lg font-semibold text-blue-500 mb-2">당신의 여행 스타일은</h2>
                <h1 class="text-5xl font-bold mb-6">{travti_label}</h1>
                <p class="text-xl text-blue-500 font-semibold mb-6">{result_description}</p>
                <!-- 결과 설명 -->
                <p class="text-lg text-slate-500 mb-16">현지인만 아는 미슐랭 가이드 맛집에서의 한 끼가 당신에겐 더 중요하죠.</p>
                
                <!-- 이번 여행 계획 요약 타이틀 -->
                <div class="text-left mb-6">
                    <h2 class="text-3xl font-extrabold mb-2">이번에 계획한 여행에 대해 알려주세요</h2>
                    <p class="text-sm text-slate-500">여행지와 일정을 선택하신 후, 동행자를 추가하세요.</p>
                </div>

                <!-- 여행지 선택 섹션 -->
                <div class="mb-4">
                    <div class="flex items-center justify-between px-2 mb-2">
                        <h2 class="text-slate-900 text-2xl font-bold">1. 여행지 선택하기</h2>
                    </div>
                    <div class="px-10 text-left flex items-center gap-4">
                        <p class="text-slate-700 font-bold text-xl">항공, 숙박을 예약하셨나요?</p>
                        <div class="inline-flex rounded-lg border-2 border-blue-500 overflow-hidden">
                            <button id="toggle-yes" class="px-4 py-2 font-bold text-white bg-blue-500 transition-colors" onclick="toggleReservation(true)">Y</button>
                            <button id="toggle-no" class="px-4 py-2 font-bold text-slate-700 bg-white transition-colors" onclick="toggleReservation(false)">N</button>
                        </div>
                    </div>
                </div>

                <!-- 업로드 섹션 -->
                <section id="upload-section" class="max-w-2xl mx-auto px-6 py-4 mb-8">
                    <div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
                        <h3 class="text-base font-semibold mb-4">항공권, 호텔 숙박권 업로드</h3>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="flex flex-col gap-4">
                                <div id="ticket-depart-drop" class="border-2 border-dashed border-slate-200 rounded-lg p-6 flex flex-col items-center justify-center text-center text-slate-500 cursor-pointer" ondragover="event.preventDefault()" ondrop="handleFileDrop(event, 'ticket_depart')" onclick="document.getElementById('ticket-depart-input').click()">
                                    <p class="font-semibold mb-2">출국 항공권</p>
                                    <p id="ticket_depart-instruction" class="text-sm">파일을 드래그하거나 클릭하여 업로드</p>
                                    <input id="ticket-depart-input" type="file" class="hidden" onchange="handleFileSelect(event, 'ticket_depart')" />
                                    <div class="mt-4" id="ticket_depart-preview"></div>
                                </div>
                                <div id="ticket-return-drop" class="border-2 border-dashed border-slate-200 rounded-lg p-6 flex flex-col items-center justify-center text-center text-slate-500 cursor-pointer" ondragover="event.preventDefault()" ondrop="handleFileDrop(event, 'ticket_return')" onclick="document.getElementById('ticket-return-input').click()">
                                    <p class="font-semibold mb-2">입국 항공권</p>
                                    <p id="ticket_return-instruction" class="text-sm">파일을 드래그하거나 클릭하여 업로드</p>
                                    <input id="ticket-return-input" type="file" class="hidden" onchange="handleFileSelect(event, 'ticket_return')" />
                                    <div class="mt-4" id="ticket_return-preview"></div>
                                </div>
                            </div>
                            <div id="hotel-drop" class="border-2 border-dashed border-slate-200 rounded-lg p-6 flex flex-col items-center justify-center text-center text-slate-500 cursor-pointer" ondragover="event.preventDefault()" ondrop="handleFileDrop(event, 'hotel')" onclick="document.getElementById('hotel-input').click()">
                                    <p class="font-semibold mb-2">호텔 숙박권</p>
                                    <p id="hotel-instruction" class="text-sm">파일을 드래그하거나 클릭하여 업로드</p>
                                    <input id="hotel-input" type="file" class="hidden" onchange="handleFileSelect(event, 'hotel')" />
                                    <div class="mt-4" id="hotel-preview"></div>
                                </div>
                        </div>
                    </div>
                </section>

                <!-- 수동 입력 섹션 -->
                <section id="manual-input-section" class="max-w-2xl mx-auto px-6 py-4 mb-8 hidden">
                    <div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
                        <h3 class="text-base font-semibold mb-4">목표 여행지와 일정을 입력해주세요</h3>
                        <div class="flex flex-col gap-4">
                            <!-- 여행지 -->
                            <div class="flex items-center gap-4">
                                <label class="text-slate-700 font-semibold whitespace-nowrap w-40">여행지 :</label>
                                <input id="trip-destination-input" type="text" placeholder="도시 - ex) 도경" class="flex-1 rounded-lg border border-slate-200 px-4 py-3 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200" />
                            </div>
                            <!-- 호텔명 -->
                            <div class="flex items-center gap-4">
                                <label class="text-slate-700 font-semibold whitespace-nowrap w-40">호텔명 :</label>
                                <input id="trip-hotel-name-input" type="text" placeholder="ex) 호텔 뉴 오타니 도쿄" class="flex-1 rounded-lg border border-slate-200 px-4 py-3 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200" />
                            </div>
                            <!-- 예상 출국 날짜/시간 -->
                            <div class="flex items-center gap-4">
                                <label class="text-slate-700 font-semibold whitespace-nowrap w-40">예상 출국 날짜 :</label>
                                <input id="trip-departure-date" type="date" class="flex-1 rounded-lg border border-slate-200 px-4 py-3 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200" />
                                <select id="trip-departure-ampm" class="rounded-lg border border-slate-200 px-2 py-2 pr-6 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200">
                                    <option value="AM">오전</option>
                                    <option value="PM">오후</option>
                                </select>
                                <select id="trip-departure-hour" class="rounded-lg border border-slate-200 px-2 py-2 pr-6 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200 w-16">
                                    <option value="12">12시</option>
                                    <option value="1">1시</option>
                                    <option value="2">2시</option>
                                    <option value="3">3시</option>
                                    <option value="4">4시</option>
                                    <option value="5">5시</option>
                                    <option value="6">6시</option>
                                    <option value="7">7시</option>
                                    <option value="8">8시</option>
                                    <option value="9">9시</option>
                                    <option value="10">10시</option>
                                    <option value="11">11시</option>
                                </select>
                            </div>
                            <!-- 예상 입국 날짜/시간 -->
                            <div class="flex items-center gap-4">
                                <label class="text-slate-700 font-semibold whitespace-nowrap w-40">예상 입국 날짜 :</label>
                                <input id="trip-arrival-date" type="date" class="flex-1 rounded-lg border border-slate-200 px-4 py-3 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200" />
                                <select id="trip-arrival-ampm" class="rounded-lg border border-slate-200 px-2 py-2 pr-6 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200">
                                    <option value="AM">오전</option>
                                    <option value="PM">오후</option>
                                </select>
                                <select id="trip-arrival-hour" class="rounded-lg border border-slate-200 px-2 py-2 pr-6 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200 w-16">
                                    <option value="12">12시</option>
                                    <option value="1">1시</option>
                                    <option value="2">2시</option>
                                    <option value="3">3시</option>
                                    <option value="4">4시</option>
                                    <option value="5">5시</option>
                                    <option value="6">6시</option>
                                    <option value="7">7시</option>
                                    <option value="8">8시</option>
                                    <option value="9">9시</option>
                                    <option value="10">10시</option>
                                    <option value="11">11시</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- 일정 분석 버튼 -->
                <div id="analysis-button-container" class="mb-6 text-center hidden">
                    <button onclick="showAnalyzedItinerary()" class="px-8 py-3 bg-blue-500 text-white font-bold rounded-lg hover:bg-blue-600 transition-colors">일정 분석</button>
                </div>

                <!-- 분석된 여행 일정 섹션 -->
                <section id="analyzed-itinerary-section" class="max-w-2xl mx-auto px-6 py-4 mb-8 hidden">
                    <div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
                        <h3 class="text-base font-semibold mb-4">분석된 여행 일정</h3>
                        <div class="flex flex-col gap-4">
                            <!-- 여행지 -->
                            <div class="flex items-center gap-4">
                                <label class="text-slate-700 font-semibold whitespace-nowrap w-40">여행지 :</label>
                                <input id="analyzed-destination-input" type="text" class="flex-1 rounded-lg border border-slate-200 px-4 py-3 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200" />
                            </div>
                            <!-- 숙박 정보 -->
                            <div class="flex items-center gap-4">
                                <label class="text-slate-700 font-semibold whitespace-nowrap w-40">숙박 정보 :</label>
                                <input id="analyzed-accommodation-input" type="text" class="flex-1 rounded-lg border border-slate-200 px-4 py-3 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200" />
                            </div>
                            <!-- 출국 날짜 -->
                            <div class="flex items-center gap-4">
                                <label class="text-slate-700 font-semibold whitespace-nowrap w-40">출국 날짜 :</label>
                                <input id="analyzed-departure-date" type="date" class="flex-1 rounded-lg border border-slate-200 px-4 py-3 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200" />
                            </div>
                            <!-- 입국 날짜 -->
                            <div class="flex items-center gap-4">
                                <label class="text-slate-700 font-semibold whitespace-nowrap w-40">입국 날짜 :</label>
                                <input id="analyzed-arrival-date" type="date" class="flex-1 rounded-lg border border-slate-200 px-4 py-3 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-200" />
                            </div>
                        </div>
                    </div>
                </section>

                <!-- 동행자 MBTI 선택 섹션 -->
                <div class="flex items-end justify-between border-b border-slate-200 pb-4 mb-4">
                    <h3 class="text-2xl font-bold mb-1">2. 동행자 추가하기</h3>
                    <span id="travti-missing-warning" class="hidden text-xs text-red-500 mb-1">TraVTI 검사를 실시하지않은 인원의 성향은 고려되지 않습니다</span>
                </div>
                <!-- 리더 선정 안내 -->
                <div class="mb-6 px-2">
                    <p class="text-blue-600 font-bold text-sm">하단 인물 카드를 클릭해서 '리더'를 선정해주세요. 여행지 추천에 리더의 성향이 가장 많이 반영됩니다</p>
                </div>
                <!-- MBTI 그리드 -->
                <div class="grid grid-cols-2 gap-6" id="mbti-grid">
                    <!-- 내 MBTI 표시 -->
                    <div class="bg-white p-6 rounded-2xl shadow-md border border-slate-100 flex items-center gap-6 relative" id="me-card" data-user-id="me" data-travti="{travti_label}" onclick="selectLeader('me')" style="cursor: pointer;">
                        <div class="flex flex-col items-center shrink-0">
                            <div class="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center text-blue-500 mb-3"><span class="material-symbols-outlined text-3xl">account_circle</span></div>
                            <div class="text-sm text-slate-500">Me</div>
                        </div>
                        <div class="text-center flex-1">
                            <h4 class="font-black text-2xl text-blue-500">{travti_label}</h4>
                        </div>
                    </div>
                    <!-- 동행자 추가 드롭 존 -->
                    <div ondragover="allowDrop(event)" ondrop="handleDrop(event)" class="border-2 border-dashed border-blue-300 bg-blue-50 p-8 rounded-2xl flex flex-col items-center justify-center gap-3 text-blue-400 transition-all hover:border-blue-500 hover:bg-blue-100" id="add-button">
                        <span class="material-symbols-outlined text-5xl">person_add</span>
                        <div class="text-center">
                            <p class="text-sm font-semibold text-blue-600">우측 친구를 드래그하여</p>
                            <p class="text-sm font-semibold text-blue-600">동행자를 추가하세요</p>
                        </div>
                    </div>
                </div>
            </section>

            <!-- MBTI 선택 박스 -->
            <div id="selector-box" class="hidden bg-white p-8 rounded-3xl shadow-xl border border-blue-100 mt-10">
                <h4 class="font-bold mb-6 text-lg text-left">추가할 MBTI 선택</h4>
                <div class="grid grid-cols-4 gap-4" id="mbti-buttons-container">
                    {{{{ mbti_buttons|safe }}}}
                </div>
            </div>
            <!-- 일정 생성하기 -->
            <div class="mt-12 text-center">
                <button onclick="window.location.href='/group-recommendation'" class="inline-flex items-center justify-center gap-2 px-8 py-3 rounded-xl bg-blue-500 text-white font-bold hover:bg-blue-600 transition-colors">
                    일정 생성하기
                </button>
            </div>
        </main>

        <!-- 우측 떠있는 동행자 선택 패널 -->
        <div id="floating-panel-container" style="position: absolute; right: 160px; z-index: 50;">
            <div style="background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.12); padding: 20px; min-width: 180px; border: 1px solid #e5e7eb; backdrop-filter: blur(10px); background-color: rgba(255,255,255,0.95);">
                <p style="font-size: 20px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 16px; text-align: center;">친구 목록</p>
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <div id="friend-kevin" data-user-id="kevin" data-travti="낭만 여행가" draggable="true" ondragstart="handleDragStart(event, 'kevin')" onclick="addCompanionByClick('kevin')" style="padding: 12px 14px; background: #f9fafb; border: 1.5px solid #e5e7eb; border-radius: 12px; text-align: center; font-weight: 600; font-size: 15px; color: #1f2937; cursor: grab; transition: all 0.2s; user-select: none; box-shadow: 0 1px 3px rgba(0,0,0,0.05);" onmouseenter="if(!this.dataset.disabled) this.style.background='#dbeafe'" onmouseleave="if(!this.dataset.disabled) this.style.background='#f9fafb'">kevin</div>
                    <div id="friend-혁수" data-user-id="혁수" data-travti="발굴 요원" draggable="true" ondragstart="handleDragStart(event, '혁수')" onclick="addCompanionByClick('혁수')" style="padding: 12px 14px; background: #f9fafb; border: 1.5px solid #e5e7eb; border-radius: 12px; text-align: center; font-weight: 600; font-size: 15px; color: #1f2937; cursor: grab; transition: all 0.2s; user-select: none; box-shadow: 0 1px 3px rgba(0,0,0,0.05);" onmouseenter="if(!this.dataset.disabled) this.style.background='#dbeafe'" onmouseleave="if(!this.dataset.disabled) this.style.background='#f9fafb'">혁수</div>
                    <div id="friend-재혁" data-user-id="재혁" data-travti="테마 기획자" draggable="true" ondragstart="handleDragStart(event, '재혁')" onclick="addCompanionByClick('재혁')" style="padding: 12px 14px; background: #f9fafb; border: 1.5px solid #e5e7eb; border-radius: 12px; text-align: center; font-weight: 600; font-size: 15px; color: #1f2937; cursor: grab; transition: all 0.2s; user-select: none; box-shadow: 0 1px 3px rgba(0,0,0,0.05);" onmouseenter="if(!this.dataset.disabled) this.style.background='#dbeafe'" onmouseleave="if(!this.dataset.disabled) this.style.background='#f9fafb'">재혁</div>
                    <div id="friend-민웅" data-user-id="민웅" data-travti="감성 휴양가" draggable="true" ondragstart="handleDragStart(event, '민웅')" onclick="addCompanionByClick('민웅')" style="padding: 12px 14px; background: #f9fafb; border: 1.5px solid #e5e7eb; border-radius: 12px; text-align: center; font-weight: 600; font-size: 15px; color: #1f2937; cursor: grab; transition: all 0.2s; user-select: none; box-shadow: 0 1px 3px rgba(0,0,0,0.05);" onmouseenter="if(!this.dataset.disabled) this.style.background='#dbeafe'" onmouseleave="if(!this.dataset.disabled) this.style.background='#f9fafb'">민웅</div>
                </div>
            </div>
        </div>

        <!-- 결과 페이지 스크립트 -->
        <script>
            const addedMbti = ["{travti_label}"];
            const allMbtiTypes = {json.dumps(all_mbti_types)};
            let hasReservation = true;

            window.addEventListener('load', function() {{
                updateMbtiButtons();
                updateFloatingPanelPosition();
            }});

            window.addEventListener('scroll', function() {{
                updateFloatingPanelPosition();
            }});

            function toggleReservation(isYes) {{
                hasReservation = isYes;
                const uploadSection = document.getElementById('upload-section');
                const manualSection = document.getElementById('manual-input-section');
                const btnYes = document.getElementById('toggle-yes');
                const btnNo = document.getElementById('toggle-no');

                if (isYes) {{
                    uploadSection.classList.remove('hidden');
                    manualSection.classList.add('hidden');
                    btnYes.classList.add('bg-blue-500', 'text-white');
                    btnYes.classList.remove('bg-white', 'text-slate-700');
                    btnNo.classList.remove('bg-red-500', 'text-white', 'bg-blue-500');
                    btnNo.classList.add('bg-white', 'text-slate-700');
                }} else {{
                    uploadSection.classList.add('hidden');
                    manualSection.classList.remove('hidden');
                    btnNo.classList.add('bg-red-500', 'text-white');
                    btnNo.classList.remove('bg-white', 'text-slate-700', 'bg-blue-500');
                    btnYes.classList.remove('bg-blue-500', 'text-white');
                    btnYes.classList.add('bg-white', 'text-slate-700');
                }}
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

            function handleFileSelect(e, kind) {{
                const file = e.target.files && e.target.files[0];
                if (!file) return;
                renderFilePreview(kind, file);
                checkFileUploads();
            }}

            function handleFileDrop(e, kind) {{
                e.preventDefault();
                const file = e.dataTransfer.files && e.dataTransfer.files[0];
                if (!file) return;
                renderFilePreview(kind, file);
                checkFileUploads();
            }}

            function checkFileUploads() {{
                const departInput = document.getElementById('ticket-depart-input');
                const returnInput = document.getElementById('ticket-return-input');
                const hotelInput = document.getElementById('hotel-input');
                const analysisBtn = document.getElementById('analysis-button-container');
                
                if ((departInput && departInput.files.length > 0) || 
                    (returnInput && returnInput.files.length > 0) || 
                    (hotelInput && hotelInput.files.length > 0)) {{
                    analysisBtn.classList.remove('hidden');
                }} else {{
                    analysisBtn.classList.add('hidden');
                }}
            }}

            function showAnalyzedItinerary() {{
                const analyzedSection = document.getElementById('analyzed-itinerary-section');
                analyzedSection.classList.remove('hidden');
                analyzedSection.scrollIntoView({{ behavior: 'smooth' }});
            }}

            function getInputIdFromKind(kind) {{
                return kind.replace('_', '-') + '-input';
            }}

            function renderFilePreview(kind, file) {{
                const previewEl = document.getElementById(kind + '-preview');
                const instructionEl = document.getElementById(kind + '-instruction');
                if (!previewEl) return;

                previewEl.innerHTML = `
                    <div class="text-sm font-semibold text-slate-700">${{file.name}}</div>
                `;
                if (instructionEl) instructionEl.classList.add('hidden');
            }}

            function clearFilePreview(kind) {{
                const inputId = getInputIdFromKind(kind);
                const inputEl = document.getElementById(inputId);
                const previewEl = document.getElementById(kind + '-preview');
                const instructionEl = document.getElementById(kind + '-instruction');
                if (inputEl) inputEl.value = '';
                if (previewEl) previewEl.innerHTML = '';
                if (instructionEl) instructionEl.classList.remove('hidden');
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
                const labelId = 'travti-label-' + Date.now();
                const requestId = 'travti-request-' + Date.now();
                newCard.dataset.userId = userId || name;
                newCard.onclick = function() {{ selectLeader(userId || name); }};

                newCard.innerHTML = `
                    <div class="flex flex-col items-center shrink-0">
                        <div class="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center text-blue-500 mb-3">
                            <span class="material-symbols-outlined text-3xl">account_circle</span>
                        </div>
                        <div class="text-sm text-slate-500">${{name}}</div>
                    </div>
                    <div class="text-center flex-1">
                        <h4 id="${{labelId}}" class="font-black text-2xl text-blue-500">로딩...</h4>
                        <button id="${{requestId}}" class="mt-1 text-xs text-slate-400 hover:text-blue-500 underline decoration-dotted hidden" onclick="requestTravti('${{requestId}}')">TraVTI 검사 요청</button>
                    </div>
                    <button onclick="deleteMbti('${{name}}', this.closest('div'))" class="absolute top-2 right-2 text-gray-400 hover:text-red-500 transition-colors">X</button>
                `;

                const addButton = document.getElementById('add-button');
                grid.insertBefore(newCard, addButton);

                if (userId) {{
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
        </script>
    </body></html>
    """
    return render_template_string(html_template, mbti_buttons=mbti_buttons, all_mbti_types=all_mbti_types)
"""
그룹 여행 추천 라우트 블루프린트
"""
import json
import sqlite3
import time
import joblib
import pandas as pd
from flask import Blueprint, request, render_template_string, session
from app import get_db

# Import helpers from project root. When this module is run directly
# Python's import path may not include the project root, so attempt
# normal import then fall back to adding parent directory to sys.path.
try:
    from utils import COMMON_HEAD, get_header, generate_next_id
except Exception:
    import sys, os
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if root not in sys.path:
        sys.path.insert(0, root)
    from utils import COMMON_HEAD, get_header, generate_next_id

group_bp = Blueprint('group', __name__)

# ========================================
# 여행지별 관광지 데이터
# ========================================
DESTINATIONS_DATA = {
    "일본": {
        "description": "효율적인 탐험가들(ENTJ + INTP)을 위한 맞춤형 선택",
        "attractions": [
            {
                "name": "Universal Studios Japan",
                "subtitle": "오사카의 엔터테인먼트 성지",
                "icon": "apartment",
                "color": "from-red-400 to-red-600",
                "match": "97%",
                "reason": "다양한 테마 영역을 효율적으로 관광하는 ENTJ와 각 어트랙션의 기술적 메커니즘을 분석하고 싶어하는 INTP를 시간 내에 모두 만족시키는 완벽한 명소입니다.",
                "buttonText": "USJ 둘러보기"
            },
            {
                "name": "21세기 미술관",
                "subtitle": "전통과 현대의 대화",
                "icon": "museum",
                "color": "from-amber-500 to-amber-700",
                "match": "94%",
                "reason": "현대 건축의 우아함을 효율적으로 감상하는 ENTJ와 미술 작품의 철학적 의미와 기술적 표현 방식을 깊이 있게 분석하고 싶은 INTP를 동시에 만족시키는 완벽한 예술 공간입니다.",
                "buttonText": "미술관 둘러보기"
            },
            {
                "name": "도쿄 스카이트리",
                "subtitle": "도시의 최고 관점에서의 경험",
                "icon": "domain",
                "color": "from-blue-400 to-blue-600",
                "match": "91%",
                "reason": "높이 634m에서 도쿄의 모든 것을 한눈에 파악하고 싶은 ENTJ와 건축 구조의 공학적 원리를 탐구하고 싶은 INTP의 욕구를 동시에 충족시킵니다.",
                "buttonText": "스카이트리 둘러보기"
            },
            {
                "name": "교토 철학의 길",
                "subtitle": "전통 문화와 사색의 공간",
                "icon": "temple_buddhist",
                "color": "from-orange-400 to-orange-600",
                "match": "88%",
                "reason": "1.5km의 수로를 따라 산책하며 전통 사원들을 효율적으로 관광하고, 동양 철학에 대해 깊이 있게 사색할 수 있는 명소입니다.",
                "buttonText": "철학의 길 둘러보기"
            }
        ]
    },
    "베트남": {
        "description": "모험심과 문화 탐구를 동시에 즐기는 여행자들을 위한 선택",
        "attractions": [
            {
                "name": "하롱베이 크루즈",
                "subtitle": "자연의 경이로움을 효율적으로 경험",
                "icon": "directions_boat",
                "color": "from-cyan-400 to-cyan-600",
                "match": "96%",
                "reason": "유네스코 세계문화유산인 하롱베이를 짧은 시간에 경험하고, 카스트 지형의 지질학적 특성을 탐구할 수 있습니다.",
                "buttonText": "크루즈 예약"
            },
            {
                "name": "호이안 야간 산책",
                "subtitle": "과거로의 시간 여행",
                "icon": "light_mode",
                "color": "from-yellow-400 to-yellow-600",
                "match": "93%",
                "reason": "15-19세기 무역 도시의 역사를 직접 체험하며, 동남아 전통 건축 문화를 깊이 있게 이해할 수 있습니다.",
                "buttonText": "호이안 투어"
            },
            {
                "name": "사파 트래킹",
                "subtitle": "산악 모험과 소수민족 문화",
                "icon": "hiking",
                "color": "from-green-400 to-green-600",
                "match": "90%",
                "reason": "전략적 트레킹 루트로 효율적으로 산악 경험을 하고, 소수민족 공동체의 생활방식을 직접 관찰하고 분석할 수 있습니다.",
                "buttonText": "사파 트래킹"
            },
            {
                "name": "메콩 델타 투어",
                "subtitle": "물 위의 전통 생활",
                "icon": "agriculture",
                "color": "from-teal-400 to-teal-600",
                "match": "87%",
                "reason": "강줄기를 따라 베트남의 시골 경제와 생태계를 체계적으로 탐사하며, 지속가능한 농업 모델을 학습할 수 있습니다.",
                "buttonText": "메콩 델타 투어"
            }
        ]
    },
    "프랑스": {
        "description": "예술, 문화, 철학을 깊이 있게 탐구하는 지식인들을 위한 선택",
        "attractions": [
            {
                "name": "루브르 박물관",
                "subtitle": "세계 최고의 미술관",
                "icon": "frame_inspect",
                "color": "from-purple-400 to-purple-600",
                "match": "95%",
                "reason": "9,000개 이상의 작품을 체계적으로 관광하고, 서양 미술사의 흐름을 깊이 있게 분석할 수 있는 최고의 장소입니다.",
                "buttonText": "루브르 방문"
            },
            {
                "name": "몽마르트르 언덕",
                "subtitle": "예술가들의 거리",
                "icon": "palette",
                "color": "from-pink-400 to-pink-600",
                "match": "92%",
                "reason": "19세기 예술 혁명의 중심지를 탐방하며, 인상주의 화가들의 창작 배경을 깊이 있게 이해할 수 있습니다.",
                "buttonText": "몽마르트르 투어"
            },
            {
                "name": "베르사유 궁전",
                "subtitle": "왕권과 건축의 정점",
                "icon": "castle",
                "color": "from-amber-400 to-amber-600",
                "match": "91%",
                "reason": "17세기 절대주의 권력의 물리적 구현을 관찰하고, 건축학적 완벽성과 정치 체제의 관계를 분석할 수 있습니다.",
                "buttonText": "베르사유 방문"
            },
            {
                "name": "라틴쿼터 철학 산책",
                "subtitle": "지식의 중심",
                "icon": "school",
                "color": "from-blue-400 to-blue-600",
                "match": "89%",
                "reason": "소르본 대학과 팡테옹을 중심으로 프랑스 철학 전통의 발상지를 탐방하며, 계몽사상의 흔적을 따라갈 수 있습니다.",
                "buttonText": "라틴쿼터 탐방"
            }
        ]
    },
    "이탈리아": {
        "description": "역사와 예술, 그리고 인간의 위대함을 추구하는 이들을 위한 선택",
        "attractions": [
            {
                "name": "피렌체 우피치 미술관",
                "subtitle": "르네상스의 심장",
                "icon": "art_gallery",
                "color": "from-red-400 to-red-600",
                "match": "96%",
                "reason": "르네상스 회화의 걸작들을 시간별로 효율적으로 감상하며, 인간 중심의 미학 철학이 어떻게 진화했는지 추적할 수 있습니다.",
                "buttonText": "우피치 방문"
            },
            {
                "name": "로마 콜로세움",
                "subtitle": "고대 제국의 웅장함",
                "icon": "important_devices",
                "color": "from-orange-400 to-orange-600",
                "match": "93%",
                "reason": "2,000년 된 고대 건축의 공학적 기적을 직접 경험하고, 로마 제국의 정치 구조와 사회 체제를 분석할 수 있습니다.",
                "buttonText": "콜로세움 방문"
            },
            {
                "name": "베네치아 대운하",
                "subtitle": "물 위의 예술 도시",
                "icon": "directions_boat",
                "color": "from-cyan-400 to-cyan-600",
                "match": "90%",
                "reason": "중세 무역 도시의 건축 기술과 예술적 감각을 고드올라 여행 중에 직접 관찰하며, 해상 공화국의 역사를 이해할 수 있습니다.",
                "buttonText": "베네치아 투어"
            },
            {
                "name": "바티칸 박물관",
                "subtitle": "인류의 영적 유산",
                "icon": "temple_buddhist",
                "color": "from-yellow-400 to-yellow-600",
                "match": "88%",
                "reason": "미켈란젤로의 시스티나 예배당과 라파엘로의 작품을 통해 종교 미술의 정점을 경험하고, 르네상스 정신을 체득할 수 있습니다.",
                "buttonText": "바티칸 방문"
            }
        ]
    }
}

@group_bp.route('/group-recommendation')
def group_recommendation():
    """AI 그룹 추천 결과 페이지"""
    destinations_json = json.dumps(DESTINATIONS_DATA, ensure_ascii=False)
    
    html_template = f"""<!DOCTYPE html><html class="light" lang="ko"><head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
    <title>TraVis | AI 그룹 여행 추천 결과</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700;800;900&display=swap" rel="stylesheet"/>
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
    <style>
        body {{ font-family: 'Pretendard', sans-serif; }}
        .hide-scrollbar::-webkit-scrollbar {{ display: none; }}
        .hide-scrollbar {{ -ms-overflow-style: none; scrollbar-width: none; }}
    </style>
    </head>
    <body class="bg-slate-50">
    <div class="relative flex min-h-screen w-full flex-col overflow-x-hidden">
        {get_header('group')}
        
        <!-- 메인 콘텐츠 -->
        <main class="flex-1 max-w-3xl mx-auto w-full px-6 pb-20">
            <!-- 타이틀 -->
            <div class="py-10 text-center">
                <h1 class="text-slate-900 tracking-tight text-4xl font-extrabold leading-tight pb-8">우리 그룹 분석</h1>
            </div>
            
            <!-- 그룹 분석 카드 -->
            <div class="bg-white rounded-3xl shadow-lg border border-slate-100 p-8 mb-12">
                <div class="flex flex-col items-center text-center gap-6">
                    <!-- 그룹 분석 제목 -->
                    <div class="max-w-2xl">
                        <div class="inline-flex items-center px-3 py-1 rounded-full bg-blue-100 text-blue-600 text-xs font-bold uppercase tracking-wider mb-2">여행 궁합 발견</div>
                        <p class="text-slate-900 text-3xl font-extrabold leading-tight tracking-tight">ENTJ + INTP: 효율적인 탐험가들</p>
                        <p class="text-slate-600 text-lg mt-3">자유로운 호기심과 전략적인 계획이 완벽하게 어우러진 조합입니다. 깊이 있는 탐색과 명확한 방향성 사이에서 균형 잡힌 여행을 즐깁니다.</p>
                        
                        <!-- 궁합 지표 -->
                        <div class="mt-8 flex flex-wrap justify-center gap-6">
                            <div class="flex flex-col items-center">
                                <span class="text-blue-500 text-2xl font-black">98%</span>
                                <span class="text-slate-600 text-sm font-medium">시너지 점수</span>
                            </div>
                            <div class="w-px h-10 bg-slate-200"></div>
                            <div class="flex flex-col items-center">
                                <span class="text-blue-500 text-2xl font-black">Active</span>
                                <span class="text-slate-600 text-sm font-medium">여행 템포</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 여행지 선택 섹션 -->
            <div class="mb-12">
                <div class="flex items-center justify-between px-2 mb-4">
                    <h2 class="text-slate-900 text-2xl font-bold">1. 여행지 선택하기</h2>
                </div>
                <div class="flex gap-4 overflow-x-auto hide-scrollbar pb-4">
                    <button onclick="selectDestination('일본')" class="destination-btn flex h-12 shrink-0 items-center justify-center gap-x-3 rounded-xl bg-blue-500 px-6 shadow-md text-white font-bold hover:bg-blue-600 transition-colors" data-destination="일본">
                        <span class="material-symbols-outlined">flag</span>
                        <p>일본</p>
                    </button>
                    <button onclick="selectDestination('베트남')" class="destination-btn flex h-12 shrink-0 items-center justify-center gap-x-3 rounded-xl bg-white border border-slate-200 px-6 text-slate-700 font-medium hover:border-blue-500 transition-all" data-destination="베트남">
                        <span class="material-symbols-outlined">flag</span>
                        <p>베트남</p>
                    </button>
                    <button onclick="selectDestination('프랑스')" class="destination-btn flex h-12 shrink-0 items-center justify-center gap-x-3 rounded-xl bg-white border border-slate-200 px-6 text-slate-700 font-medium hover:border-blue-500 transition-all" data-destination="프랑스">
                        <span class="material-symbols-outlined">flag</span>
                        <p>프랑스</p>
                    </button>
                    <button onclick="selectDestination('이탈리아')" class="destination-btn flex h-12 shrink-0 items-center justify-center gap-x-3 rounded-xl bg-white border border-slate-200 px-6 text-slate-700 font-medium hover:border-blue-500 transition-all" data-destination="이탈리아">
                        <span class="material-symbols-outlined">flag</span>
                        <p>이탈리아</p>
                    </button>
                </div>
            </div>
            
            <!-- AI 추천 관광지 섹션 -->
            <div id="attractions-section" class="mb-10"></div>
            
            <!-- 추가 생성 버튼 -->
            <div class="text-center mb-16">
                <button onclick="addMoreAttractions()" class="inline-flex items-center gap-2 px-8 py-3 bg-white border-2 border-blue-500 text-blue-500 font-bold rounded-xl hover:bg-blue-50 transition-colors">
                    <span class="material-symbols-outlined">add</span>
                    추가 정보 보기
                </button>
            </div>
        </main>
    </div>
    
    <script>
        const destinationsData = {destinations_json};
        let currentDestination = '일본';
        let visibleCount = 2;
        
        function selectDestination(destination) {{
            currentDestination = destination;
            visibleCount = 2;
            
            // 버튼 스타일 업데이트
            document.querySelectorAll('.destination-btn').forEach(btn => {{
                if (btn.dataset.destination === destination) {{
                    btn.classList.remove('bg-white', 'border', 'border-slate-200', 'text-slate-700');
                    btn.classList.add('bg-blue-500', 'shadow-md', 'text-white');
                }} else {{
                    btn.classList.remove('bg-blue-500', 'shadow-md', 'text-white');
                    btn.classList.add('bg-white', 'border', 'border-slate-200', 'text-slate-700');
                }}
            }});
            
            renderAttractions();
        }}
        
        function renderAttractions() {{
            const section = document.getElementById('attractions-section');
            const data = destinationsData[currentDestination];
            const attractions = data.attractions.slice(0, visibleCount);
            
            let html = `
                <div class="flex flex-col gap-2 px-2 mb-8">
                    <h2 class="text-slate-900 text-2xl font-bold tracking-tight">${{currentDestination}}의 AI 추천 관광지</h2>
                    <p class="text-slate-600">${{data.description}}</p>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            `;
            
            attractions.forEach((attr, idx) => {{
                html += `
                    <div class="group bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all border border-slate-100">
                        <div class="relative h-64 overflow-hidden">
                            <div class="absolute inset-0 bg-gradient-to-br ${{attr.color}} flex items-center justify-center">
                                <span class="material-symbols-outlined text-white" style="font-size: 120px;">${{attr.icon}}</span>
                            </div>
                            <div class="absolute top-4 left-4 bg-blue-500 text-white px-3 py-1 rounded-lg shadow-lg flex items-center gap-1 text-xs font-bold">
                                <span class="material-symbols-outlined text-xs">auto_awesome</span> ${{attr.match}} 일치
                            </div>
                        </div>
                        <div class="p-6">
                            <div class="flex justify-between items-start mb-4">
                                <div>
                                    <h3 class="text-2xl font-bold text-slate-900">${{attr.name}}</h3>
                                    <p class="text-slate-500 font-medium">${{attr.subtitle}}</p>
                                </div>
                                <button class="p-2 rounded-full bg-slate-100 text-slate-600 hover:bg-blue-100 hover:text-blue-500 transition-colors">
                                    <span class="material-symbols-outlined">favorite</span>
                                </button>
                            </div>
                            <div class="bg-blue-50 rounded-xl p-4 border border-blue-100 mb-4">
                                <p class="text-blue-600 text-sm font-bold flex items-center gap-1 mb-2">
                                    <span class="material-symbols-outlined text-sm">psychology</span> AI 추천 이유
                                </p>
                                <p class="text-slate-700 text-sm leading-relaxed italic">
                                    "${{attr.reason}}"
                                </p>
                            </div>
                            <button class="w-full py-3 px-4 bg-white text-slate-900 font-bold rounded-xl border border-slate-200 hover:bg-blue-500 hover:text-white transition-colors">${{attr.buttonText}}</button>
                        </div>
                    </div>
                `;
            }});
            
            html += '</div>';
            section.innerHTML = html;
        }}
        
        function addMoreAttractions() {{
            const data = destinationsData[currentDestination];
            if (visibleCount < data.attractions.length) {{
                visibleCount += 2;
            }} else {{
                visibleCount = 2;
            }}
            renderAttractions();
        }}
        
        // 초기 렌더링
        renderAttractions();
    </script>
    </body></html>
    """
    return render_template_string(html_template)

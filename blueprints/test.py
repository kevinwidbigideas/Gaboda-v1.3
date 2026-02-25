"""
테스트 라우트 블루프린트
"""
import json
from flask import Blueprint, render_template_string
from utils import COMMON_HEAD, get_header

test_bp = Blueprint('test', __name__)

QUESTIONS = {
    1: {
        "title": "여행 준비 스타일을 알려주세요.",
        "question": "오늘은 Travis와 여행을 떠납니다.<br>당신은 누워서 핸드폰으로 여행지의 지도를 보고 있습니다.<br>당신의 지도 앱(구글 맵) 상태는 어떤가요?",
        "options": [
            {"text": "가야 할 곳들이 동선별로<br>핀과 메모로 빽빽하게 <br>저장되어 있다", "icon": "map"},
            {"text": "일단 유명한 곳 몇 개만 대충<br> 찍어둔 상태다", "icon": "location_on"}
        ]
    },
    2: {
        "title": "당신의 공항 도착 시간 스타일은?",
        "question": "이제 공항으로 가야해서 집을 나섭니다.<br>당신의 예정 도착시간은 언제인가요?",
        "options": [
            {"text": "어떤 변수가 생길지 모르니<br>최소 3시간 전에는 도착해야 <br>안심된다", "icon": "flight"},
            {"text": "면세 쇼핑 계획이 없다면 <br>2시간 전에도 충분하다", "icon": "schedule"}
        ]
    },
    3: {
        "title": "당신이 선택한 숙소의 기준은?",
        "question": "비행기 타느라 너무 고생하셨어요!<br>눈 앞에 당신이 고른 숙소가 보이네요.<br>이번에 여행의 숙소를 고를 때 가장 중요한 기준은 무엇이었나요?",
        "options": [
            {"text": "동선 낭비없는 최적의 위치와<br> 편리한 교통편", "icon": "hotel"},
            {"text": "위치가 조금 멀더라도 숙소<br> 자체의 무드와 특별한 감성", "icon": "mood"}
        ]
    },
    4: {
        "title": "당신의 못 드시는 음식을 알려주세요.",
        "question": "Travis가 근처 식당을 예약하기 전에 확인할 것이 있다네요.<br>당신의 '이건 절대 못 먹겠어!'는 무엇인가요?",
        "options": [
            {"text": "고수, 오이, 마라 등<br> 기피 음식이 있다", "icon": "restaurant", "custom_ui": "food_restriction"},
            {"text": "전 아무거나 잘 먹는걸요!", "icon": "done"}
        ]
    },
    5: {
        "title": "당신의 여행 밀도는?",
        "question": "근처 식당에서 맛있는 점심 식사 후, 잠시 숙소로 돌아왔어요.<br>당신의 다음 행동은 무엇인가요?",
        "options": [
            {"text": "밥 먹었으니 여행 시작해야지!<br>놀러왔으니 바로 출발한다.", "icon": "explore"},
            {"text": "잠시만 침대에서 쉬었다가 갈래.<br>비행기도 탔고 배도 부르니까.", "icon": "hotel"}
        ]
    },
    6: {
        "title": "당신의 도시 탐험 스타일은?",
        "question": "본격적인 도시 탐험!<br>Travis가 당신의 체력을 고려해서 루트를 짜주려해요.<br>당신이 받은 루트는?",
        "options": [
            {"text": "많은 이동수단이 포함된<br>최소한의 도보 루트<br>: 평소에 운동을 거의 하지 않아서<br>추천했어요.", "icon": "local_taxi"},
            {"text": "최소한의 이동수단이 포함된<br>짧은 도보 루트<br>: 평소에 산책 등은 꾸준히<br>하셔서 추천했어요.", "icon": "directions_walk"},
            {"text": "도보로만 이루어진<br>1시간 정도의 도보 루트<br>: 주 1회에서 3회 정도 운동을<br>하시는 것 같아서 추천했어요.", "icon": "directions_run"},
            {"text": "골목 골목 도보로 둘러보는<br>2시간 정도의 도보 루트<br>: 거의 매일 운동을 하시는 것<br>같아서 추천했어요.", "icon": "hiking"}
        ]
    },
    7: {
        "title": "당신이 흥미를 느끼는 포인트는?",
        "question": "Travis와 도심 탐험을 하는 지금, 당신의 관심은 주로 어디에 있나요?",
        "options": [
            {"text": "눈앞의 선명한 색감, 거리의 <br>소음, 맛있는 냄새 등 오감을 <br>온전히 즐긴다", "icon": "visibility"},
            {"text": "이 풍경이 주는 영감과 내가<br> 지금 여기서 느끼는 상념에 <br>젖어든다", "icon": "light_mode"}
        ]
    },
    8: {
        "title": "당신의 돌발상황 대처방법은?",
        "question": "아뿔사, 정신없이 구경하다보니 길을 잃었습니다.<br>당신은 이런 상황에서 어떻게 대처하죠?",
        "options": [
            {"text": "주변에 도움을 청할<br>사람이 있나 찾아본다", "icon": "people"},
            {"text": "구글 맵을 다시 켜고 스스로 <br>길을 찾아낼 때까지 집중한다", "icon": "map"}
        ]
    },
    9: {
        "title": "당신이 흥미를 느끼는 포인트는?",
        "question": "다행히 길을 찾아서 목적지인 랜드마크에 도착했습니다.<br>Travis가 랜드마크에 대해 설명을 해준다고 하네요.<br>어떤 이야기에 더 끌리나요?",
        "options": [
            {"text": "이 건물의 정확한 제작 연도와<br>독특한 건축 양식의 디테일한 정보", "icon": "info"},
            {"text": "이 장소에 얽힌 비극적인<br>전설이나 시대적 배경이 주는<br>드라마틱한 서사", "icon": "history"}
        ]
    },
    10: {
        "title": "구경을 했다보니 또 배가 고프네요!",
        "question": "Travis가 추천한 식당 중에 이 식당을 선택하셨는데요.<br>당신이 이 식당을 선택한 이유는 무엇인가요?",
        "options": [
            {"text": "리뷰로 검증된 음식사진이<br>맛있어 보이는 실패없는 핫플이라서", "icon": "star"},
            {"text": "현지인들이 갈 것 같은 골목의<br>숨겨진 노포 같은 느낌이<br>주는 이끌림 때문에", "icon": "favorite"}
        ]
    },
    11: {
        "title": "당신의 의사결정에서 '효율'에 무게는?",
        "question": "식당에 도착하니 줄이 2시간이나 된다고 하네요.<br>같이 온 동행자와 논의해야 할 것 같아요.<br>당신의 의견은?",
        "options": [
            {"text": "2시간을 여기서 쓰는 건<br>비효율적이야. 다른 식당들도<br>많을테니 다른 대안을 찾아보자.", "icon": "task_alt"},
            {"text": "이것도 나름 여행의 추억이고,<br>기껏 찾아왔으니 기다리는 것도<br>나쁘지 않을 것 같아.", "icon": "favorite_border"}
        ]
    },
    12: {
        "title": "저녁 시간에 당신이 더 끌리는 분위기는?",
        "question": "하루종일 돌아다니다 보니 벌써 어두워졌네요.<br>벌써 8시가 넘었어요. 주위의 로컬 펍에서 활기찬 음악 소리가 들릴 때 당신의 속마음은?",
        "options": [
            {"text": "첫날인데! 현지의 느낌 가득한<br>펍에서 낯선 사람과도 어울려<br>놀 수 있는 그 분위기에 합류하고 싶다.", "icon": "celebration"},
            {"text": "첫날인데 너무 힘들었어.<br>숙소에서 조용히 맥주 한 캔하며<br>여유롭게 하루를 정리하고 싶어.", "icon": "nights_stay"}
        ]
    },
    13: {
        "title": "당신의 음주 성향은?",
        "question": "술 얘기가 나와서 그런데 궁금하네요. 당신은 여행가면 술을 즐기시는 편인가요?",
        "options": [
            {"text": "필수 - 여행의 밤은 역시 술이지!<br>현지의 술을 잔뜩 마시고 가고 싶어!", "icon": "celebration"},
            {"text": "선택 - 분위기에 따라<br>한 잔 정도면 충분해요.<br>필수는 아니에요", "icon": "local_bar"},
            {"text": "불호 - 잘 마시지도 못하고<br>맛없는 술보다는 맛있는<br>음료나 디저트가 더 좋아.", "icon": "local_drink"}
        ]
    },
    14: {
        "title": "내일을 정하는 당신의 타이밍은?",
        "question": "여행 첫날 밤이네요.<br>침대의 눈을 감으니 오늘 있었던 일과 내일의 일정에 대한 생각이 나요.<br>내일 일정에 대한 결정은 다 되어있나요?",
        "options": [
            {"text": "이미 한국에서 출발 전<br>시간 단위로 꼼꼼하게 다 짜왔잖아!", "icon": "checklist"},
            {"text": "대략적인 장소는 있어도 내일 아침의<br>기분과 창밖의 날씨를 보고 결정할거야!", "icon": "cloud"}
        ]
    },
    15: {
        "title": "당신의 대처 방식은?",
        "question": "호텔 조식을 먹고 나와서 친구가 Travis에게 추천받은 카페로 왔어요.<br>그런데 이런! 가게의 재료소진으로 일찍 문을 닫아버렸네요.",
        "options": [
            {"text": "걱정마! 근처에 비슷한 분위기의<br>별점 높은 곳이 있으니 그쪽으로 가보자.", "icon": "lightbulb"},
            {"text": "아이고, 진짜 아쉽겠다...<br>기대 많이 했을텐데.<br>다른 가고 싶은 곳이 또 있어?", "icon": "sentiment_satisfied"}
        ]
    },
    16: {
        "title": "이 상황에서 당신의 판단은?",
        "question": "친구와 시내를 둘러보기 위해 이동하던 중, 친구가 물었어요.<br>\"전에 내가 체력을 고려하지 못하고 일정을 짜서 힘들었던 부모님이<br> 남은 일정을 취소하면 안되냐고 물었었어. 그 때 너였다면 어떻게 대답했을까?\"",
        "options": [
            {"text": "죄송해요. 상황을 분석해서<br>이동과 도보를 최소화한<br>다른 효율적인 동선을 짜볼게요.", "icon": "construction"},
            {"text": "무리하게 계획을 짠 건 아닌지<br>너무 죄송하네요...오늘은 여기까지만<br>보고 들어가서 쉴까요?", "icon": "healing"}
        ]
    },
    17: {
        "title": "당신의 갈등 해결 방식은?",
        "question": "시내도 둘러보고 마지막으로 공항에 가기전에 둘러보고 싶은 곳이 있는데<br> 친구와의 의견차이가 도저히 좁혀지질 않네요.<br>생각을 정리하고 당신이 친구에게 제안을 합니다.",
        "options": [
            {"text": "그냥 서로 보고싶은 것이 다르니까<br>효율적으로 2시간 각자 보고<br>다시 만나는 건 어때?", "icon": "schedule"},
            {"text": "서운하지 않게 조금씩 양보해서<br>최대한 같이 움직일 수 있는<br>곳을 찾아볼까?", "icon": "handshake"}
        ]
    },
    18: {
        "title": "당신의 기념품 선택 기준은?",
        "question": "여행을 마치기 전, 기념품 샵에서 마지막 선물을<br> 고르는 당신의 기준은?",
        "options": [
            {"text": "한국보다 얼마나 저렴한지,<br> 실생활에서 잘 쓸 수 있는<br> 물건인지 따져본다", "icon": "shopping_bag"},
            {"text": "여기서만 살 수 있어! 라는 <br>특별한 희소성과 장소의 <br>의미에 집중한다", "icon": "card_giftcard"}
        ]
    },
    19: {
        "title": "당신의 여행 만족 포인트는?",
        "question": "수속도 마치고 귀국 행 비행기에 탑승했어요.<br>너무 재미있었고 즐거운 여행이었어요.<br>Travis와 함께 한 여행, 어떤 부분이 마음에 드셨나요?",
        "options": [
            {"text": "아침부터 밤까지! 온 에너지를<br>쏟아붓는 '뽕을 뽑는'<br>꽉 찬 일정이어서 좋았어!", "icon": "bolt"},
            {"text": "하루 한 두 군데만 들리는<br>여유롭고 여백이 있는<br>일정이 마음에 들었어!", "icon": "spa"}
        ]
    }
}

@test_bp.route('/test', methods=['GET', 'POST'])
def test():
    """테스트 페이지"""
    questions_json = json.dumps(QUESTIONS)
    
    html_template = f"""
    <!DOCTYPE html><html><head>{COMMON_HEAD}<title>Testing MBTI</title></head>
    <body class="bg-slate-50 min-h-screen">
        <!-- 인트로 화면 -->
        <div id="intro-overlay" class="fixed inset-0 z-50 bg-white flex flex-col items-center justify-center transition-opacity duration-700 opacity-100 p-8">
            <div class="text-center space-y-6">
                <h1 id="intro-line-1" class="text-3xl md:text-5xl font-bold text-slate-800 leading-relaxed tracking-wide transition-opacity duration-700 opacity-0 transform translate-y-4">
                    <span class="text-blue-600">Travis</span>와 1박2일 여행을 통해,
                </h1>
                <h2 id="intro-line-2" class="text-2xl md:text-4xl font-medium text-slate-700 leading-relaxed tracking-wider transition-opacity duration-700 opacity-0 transform translate-y-4 delay-200">
                    당신의 <span class="text-blue-600 font-bold">TraVTI</span>, 여행 페르소나를 알아봐요!
                </h2>
            </div>
        </div>

        {get_header('test')}
        <!-- 메인 콘텐츠 (초기에는 숨김) -->
        <main id="main-content" class="pt-12 pb-20 px-6 opacity-0 transition-opacity duration-1000">
            <div class="max-w-5xl mx-auto">
                <!-- 진행 상황 표시 영역 -->
                <div class="mb-12">
                    <div class="flex justify-between items-end mb-4">
                        <div><span class="text-blue-500 font-bold text-sm" id="question-num">Question 01</span><h2 class="text-2xl font-bold mt-1" id="question-subtitle">어떤 여행 취향이든, 다 맞춰주니까</h2></div>
                        <!-- 현재 진행도 (X / 20) 표시 -->
                        <div class="text-sm text-slate-400"><span id="progress-num">1</span> / <span id="progress-max">20</span></div>
                    </div>
                    <!-- 진행 바 -->
                    <div class="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
                        <div class="bg-blue-500 h-full" id="progress-bar" style="width: 10%;"></div>
                    </div>
                </div>
                <!-- 질문 제목 -->
                <h1 class="text-3xl font-bold text-center mb-12" id="question-title">내가 선호하는 여행 스타일은?</h1>
                <!-- 선택지 버튼들 -->
                <div class="grid grid-cols-2 gap-4" id="options-container">
                </div>
                <!-- 이전 질문으로 이동 버튼 -->
                <div class="mt-16">
                    <button onclick="goPrev()" id="prev-btn" class="text-slate-400 font-semibold flex items-center gap-2 hover:text-slate-600 transition-colors">← 이전으로</button>
                </div>
            </div>
        </main>
        <!-- 테스트 페이지 스크립트 -->
        <script>
            const QUESTIONS = {questions_json};
            let answers = JSON.parse(localStorage.getItem('answers')) || [];
            let answerIndices = JSON.parse(localStorage.getItem('answer_indices')) || [];
            if (!Array.isArray(answerIndices)) {{ answerIndices = []; }}
            let currentQuestion = 1;

            // 페이지 로드 시 인트로 애니메이션 및 첫 번째 질문 표시
            window.addEventListener('load', function() {{
                // 인트로 화면 처리
                const introOverlay = document.getElementById('intro-overlay');
                const line1 = document.getElementById('intro-line-1');
                const line2 = document.getElementById('intro-line-2');
                const mainContent = document.getElementById('main-content');
                
                // 0.2초 후 첫 번째 줄 페이드 인 & 슬라이드 업
                setTimeout(() => {{
                    line1.classList.remove('opacity-0', 'translate-y-4');
                    line1.classList.add('opacity-100', 'translate-y-0');
                }}, 200);

                // 0.8초 후 두 번째 줄 페이드 인 & 슬라이드 업
                setTimeout(() => {{
                    line2.classList.remove('opacity-0', 'translate-y-4');
                    line2.classList.add('opacity-100', 'translate-y-0');
                }}, 800);

                // 2.5초 후 전체 화면 페이드아웃 및 메인 컨텐츠 표시
                setTimeout(() => {{
                    introOverlay.classList.remove('opacity-100');
                    introOverlay.classList.add('opacity-0');
                    
                    // 인트로가 사라지기 시작할 때 메인 컨텐츠 페이드 인
                    setTimeout(() => {{
                        mainContent.classList.remove('opacity-0');
                        mainContent.classList.add('opacity-100');
                    }}, 200);
                    
                    // 페이드아웃 완료 후 요소 제거
                    setTimeout(() => {{
                        introOverlay.style.display = 'none';
                    }}, 700);
                }}, 2500);

                displayQuestion(currentQuestion);
            }});

            // 질문 표시 함수
            function displayQuestion(qNum) {{
                const question = QUESTIONS[qNum];
                document.getElementById('question-num').textContent = 'Question ' + String(qNum).padStart(2, '0');
                document.getElementById('question-subtitle').textContent = question.title;
                document.getElementById('question-title').innerHTML = question.question;
                document.getElementById('progress-num').textContent = qNum;
                document.getElementById('progress-max').textContent = '19';
                document.getElementById('progress-bar').style.width = (qNum / 19 * 100) + '%';
                

                
                // 선택지 버튼 생성 또는 텍스트 입력창 생성
                const optionsContainer = document.getElementById('options-container');
                optionsContainer.innerHTML = '';
                
                if (question.type === 'text') {{
                    // 주관식 입력 - 컨테이너를 flex로 중앙정렬
                    optionsContainer.className = 'flex justify-center';
                    
                    const inputDiv = document.createElement('div');
                    inputDiv.className = 'flex flex-col gap-4 w-full max-w-md';
                    
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.id = 'text-answer';
                    input.placeholder = question.placeholder;
                    input.className = 'w-full px-4 py-3 border-2 border-slate-200 rounded-lg focus:outline-none focus:border-blue-500';
                    
                    const submitBtn = document.createElement('button');
                    submitBtn.textContent = '답변 제출';
                    submitBtn.className = 'bg-blue-500 text-white font-bold py-3 px-6 rounded-lg hover:bg-blue-600 transition-colors w-full';
                    submitBtn.onclick = () => {{
                        const textAnswer = document.getElementById('text-answer').value.trim();
                        if (textAnswer) {{
                            selectOption(null, textAnswer);
                        }} else {{
                            alert('도시와 이유를 입력해주세요.');
                        }}
                    }};
                    
                    inputDiv.appendChild(input);
                    inputDiv.appendChild(submitBtn);
                    optionsContainer.appendChild(inputDiv);
                }} else {{
                    // 객관식 선택지
                    optionsContainer.className = 'grid grid-cols-2 gap-4';
                    question.options.forEach((option, idx) => {{
                        const button = document.createElement('button');
                        const isSelected = qNum === 19 && answerIndices[currentQuestion - 1] === idx;
                        
                        // onclick 핸들러
                        button.onclick = () => {{
                            if (option.custom_ui === 'food_restriction') {{
                                showComplexFoodUI(button, idx, option.text, qNum);
                            }} else if (option.input_required) {{
                                showInputForOption(button, idx, option.text, qNum);
                            }} else {{
                                selectOptionWithButton(button, idx, option.text, qNum);
                            }}
                        }};

                        button.className = 'bg-white p-8 rounded-3xl border-2 ' + 
                            (isSelected ? 'border-blue-500 border-4' : 'border-transparent') + 
                            ' hover:border-blue-200 shadow-sm flex flex-col items-center transition-all cursor-pointer';
                        button.setAttribute('data-option-idx', idx);
                        
                        // 원본 HTML 저장
                        const originalHtml = `
                            <div class="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mb-4 text-blue-500"><span class="material-symbols-outlined text-4xl">${{option.icon}}</span></div>
                            <h3 class="text-xl font-bold">${{option.text.replace(/\\n/g, '<br>')}}</h3>
                        `;
                        button.innerHTML = originalHtml;
                        button.setAttribute('data-original-html', originalHtml);
                        
                        optionsContainer.appendChild(button);
                    }});
                    
                    // 질문 19번인 경우 답변 제출 버튼 추가

                }}
            }}

            // 옵션 선택 함수 (일반 질문용)
            function selectOption(optionIdx, optionText) {{
                // 답변 저장
                answers[currentQuestion - 1] = optionText;
                answerIndices[currentQuestion - 1] = optionIdx;
                localStorage.setItem('answers', JSON.stringify(answers));
                localStorage.setItem('answer_indices', JSON.stringify(answerIndices));
                
                // 다음 질문 표시
                currentQuestion++;
                displayQuestion(currentQuestion);
            }}

            // 옵션 선택 함수 (질문 19번용 - 하이라이트 효과)
            function selectOptionWithButton(button, optionIdx, optionText, qNum) {{
                // 답변 저장
                answers[currentQuestion - 1] = optionText;
                answerIndices[currentQuestion - 1] = optionIdx;
                localStorage.setItem('answers', JSON.stringify(answers));
                localStorage.setItem('answer_indices', JSON.stringify(answerIndices));
                
                if (qNum === 19) {{
                    submitAnswers();
                }} else {{
                    // 질문 19번이 아닌 경우 자동으로 다음 질문으로 이동
                    currentQuestion++;
                    displayQuestion(currentQuestion);
                }}
            }}


            let currentRestrictions = [];

            // Complex Food UI
            function showComplexFoodUI(button, idx, originalText, qNum) {{
                const container = document.getElementById('options-container');
                
                // Fade out
                container.style.transition = 'opacity 0.2s';
                container.style.opacity = '0';
                
                setTimeout(() => {{
                    // Change layout to single column
                    container.className = 'w-full max-w-2xl mx-auto';
                    
                    // Render Full UI
                    container.innerHTML = `
                         <div id="food-restriction-container" class="bg-white rounded-3xl p-8 shadow-sm border border-slate-200">
                            <h3 class="text-xl font-bold text-center mb-6">${{originalText.replace(/\\n/g, ' ')}}</h3>
                            
                            <!-- Input Area -->
                            <div class="flex gap-2 mb-4">
                                <input type="text" id="food-name" class="flex-grow px-4 py-3 border rounded-xl text-black focus:outline-none focus:border-blue-500" placeholder="음식/재료명 (예: 오이)">
                                <select id="food-reason" class="w-32 px-4 py-3 border rounded-xl text-black focus:outline-none focus:border-blue-500">
                                    <option value="취향">취향</option>
                                    <option value="알러지">알러지</option>
                                    <option value="종교">종교</option>
                                    <option value="신념">신념</option>
                                    <option value="기타">기타</option>
                                </select>
                                <button type="button" onclick="addRestrictionItem()" class="bg-blue-500 text-white px-6 py-3 rounded-xl font-bold shrink-0 hover:bg-blue-600 transition-colors">추가</button>
                            </div>

                            <!-- List Area -->
                            <div id="restriction-list" class="flex flex-col gap-2 min-h-[100px] max-h-[300px] overflow-y-auto bg-slate-50 rounded-xl p-4 border border-slate-100 mb-6">
                                <div class="flex-grow flex items-center justify-center text-sm text-slate-400">추가된 항목이 없습니다.</div>
                            </div>

                            <div class="flex gap-3">
                                <button type="button" onclick="displayQuestion(${{qNum}})" class="w-1/3 bg-slate-100 text-slate-600 py-4 rounded-xl font-bold hover:bg-slate-200 transition-colors">
                                    취소 (뒤로)
                                </button>
                                <button type="button" onclick="submitComplexFood(${{idx}}, '${{originalText}}', ${{qNum}})" class="w-2/3 bg-slate-900 text-white py-4 rounded-xl font-bold hover:bg-slate-800 transition-colors">
                                    확인 (다음으로)
                                </button>
                            </div>
                        </div>
                    `;
                    
                    // Fade in
                    container.style.opacity = '1';
                    
                    currentRestrictions = [];
                    renderRestrictionList();
                    
                    // Focus input
                    setTimeout(() => {{
                        const input = document.getElementById('food-name');
                        if(input) {{
                            input.focus(); 
                            input.onkeydown = (e) => {{
                                if(e.key === 'Enter') addRestrictionItem();
                            }};
                        }}
                    }}, 100);
                    
                }}, 200);
            }}

            function addRestrictionItem() {{
                const nameInput = document.getElementById('food-name');
                const reasonInput = document.getElementById('food-reason');
                const name = nameInput.value.trim();
                const reason = reasonInput.value;

                if (!name) return alert('음식 이름을 입력해주세요.');
                
                currentRestrictions.push({{ name, reason }});
                nameInput.value = '';
                nameInput.focus();
                renderRestrictionList();
            }}

            function removeRestrictionItem(idx) {{
                currentRestrictions.splice(idx, 1);
                renderRestrictionList();
            }}

            function renderRestrictionList() {{
                const listEl = document.getElementById('restriction-list');
                if (!listEl) return;
                
                if (currentRestrictions.length === 0) {{
                    listEl.innerHTML = '<div class="flex-grow flex items-center justify-center text-sm text-slate-400">추가된 항목이 없습니다.</div>';
                    return;
                }}

                listEl.innerHTML = currentRestrictions.map((item, idx) => `
                    <div class="flex items-center justify-between bg-white px-3 py-2 rounded shadow-sm border border-slate-200">
                        <div class="flex flex-col leading-tight">
                            <span class="font-bold text-slate-800 text-sm text-left">${{item.name}}</span>
                            <span class="text-[10px] text-slate-500 text-left">${{item.reason}}</span>
                        </div>
                        <button onclick="removeRestrictionItem(${{idx}})" class="text-red-400 hover:text-red-600 font-bold px-2">×</button>
                    </div>
                `).join('');
            }}

            function submitComplexFood(idx, originalText, qNum) {{
                if (currentRestrictions.length === 0) {{
                    alert('제한 식단을 최소 1개 입력하거나, 제한이 없다면 다른 보기를 선택해주세요.');
                    return;
                }}
                
                const details = currentRestrictions.map(r => `${{r.name}}[${{r.reason}}]`).join(', ');
                const finalText = originalText.replace(/<br>/g, ' ') + ' (' + details + ')';
                
                selectOptionWithButton(null, idx, finalText, qNum);
            }}

            // 입력 옵션 보여주기 함수 (Old)
            function showInputForOption(button, idx, originalText, qNum) {{
                // 이미 입력 모드면 리턴
                if (button.querySelector('input')) return;
                
                // 다른 모든 버튼 원복
                const allButtons = document.querySelectorAll('[data-option-idx]');
                allButtons.forEach(btn => {{
                    const origHtml = btn.getAttribute('data-original-html');
                    if (origHtml) {{
                        btn.innerHTML = origHtml;
                        btn.className = btn.className.replace('border-blue-500 border-4', 'border-transparent');
                    }}
                }});
                
                // 현재 버튼 하이라이트
                button.className = button.className.replace('border-transparent', 'border-blue-500 border-4');
                
                // 입력 폼으로 교체
                button.innerHTML = `
                    <div class="flex flex-col items-center w-full gap-3" onclick="event.stopPropagation()">
                        <h3 class="text-lg font-bold">${{originalText.replace(/\\n/g, ' ')}}</h3>
                        <input type="text" id="option-input-${{idx}}" class="w-full px-3 py-2 border rounded text-black bg-slate-50 focus:outline-none focus:border-blue-500" placeholder="기피 음식을 입력해주세요">
                        <button id="btn-confirm-${{idx}}" type="button" class="bg-blue-500 text-white px-6 py-2 rounded-lg font-bold hover:bg-blue-600 transition-colors cursor-pointer text-sm">확인</button>
                    </div>
                `;
                
                // 이벤트 바인딩 지연 실행
                setTimeout(() => {{
                    const confirmBtn = document.getElementById(`btn-confirm-${{idx}}`);
                    const input = document.getElementById(`option-input-${{idx}}`);
                    if (confirmBtn) {{
                        confirmBtn.onclick = (e) => {{
                            e.preventDefault();
                            e.stopPropagation();
                            submitInputOption(idx, originalText, qNum);
                        }};
                    }}
                    if (input) {{
                         input.onkeydown = (e) => {{
                            if (e.key === 'Enter') {{
                                e.preventDefault();
                                e.stopPropagation();
                                submitInputOption(idx, originalText, qNum);
                            }}
                        }};
                        input.focus();
                    }}
                }}, 0);
            }}
            
            // 입력 제출 처리 (Old)
            function submitInputOption(idx, originalText, qNum) {{
                const input = document.getElementById(`option-input-${{idx}}`);
                const value = input.value.trim();
                
                if (!value) {{
                    alert('내용을 입력해주세요.');
                    return;
                }}
                
                // 저장될 텍스트: "옵션명 (입력값)"
                const finalText = originalText.replace(/<br>/g, ' ') + ' (' + value + ')';
                selectOptionWithButton(null, idx, finalText, qNum);
            }}

            // 답변 제출 함수 (질문 19번 이후)
            // 답변 제출 함수 (질문 19번 이후)
            // 답변 제출 함수 (질문 19번 이후)
            function submitAnswers() {{
                // 로딩 표시
                const overlay = document.getElementById('intro-overlay');
                if(overlay) {{
                    overlay.innerHTML = '<div class="text-2xl font-bold text-slate-800">TraVTI 분석 중...</div>';
                    overlay.style.display = 'flex';
                    // Force reflow
                    void overlay.offsetWidth; 
                    overlay.classList.remove('opacity-0');
                    overlay.classList.add('opacity-100');
                }}

                console.log('Submitting answers...', {{ answers: answers, answer_indices: answerIndices }});
                
                fetch('/submit-answers', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ answers: answers, answer_indices: answerIndices }})
                }})
                .then(response => {{
                    console.log('Response status:', response.status);
                    return response.json();
                }})
                .then(data => {{
                    console.log('Response data:', data);
                    if (data.redirect) {{
                        if (data.survey_id) {{
                            localStorage.setItem('travTRVUserId', data.survey_id);
                        }}
                        localStorage.removeItem('answers');
                        localStorage.removeItem('answer_indices');
                        window.location.href = data.redirect;
                    }} else {{
                        alert('결과 제출 실패: ' + (data.error || '알 수 없는 오류'));
                        if(overlay) {{
                            overlay.style.display = 'none';
                        }}
                    }}
                }})
                .catch(err => {{
                    console.error('Error submitting answers:', err);
                    alert('서버 통신 오류: ' + err.message);
                    if(overlay) {{
                        overlay.style.display = 'none';
                    }}
                }});
            }}

            // 이전 질문으로 이동
            function goPrev() {{
                if (currentQuestion > 1) {{
                    currentQuestion--;
                    displayQuestion(currentQuestion);
                }} else {{
                    window.location.href = '/';
                }}
            }}
        </script>
    </body></html>
    """
    
    return render_template_string(html_template)

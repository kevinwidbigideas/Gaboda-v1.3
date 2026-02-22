from flask import Flask, render_template_string, request, redirect, url_for, session, g
import json
import sqlite3
import os
import time
from datetime import datetime
import joblib
import pandas as pd

# Flask 앱 초기화
app = Flask(__name__)
# 세션 데이터를 암호화하기 위한 시크릿 키 설정
app.secret_key = "gaboda_secret"

# ========================================
# DB config (avoid OneDrive locks)
# ========================================
DB_PATH = r"C:\temp\travis.db"

def ensure_db_path():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_db():
    if 'db' not in g:
        ensure_db_path()
        g.db = sqlite3.connect(
            DB_PATH,
            timeout=60.0,
            isolation_level=None,
            check_same_thread=False
        )
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.execute('PRAGMA synchronous=NORMAL')
        g.db.execute('PRAGMA busy_timeout=10000')
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass

def init_db():
    ensure_db_path()
    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA busy_timeout=10000')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS survey_responses (
            ID TEXT PRIMARY KEY,
            Base_MBTI TEXT,
            Actual_Label TEXT,
            TraVTI_Label TEXT,
            TraVTI_Vector TEXT,
            Score_EI REAL,
            Score_SN REAL,
            Score_TF REAL,
            Score_JP REAL,
            Stamina REAL,
            Alcohol REAL,
            Q1 TEXT, Q2 TEXT, Q3 TEXT, Q4 TEXT, Q5 TEXT,
            Q6 TEXT, Q7 TEXT, Q8 TEXT, Q9 TEXT, Q10 TEXT,
            Q11 TEXT, Q12 TEXT, Q13 TEXT, Q14 TEXT, Q15 TEXT,
            Q16 TEXT, Q17 TEXT, Q18 TEXT, Q19 TEXT, Q20 TEXT,
            Q1_Val REAL, Q2_Val REAL, Q3_Val REAL, Q4_Val REAL, Q5_Val REAL,
            Q6_Val REAL, Q7_Val REAL, Q8_Val REAL, Q9_Val REAL, Q10_Val REAL,
            Q11_Val REAL, Q12_Val REAL, Q13_Val REAL, Q14_Val REAL, Q15_Val REAL,
            Q16_Val REAL, Q17_Val REAL, Q18_Val REAL, Q19_Val REAL, Q20_Val TEXT
        )
    ''')
    conn.close()

def generate_next_id():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT MAX(ID) FROM survey_responses')
    row = cursor.fetchone()
    result = row[0] if row else None
    if result is None:
        next_num = 1000
    else:
        try:
            current_num = int(result.split('-')[-1])
            next_num = current_num + 1
        except Exception:
            next_num = 1000
    return f"TRV-NEW-{next_num}"

# ========================================
# 공통 HTML 헤더 (모든 페이지에서 사용)
# ========================================
# 메타 정보, 폰트, 아이콘, Tailwind CSS 등을 포함
COMMON_HEAD = """
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700;800;900&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,typography,container-queries"></script>
<style>body { font-family: 'Pretendard', sans-serif; }</style>
"""

# ========================================
# 공통 네비게이션 헤더 함수
# ========================================
def get_header(current_page):
    """현재 페이지에 따른 네비게이션 헤더 반환"""
    pages = {
        'home': '/',
        'test': '/test',
        'result': '/result',
        'group': '/group-recommendation'
    }
    
    nav_html = f"""
    <!-- 헤더 -->
    <header class="sticky top-0 z-50 border-b border-slate-200 bg-white">
        <div class="flex items-center justify-between w-full px-6 md:px-10 py-4">
            <div class="flex items-center gap-8 max-w-3xl mx-auto w-full px-6">
                <a href="/" class="flex items-center gap-3 text-blue-500 cursor-pointer hover:opacity-80 transition-opacity">
                    <div class="size-8 flex items-center justify-center bg-blue-500 rounded-lg text-white font-bold">G</div>
                    <h2 class="text-slate-900 text-xl font-extrabold">Travis</h2>
                </a>
                <nav class="hidden md:flex items-center gap-8">
                    <a class="text-slate-600 text-sm font-semibold hover:text-blue-500 transition-colors {'text-blue-500 border-b-2 border-blue-500 py-1' if current_page == 'test' else ''}" href="/test">내 MBTI</a>
                    <a class="text-slate-600 text-sm font-semibold hover:text-blue-500 transition-colors {'text-blue-500 border-b-2 border-blue-500 py-1' if current_page == 'result' else ''}" href="/result">AI 여행지 추천</a>
                </nav>
            </div>
        </div>
    </header>
    """
    return nav_html

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

# ========================================
# 페이지 1: 메인 랜딩 페이지
# ========================================
@app.route('/')
def index():
    # 메인 페이지를 렌더링 (TRIP MBTI 소개)
    return render_template_string(f"""
    <!DOCTYPE html><html><head>{COMMON_HEAD}<title>TRIP MBTI</title></head>
    <body class="bg-white">
        {get_header('home')}
        <!-- 메인 콘텐츠 -->
        <main class="pt-20 pb-20 px-6 max-w-3xl mx-auto grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            <!-- 왼쪽: 텍스트 영역 -->
            <div class="space-y-6">
                <h1 class="text-4xl lg:text-5xl font-extrabold leading-[3rem] lg:leading-[4rem] tracking-tight">어떤 취향이든,<br><span class="text-blue-500">다 맞춰주니까</span></h1>
                <p class="text-base lg:text-lg text-slate-500">Travis는 여러분의 취향에 꼭 맞는 일정을<br>추천해 드립니다.</p>
                <!-- 테스트 시작 버튼 -->
                <a href="/test" class="inline-block bg-blue-500 text-white font-bold py-4 px-10 rounded-full text-lg shadow-lg hover:scale-105 transition-transform">여행성향 알아보기</a>
            </div>
            <!-- 오른쪽: 이미지/카드 영역 -->
            <div class="relative flex justify-end">
                <div class="w-80 h-[480px] bg-white rounded-[2.5rem] shadow-2xl p-8 flex flex-col items-center border border-slate-100">
                    <div class="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-8 mt-10"><span class="material-icons-outlined text-3xl text-slate-400">photo_camera</span></div>
                    <h3 class="text-xl font-bold text-center mb-10">내가 선호하는 여행 스타일은?</h3>
                    <div class="w-full space-y-3">
                        <div class="w-full py-3 px-6 rounded-full border-2 border-blue-500 text-blue-500 font-semibold text-center bg-blue-50">SNS 핫플레이스</div>
                        <div class="w-full py-3 px-6 rounded-full border-2 border-blue-500 text-blue-500 font-semibold text-center bg-blue-50">여유롭게 힐링</div>
                    </div>
                </div>
            </div>
        
        
</main>

        
    </body></html>
    """)

# ========================================
# 페이지 2: MBTI 테스트 페이지
# ========================================
@app.route('/test', methods=['GET', 'POST'])
def test():
    # 테스트 질문 데이터 정의
    questions = {
        1: {
            "title": "당신의 지도 앱(구글 맵) 상태는 어떤가요?",
            "subtitle": "여행 준비 스타일을 알려주세요",
            "options": [
                {"text": "가야 할 곳들이 동선별로 핀과 메모로 빽빽하게 저장되어 있다", "icon": "map"},
                {"text": "일단 유명한 곳 몇 개만 대충 찍어둔 상태다", "icon": "location_on"}
            ]
        },
        2: {
            "title": "이제 공항으로 가야죠. 언제쯤 도착하실 예정인가요?",
            "subtitle": "당신의 공항 도착 시간 스타일은?",
            "options": [
                {"text": "어떤 변수가 생길지 모르니 최소 3시간 전에는 도착해야 안심된다", "icon": "flight"},
                {"text": "면세 쇼핑 계획이 없다면 1.5~2시간 전에도 충분하다", "icon": "schedule"}
            ]
        },
        3: {
            "title": "이번 여행의 숙소를 고를 때 가장 중요했던 기준은 무엇이었나요?",
            "subtitle": "당신의 숙소 선택 기준은?",
            "options": [
                {"text": "동선 낭비가 없는 최적의 위치와 편리한 교통편", "icon": "hotel"},
                {"text": "위치가 조금 멀더라도 숙소 자체의 무드와 특별한 감성", "icon": "mood"}
            ]
        },
        4: {
            "title": "식당 예약 전 체크할게요. 이건 절대 못 드시죠?",
            "subtitle": "당신의 음식 기피 사항을 선택해주세요",
            "options": [
                {"text": "고수, 오이, 마라, 해산물 등 기피 음식이 있다", "icon": "restaurant"},
                {"text": "특별히 기피하는 음식이 없다", "icon": "done"}
            ]
        },
        5: {
            "title": "만족스러운 점심 식사 후, 당신의 본능이 이끄는 첫 행동은?",
            "subtitle": "당신의 여행 에너지는?",
            "options": [
                {"text": "에너지가 올라왔어요! 새로운 동네가 궁금하니 바로 탐험을 시작한다", "icon": "explore"},
                {"text": "배도 부르니 일단 숙소로 들어가 침대에 누워 잠시 숨을 돌린다", "icon": "hotel"}
            ]
        },
        6: {
            "title": "본격적인 도심 탐험! 오늘 당신의 보행 스타일은 어떤가요?",
            "subtitle": "당신의 체력 레벨은?",
            "options": [
                {"text": "저질체력 - 걷는 건 최소한으로! 택시가 제 여행의 동반자예요", "icon": "local_taxi"},
                {"text": "보통체력 - 걸을 수는 있지만 적당히 카페가 나오면 쉬어가야 해요", "icon": "directions_walk"},
                {"text": "좋은체력 - 땡볕에 걷는 것만 아니면 하루 종일도 오케이!", "icon": "hiking"},
                {"text": "강철체력 - 내 두 다리만 있다면 어디든 갈 수 있죠!", "icon": "directions_run"}
            ]
        },
        7: {
            "title": "거리를 걷는 지금, 당신의 시선은 주로 어디에 머무나요?",
            "subtitle": "당신의 관찰 스타일은?",
            "options": [
                {"text": "눈앞의 선명한 색감, 거리의 소음, 맛있는 냄새 등 오감을 온전히 즐긴다", "icon": "visibility"},
                {"text": "이 풍경이 주는 영감과 내가 지금 여기서 느끼는 상념에 젖어든다", "icon": "light_mode"}
            ]
        },
        8: {
            "title": "아뿔싸, 골목을 걷다 길을 잃었습니다. 어떡하죠?",
            "subtitle": "당신의 길 잃음 대처법은?",
            "options": [
                {"text": "당황하지 않고 주변 현지인에게 바로 말을 걸어 길을 묻는다", "icon": "people"},
                {"text": "구글 맵을 다시 켜고 스스로 길을 찾아낼 때까지 집중한다", "icon": "map"}
            ]
        },
        9: {
            "title": "가이드가 랜드마크 앞에서 설명을 시작합니다. 어떤 이야기에 더 끌리나요?",
            "subtitle": "당신의 정보 선호도는?",
            "options": [
                {"text": "이 건물의 정확한 제작 연도와 독특한 건축 양식의 디테일한 정보", "icon": "info"},
                {"text": "이 장소에 얽힌 비극적인 전설이나 시대적 배경이 주는 드라마틱한 서사", "icon": "history"}
            ]
        },
        10: {
            "title": "애써 찾아간 맛집! 당신은 이 식당을 왜 선택했었나요?",
            "subtitle": "당신의 선택 기준은?",
            "options": [
                {"text": "리뷰가 검증된 곳이자, 사진이 예쁘게 나와 실패 없는 핫플이라서", "icon": "star"},
                {"text": "왠지 모를 이끌림! 나만 아는 아지트 같은 숨은 노포의 느낌이라서", "icon": "favorite"}
            ]
        },
        11: {
            "title": "그런데 줄이 2시간이나 되네요! 동행자와 논의해야 합니다.",
            "subtitle": "당신의 의사결정 방식은?",
            "options": [
                {"text": "2시간을 여기서 다 쓰는 건 비효율적이야. 다른 대안을 찾아보자", "icon": "task_alt"},
                {"text": "기다리는 것도 여행의 추억 아닐까? 네가 원한다면 끝까지 기다려볼게", "icon": "favorite_border"}
            ]
        },
        12: {
            "title": "친구가 꼭 가고 싶어 했던 카페가 문을 닫았다면? 당신의 첫 마디는?",
            "subtitle": "당신의 대처 방식은?",
            "options": [
                {"text": "근처에 비슷한 분위기의 별점 높은 곳이 또 있어. 그리로 가자", "icon": "lightbulb"},
                {"text": "아이고, 진짜 아쉽겠다... 너 여기 정말 기대 많이 했을 텐데", "icon": "sentiment_satisfied"}
            ]
        },
        13: {
            "title": "함께 온 부모님이 다리가 아프다며 남은 일정을 취소하자고 하십니다.",
            "subtitle": "당신의 반응은?",
            "options": [
                {"text": "상황을 분석해서 이동을 최소화한 다른 효율적인 동선을 바로 짜볼게요", "icon": "construction"},
                {"text": "무리하게 계획을 짠 건 아닌지 죄송하네요. 오늘은 여기서 푹 쉬어요", "icon": "healing"}
            ]
        },
        14: {
            "title": "저녁 8시, 로컬 펍에서 활기찬 음악 소리가 들릴 때 당신의 마음은?",
            "subtitle": "당신의 저녁 선호도는?",
            "options": [
                {"text": "낯선 사람과도 기분 좋게 건배할 수 있는 그 분위기에 합류하고 싶다", "icon": "celebration"},
                {"text": "숙소에서 조용히 맥주 한 캔 하며 나만의 시간으로 하루를 정리하고 싶다", "icon": "nights_stay"}
            ]
        },
        15: {
            "title": "오늘 밤, 당신의 잔에는 무엇이 채워져 있나요?",
            "subtitle": "당신의 음주 성향은?",
            "options": [
                {"text": "필수 - 여행의 밤은 역시 술이지! 매일 밤 로컬 술을 즐기고 싶어요", "icon": "local_bar"},
                {"text": "선택 - 분위기에 따라 한 잔 정도면 충분해요. 필수는 아니에요", "icon": "coffee"},
                {"text": "불호 - 술보다는 맛있는 음료나 디저트를 즐기는 게 더 좋아요", "icon": "local_drink"}
            ]
        },
        16: {
            "title": "만약 동행자와 가고 싶은 곳이 달라 의견 차이가 생겼다면?",
            "subtitle": "당신의 갈등 해결 방식은?",
            "options": [
                {"text": "서로 시간 낭비하지 말고 2시간 각자 보고 다시 만나는 건 어때?", "icon": "schedule"},
                {"text": "서운하지 않게 조금씩 양보해서 최대한 같이 움직일 수 있는 곳을 찾아보자", "icon": "handshake"}
            ]
        },
        17: {
            "title": "여행을 마치기 전, 기념품 샵에서 마지막 선물을 고르는 당신의 기준은?",
            "subtitle": "당신의 선물 선택 기준은?",
            "options": [
                {"text": "한국보다 얼마나 저렴한지, 실생활에서 잘 쓸 수 있는 물건인지 따져본다", "icon": "shopping_bag"},
                {"text": "여기서만 살 수 있어! 라는 특별한 희소성과 장소의 의미에 집중한다", "icon": "card_giftcard"}
            ]
        },
        18: {
            "title": "내일 상세 일정을 최종적으로 확정하는 타이밍은 언제인가요?",
            "subtitle": "당신의 계획 수립 방식은?",
            "options": [
                {"text": "이미 한국에서 출발 전 시간 단위로 꼼꼼하게 다 짜왔다", "icon": "checklist"},
                {"text": "내일 아침의 기분과 창밖의 날씨를 보고 결정하고 싶다", "icon": "cloud"}
            ]
        },
        19: {
            "title": "이번 여행 전반에 걸쳐 당신이 꿈꾸는 속도는 어느 정도인가요?",
            "subtitle": "당신의 여행 페이스는?",
            "options": [
                {"text": "아침부터 밤까지! 온 에너지를 쏟아붓는 '뽕을 뽑는' 꽉 찬 일정", "icon": "bolt"},
                {"text": "하루 한두 군데만 봐도 충분해요. 여백이 있는 여유로운 일정", "icon": "spa"}
            ]
        },
        20: {
            "title": "가장 마음에 들었던 여행지는 어디인가요?",
            "subtitle": "마지막 질문입니다! 당신을 매료시킨 도시와 이유를 알려주세요.",
            "type": "text",
            "placeholder": "예) 교토 - 전통 일본 건축물의 오래된 감성"
        }

    }
    questions_json = json.dumps(questions)
    
    # 테스트 페이지 HTML 템플릿 (모든 질문을 JavaScript로 관리)
    html_template = f"""
    <!DOCTYPE html><html><head>{COMMON_HEAD}<title>Testing MBTI</title></head>
    <body class="bg-slate-50 min-h-screen">
        {get_header('test')}
        <!-- 메인 콘텐츠 -->
        <main class="pt-12 pb-20 px-6">
            <div class="max-w-2xl mx-auto">
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

            // 페이지 로드 시 첫 번째 질문 표시
            window.addEventListener('load', function() {{
                displayQuestion(currentQuestion);
            }});

            // 질문 표시 함수
            function displayQuestion(qNum) {{
                const question = QUESTIONS[qNum];
                document.getElementById('question-num').textContent = 'Question ' + String(qNum).padStart(2, '0');
                document.getElementById('question-subtitle').textContent = question.subtitle;
                document.getElementById('question-title').textContent = question.title;
                document.getElementById('progress-num').textContent = qNum;
                document.getElementById('progress-max').textContent = '20';
                document.getElementById('progress-bar').style.width = (qNum * 5) + '%';
                
                // 이전 버튼 활성화/비활성화
                const prevBtn = document.getElementById('prev-btn');
                if (qNum === 1) {{
                    prevBtn.style.color = '#cbd5e1';
                    prevBtn.style.pointerEvents = 'none';
                }} else {{
                    prevBtn.style.color = '#94a3b8';
                    prevBtn.style.pointerEvents = 'auto';
                }}
                
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
                        button.onclick = () => selectOption(idx, option.text);
                        button.className = 'bg-white p-8 rounded-3xl border-2 border-transparent hover:border-blue-200 shadow-sm flex flex-col items-center transition-all cursor-pointer';
                        button.innerHTML = `
                            <div class="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mb-4 text-blue-500"><span class="material-symbols-outlined text-4xl">${{option.icon}}</span></div>
                            <h3 class="text-xl font-bold">${{option.text}}</h3>
                        `;
                        optionsContainer.appendChild(button);
                    }});
                }}
            }}

            // 옵션 선택 함수
            function selectOption(optionIdx, optionText) {{
                // 답변 저장
                answers[currentQuestion - 1] = optionText;
                answerIndices[currentQuestion - 1] = optionIdx;
                localStorage.setItem('answers', JSON.stringify(answers));
                localStorage.setItem('answer_indices', JSON.stringify(answerIndices));
                
                // 모든 질문 완료 시 (20개 질문)
                if (currentQuestion === 20) {{
                    // 답변을 서버로 제출
                    fetch('/submit-answers', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ answers: answers, answer_indices: answerIndices }})
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.redirect) {{
                            localStorage.removeItem('answers');
                            localStorage.removeItem('answer_indices');
                            window.location.href = data.redirect;
                        }}
                    }});
                }} else {{
                    // 다음 질문 표시 (서버 호출 없음)
                    currentQuestion++;
                    displayQuestion(currentQuestion);
                }}
            }}

            // 이전 질문으로 이동
            function goPrev() {{
                if (currentQuestion > 1) {{
                    currentQuestion--;
                    displayQuestion(currentQuestion);
                }}
            }}
        </script>
    </body></html>
    """
    
    return render_template_string(html_template)

# ========================================
# API: 모든 답변 제출
# ========================================
@app.route('/submit-answers', methods=['POST'])
def submit_answers():
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

    # 스코어 계산: 인덱스 = Q번호 - 1
    # E/I: Q5[4], Q8[7], Q14[13], Q19[18] (weight Q19: 1.5)
    # S/N: Q7[6], Q9[8], Q10[9], Q17[16] (weight Q10: 1.5)
    # T/F: Q11[10], Q12[11], Q13[12], Q16[15] (weight Q13: 1.5)
    # J/P: Q1[0], Q2[1], Q3[2], Q18[17] (weight Q18: 1.5)
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
        # 메타데이터 로드 (컬럼 정보 확인)
        with open('rf_travel_model_metadata.json', 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # 모델 로드
        rf_model = joblib.load('rf_travel_model.joblib')
        
        # Q1~Q19 값 추출 (Q4_Val 제외)
        q_vals_for_pred = []
        for i in range(19):
            if i != 3:  # Q4_Val (인덱스 3) 제외
                q_vals_for_pred.append(q_vals_numeric[i])
        
        # DataFrame으로 변환 (컬럼 순서 일치)
        feature_df = pd.DataFrame([q_vals_for_pred], columns=metadata['feature_columns'])
        
        # 예측
        prediction = rf_model.predict(feature_df)[0]
        travti_label = prediction  # 예측 결과를 TraVTI_Label에 저장
    except Exception as e:
        print(f"모델 예측 오류: {e}")
        travti_label = None  # 모델 로드 실패 시 None 저장

    insert_query = "INSERT INTO survey_responses (ID, Base_MBTI, Actual_Label, TraVTI_Label, TraVTI_Vector, Score_EI, Score_SN, Score_TF, Score_JP, Stamina, Alcohol, Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10, Q11, Q12, Q13, Q14, Q15, Q16, Q17, Q18, Q19, Q20, Q1_Val, Q2_Val, Q3_Val, Q4_Val, Q5_Val, Q6_Val, Q7_Val, Q8_Val, Q9_Val, Q10_Val, Q11_Val, Q12_Val, Q13_Val, Q14_Val, Q15_Val, Q16_Val, Q17_Val, Q18_Val, Q19_Val, Q20_Val) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    values = [
        survey_id,
        None, None, travti_label, None,
        round(score_ei, 3), round(score_sn, 3), round(score_tf, 3), round(score_jp, 3),
        stamina, alcohol
    ] + answers + q_vals_numeric

    for attempt in range(5):
        try:
            cursor.execute(insert_query, values)
            break
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e).lower() and attempt < 4:
                time.sleep(0.2 * (attempt + 1))
                continue
            raise

    session['survey_id'] = survey_id
    return {'success': True, 'redirect': '/result', 'survey_id': survey_id}, 200

@app.route('/result')
def result():
    # DB에서 가장 최근 제출 데이터 조회
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
                # TraVTI_Label에 따른 설명 매핑
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
    
    # 모든 MBTI 타입
    all_mbti_types = ["INTP", "ESTJ", "ENFP", "INFJ", "ENTP", "ISFP", "ISTJ", "ESFP"]
    # MBTI 타입 버튼들을 HTML로 생성
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
                
                <!-- 동행자 MBTI 선택 섹션 -->
                <div class="text-left border-b border-slate-200 pb-4 mb-8">
                    <h3 class="text-2xl font-bold mb-1">동행자 추가하기</h3>
                </div>
                <!-- MBTI 그리드 (내 MBTI + 추가된 MBTI들 + 추가 버튼) -->
                <div class="grid grid-cols-2 gap-6" id="mbti-grid">
                    <!-- 내 MBTI 표시 -->
                    <div class="bg-white p-6 rounded-2xl shadow-md border border-slate-100 flex items-center gap-5">
                        <div class="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center text-blue-500"><span class="material-symbols-outlined text-3xl">account_circle</span></div>
                        <div class="text-left"><span class="text-[10px] bg-slate-900 text-white px-1.5 py-0.5 rounded">Me</span><h4 class="font-black text-2xl text-blue-500">{travti_label}</h4></div>
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

            <!-- MBTI 선택 박스 (숨겨짐 상태로 시작) -->
            <div id="selector-box" class="hidden bg-white p-8 rounded-3xl shadow-xl border border-blue-100 mt-10">
                <h4 class="font-bold mb-6 text-lg text-left">추가할 MBTI 선택</h4>
                <div class="grid grid-cols-4 gap-4" id="mbti-buttons-container">
                    <!-- MBTI 버튼들 (동적 생성) -->
                    {{{{ mbti_buttons|safe }}}}
                </div>
            </div>

            <!-- AI 추천 섹션 -->
            <section class="mt-20 text-center"><div class="bg-blue-50 rounded-3xl p-12">
                <h3 class="text-2xl font-bold mb-4">Travis AI의 맞춤 여행지 추천</h3>
                <a href="/group-recommendation" class="bg-blue-500 text-white font-bold py-4 px-10 rounded-full inline-block cursor-pointer hover:bg-blue-600 transition-colors">여행지 추천받기</a>
            </div></section>
        </main>
        <!-- 우측 떠있는 동행자 선택 패널 -->
        <div id="floating-panel-container" style="position: absolute; right: 160px; z-index: 50;">
            <div style="background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.12); padding: 20px; min-width: 180px; border: 1px solid #e5e7eb; backdrop-filter: blur(10px); background-color: rgba(255,255,255,0.95);">
                <p style="font-size: 20px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 16px; text-align: center;">친구 목록</p>
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <div id="friend-kevin" draggable="true" ondragstart="handleDragStart(event, 'kevin')" onclick="addCompanionByClick('kevin')" style="padding: 12px 14px; background: #f9fafb; border: 1.5px solid #e5e7eb; border-radius: 12px; text-align: center; font-weight: 600; font-size: 15px; color: #1f2937; cursor: grab; transition: all 0.2s; user-select: none; box-shadow: 0 1px 3px rgba(0,0,0,0.05);" onmouseenter="if(!this.dataset.disabled) this.style.background='#dbeafe'" onmouseleave="if(!this.dataset.disabled) this.style.background='#f9fafb'">kevin</div>
                    <div id="friend-혁수" draggable="true" ondragstart="handleDragStart(event, '혁수')" onclick="addCompanionByClick('혁수')" style="padding: 12px 14px; background: #f9fafb; border: 1.5px solid #e5e7eb; border-radius: 12px; text-align: center; font-weight: 600; font-size: 15px; color: #1f2937; cursor: grab; transition: all 0.2s; user-select: none; box-shadow: 0 1px 3px rgba(0,0,0,0.05);" onmouseenter="if(!this.dataset.disabled) this.style.background='#dbeafe'" onmouseleave="if(!this.dataset.disabled) this.style.background='#f9fafb'">혁수</div>
                    <div id="friend-재혁" draggable="true" ondragstart="handleDragStart(event, '재혁')" onclick="addCompanionByClick('재혁')" style="padding: 12px 14px; background: #f9fafb; border: 1.5px solid #e5e7eb; border-radius: 12px; text-align: center; font-weight: 600; font-size: 15px; color: #1f2937; cursor: grab; transition: all 0.2s; user-select: none; box-shadow: 0 1px 3px rgba(0,0,0,0.05);" onmouseenter="if(!this.dataset.disabled) this.style.background='#dbeafe'" onmouseleave="if(!this.dataset.disabled) this.style.background='#f9fafb'">재혁</div>
                    <div id="friend-민웅" draggable="true" ondragstart="handleDragStart(event, '민웅')" onclick="addCompanionByClick('민웅')" style="padding: 12px 14px; background: #f9fafb; border: 1.5px solid #e5e7eb; border-radius: 12px; text-align: center; font-weight: 600; font-size: 15px; color: #1f2937; cursor: grab; transition: all 0.2s; user-select: none; box-shadow: 0 1px 3px rgba(0,0,0,0.05);" onmouseenter="if(!this.dataset.disabled) this.style.background='#dbeafe'" onmouseleave="if(!this.dataset.disabled) this.style.background='#f9fafb'">민웅</div>
                </div>
            </div>
        </div>

        <!-- 결과 페이지 스크립트 -->
        <script>
            // 추가된 MBTI 목록 (초기값: 예측된 MBTI로 설정)
            const addedMbti = ["{travti_label}"];
            // 모든 MBTI 타입
            const allMbtiTypes = {json.dumps(all_mbti_types)};

            // 페이지 로드 시 버튼 업데이트 및 스크롤 핸들러 설정
            window.addEventListener('load', function() {{
                updateMbtiButtons();
                updateFloatingPanelPosition();
            }});

            // 스크롤 이벤트에서 플로팅 패널 위치 업데이트
            window.addEventListener('scroll', function() {{
                updateFloatingPanelPosition();
            }});

            function updateFloatingPanelPosition() {{
                const panel = document.getElementById('floating-panel-container');
                if (panel) {{
                    const scrollY = window.scrollY;
                    const viewportHeight = window.innerHeight;
                    const targetY = scrollY + (viewportHeight / 2) - 150;
                    panel.style.top = targetY + 'px';
                }}
            }}

            // MBTI 선택 박스 토글 (보이기/숨기기)
            function toggleSelector() {{
                const box = document.getElementById('selector-box');
                box.classList.toggle('hidden');
                box.scrollIntoView({{ behavior: 'smooth' }});
            }}

            // Drag & Drop handlers for floating companions
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
                // add companion card
                addCompanionCard(name);
            }}

            function addCompanionCard(name) {{
                if (addedMbti.includes(name)) return;
                addedMbti.push(name);
                updateFloatingFriendState(name);

                const grid = document.getElementById('mbti-grid');
                const newCard = document.createElement('div');
                newCard.className = 'bg-white p-6 rounded-2xl shadow-md border border-slate-100 flex items-center gap-5 relative';
                newCard.innerHTML = `
                    <div class="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center text-blue-500">
                        <span class="material-symbols-outlined text-3xl">account_circle</span>
                    </div>
                    <div class="text-left">
                        <h4 class="font-black text-2xl text-blue-500">${{name}}</h4>
                        <div class="text-sm text-slate-400">동행자</div>
                    </div>
                    <button onclick="deleteMbti('${{name}}', this.closest('div'))" class="absolute top-2 right-2 text-gray-400 hover:text-red-500 transition-colors">
                        <span class="material-symbols-outlined text-xl">close</span>
                    </button>
                `;

                // insert before add-button element
                const addButton = document.getElementById('add-button');
                grid.insertBefore(newCard, addButton);
            }}

            function addCompanionByClick(name) {{
                addCompanionCard(name);
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

            // MBTI 버튼 업데이트 (이미 추가된 MBTI는 비활성화)
            function updateMbtiButtons() {{
                const container = document.getElementById('mbti-buttons-container');
                container.innerHTML = '';
                
                allMbtiTypes.forEach(mbti => {{
                    const button = document.createElement('button');
                    button.textContent = mbti;
                    button.className = 'py-2 rounded-lg font-bold border border-slate-200';
                    
                    // 이미 추가된 MBTI는 비활성화
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

            // MBTI 추가 함수
            function addMbti(type) {{
                // 이미 추가된 것이면 중단
                if (addedMbti.includes(type)) {{
                    return;
                }}

                // 추가된 목록에 추가
                addedMbti.push(type);

                // 새로운 MBTI 카드 생성
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
                
                // 추가 버튼 앞에 새로운 카드 삽입
                const addButton = document.getElementById('add-button');
                grid.insertBefore(newCard, addButton);

                // 버튼 업데이트
                updateMbtiButtons();

                // 선택 박스 닫기
                document.getElementById('selector-box').classList.add('hidden');
            }}

            // MBTI 삭제 함수
            function deleteMbti(type, cardElement) {{
                // 추가된 목록에서 제거
                const index = addedMbti.indexOf(type);
                if (index > -1) {{
                    addedMbti.splice(index, 1);
                }}

                // 카드 제거
                cardElement.remove();

                // 플로팅 아이콘 다시 활성화
                enableFloatingFriendState(type);

                // 버튼 업데이트
                updateMbtiButtons();
            }}
        </script>
    </body></html>
    """
    return render_template_string(html_template, mbti_buttons=mbti_buttons, all_mbti_types=all_mbti_types)

# ========================================
# 페이지 4: AI 그룹 추천 결과 페이지
# ========================================
@app.route('/group-recommendation')
def group_recommendation():
    # AI 그룹 추천 결과 페이지
    destinations_json = json.dumps(DESTINATIONS_DATA, ensure_ascii=False)
    
    html_template = f"""<!DOCTYPE html><html class="light" lang="ko"><head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
    <title>TraVis | Travis AI 그룹 여행 추천 결과</title>
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
                    <!-- 프로필 이미지 -->
                    <div class="flex -space-x-4">
                        <div class="bg-center bg-no-repeat aspect-square bg-cover rounded-full size-24 ring-4 ring-white shadow-lg" style='background-image: url("data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22 fill=%22%23137fec%22%3E%3Cpath d=%22M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 11 8.5 11zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z%22/%3E%3C/svg%3E");'></div>
                        <div class="bg-center bg-no-repeat aspect-square bg-cover rounded-full size-24 ring-4 ring-white shadow-lg" style='background-image: url("data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22 fill=%22%23137fec%22%3E%3Cpath d=%22M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 11 8.5 11zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z%22/%3E%3C/svg%3E");'></div>
                    </div>
                    
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
                            <div class="w-px h-10 bg-slate-200"></div>
                            <div class="flex flex-col items-center">
                                <span class="text-blue-500 text-2xl font-black">혼합형</span>
                                <span class="text-slate-600 text-sm font-medium">소셜 에너지</span>
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
            
            <!-- 일정 선택 섹션 -->
            <div class="mb-12">
                <div class="flex items-center justify-between px-2 mb-4">
                    <h2 class="text-slate-900 text-2xl font-bold">2. 일정 선택하기</h2>
                </div>
                <div class="flex gap-4 items-center flex-wrap">
                    <button onclick="selectItinerary('1박2일')" class="itinerary-btn flex h-12 shrink-0 items-center justify-center rounded-xl bg-white border border-slate-200 px-6 text-slate-700 font-medium hover:border-blue-500 transition-all" data-itinerary="1박2일">
                        <span>1박 2일</span>
                    </button>
                    <button onclick="selectItinerary('2박3일')" class="itinerary-btn flex h-12 shrink-0 items-center justify-center rounded-xl bg-white border border-slate-200 px-6 text-slate-700 font-medium hover:border-blue-500 transition-all" data-itinerary="2박3일">
                        <span>2박 3일</span>
                    </button>
                    <button onclick="selectItinerary('3박4일')" class="itinerary-btn flex h-12 shrink-0 items-center justify-center rounded-xl bg-white border border-slate-200 px-6 text-slate-700 font-medium hover:border-blue-500 transition-all" data-itinerary="3박4일">
                        <span>3박 4일</span>
                    </button>
                    <button onclick="selectItinerary('4박5일')" class="itinerary-btn flex h-12 shrink-0 items-center justify-center rounded-xl bg-white border border-slate-200 px-6 text-slate-700 font-medium hover:border-blue-500 transition-all" data-itinerary="4박5일">
                        <span>4박 5일</span>
                    </button>
                    <button onclick="selectItinerary('5박6일')" class="itinerary-btn flex h-12 shrink-0 items-center justify-center rounded-xl bg-white border border-slate-200 px-6 text-slate-700 font-medium hover:border-blue-500 transition-all" data-itinerary="5박6일">
                        <span>5박 6일</span>
                    </button>
                </div>
            </div>
            
            <!-- 맞춤형 AI 일정 생성 버튼 -->
            <div class="text-center mb-16">
                <button onclick="generateCustomItinerary()" class="inline-flex items-center gap-2 px-8 py-3 bg-blue-500 text-white font-bold rounded-xl hover:bg-blue-600 transition-colors shadow-md">
                    <span class="material-symbols-outlined">auto_awesome</span>
                    맞춤형 AI 일정 생성
                </button>
            </div>
            
            <!-- AI 추천 관광지 섹션 -->
            <div id="attractions-section" class="mb-10" style="display: none;"></div>
            
            <!-- 추가 생성 버튼 -->
            <div class="text-center mb-16">
                <button onclick="addMoreAttractions()" class="inline-flex items-center gap-2 px-8 py-3 bg-white border-2 border-blue-500 text-blue-500 font-bold rounded-xl hover:bg-blue-50 transition-colors">
                    <span class="material-symbols-outlined">add</span>
                    추가 생성
                </button>
            </div>
            
            <!-- 그룹 궁합 섹션 -->
            <div class="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white rounded-3xl shadow-2xl p-8 md:p-16 overflow-hidden relative">
                <a href="/result" class="absolute top-6 left-6 inline-flex items-center justify-center w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 transition-colors z-20">
                    <span class="material-symbols-outlined text-white">arrow_back</span>
                </a>
                <div class="relative z-10 flex flex-col md:flex-row items-center gap-10">
                    <div class="flex-1">
                        <h2 class="text-3xl font-bold mb-4">우리 그룹이 잘 맞는 이유</h2>
                        <div class="space-y-4">
                            <div class="flex gap-4">
                                <div class="size-10 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                                    <span class="material-symbols-outlined text-blue-400">analytics</span>
                                </div>
                                <p class="text-slate-300"><strong class="text-white">기획 스타일:</strong> ENTJ가 전체적인 루트를 설계하면, INTP가 여행을 특별하게 만들어줄 숨은 명소들을 찾아냅니다.</p>
                            </div>
                            <div class="flex gap-4">
                                <div class="size-10 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                                    <span class="material-symbols-outlined text-blue-400">speed</span>
                                </div>
                                <p class="text-slate-300"><strong class="text-white">템포:</strong> 고효율 여행과 지적 호기심이 만났습니다. 디테일을 놓치지 않으면서도 많은 곳을 경험할 수 있습니다.</p>
                            </div>
                            <div class="flex gap-4">
                                <div class="size-10 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                                    <span class="material-symbols-outlined text-blue-400">people</span>
                                </div>
                                <p class="text-slate-300"><strong class="text-white">관계성:</strong> 서로 다른 관점에서 여행을 바라보며, 깊은 대화 속에서 둘만의 추억을 만들어갑니다.</p>
                            </div>
                        </div>
                    </div>
                    <!-- 궁합 차트 -->
                    <div class="flex-1 w-full max-w-xs bg-white/5 rounded-2xl p-6 border border-white/10">
                        <h4 class="font-bold text-center mb-6">그룹 궁합 차트</h4>
                        <div class="space-y-6">
                            <div>
                                <div class="flex justify-between text-xs font-bold mb-1 uppercase tracking-widest text-slate-400">
                                    <span>논리 일치도</span>
                                    <span>100%</span>
                                </div>
                                <div class="h-2 w-full bg-white/10 rounded-full overflow-hidden">
                                    <div class="h-full bg-blue-500 rounded-full w-[100%]"></div>
                                </div>
                            </div>
                            <div>
                                <div class="flex justify-between text-xs font-bold mb-1 uppercase tracking-widest text-slate-400">
                                    <span>에너지 싱크</span>
                                    <span>85%</span>
                                </div>
                                <div class="h-2 w-full bg-white/10 rounded-full overflow-hidden">
                                    <div class="h-full bg-blue-500 rounded-full w-[85%]"></div>
                                </div>
                            </div>
                            <div>
                                <div class="flex justify-between text-xs font-bold mb-1 uppercase tracking-widest text-slate-400">
                                    <span>모험 성향</span>
                                    <span>92%</span>
                                </div>
                                <div class="h-2 w-full bg-white/10 rounded-full overflow-hidden">
                                    <div class="h-full bg-blue-500 rounded-full w-[92%]"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="absolute -bottom-20 -right-20 size-64 bg-blue-500/20 blur-[100px] rounded-full"></div>
                <div class="absolute -top-20 -left-20 size-64 bg-blue-500/10 blur-[100px] rounded-full"></div>
            </div>
        </main>
    </div>
    
    <script>
        const destinationsData = {destinations_json};
        let currentDestination = '일본';
        let selectedItinerary = null;
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
        
        function selectItinerary(itinerary) {{
            selectedItinerary = itinerary;
            
            // 버튼 스타일 업데이트
            document.querySelectorAll('.itinerary-btn').forEach(btn => {{
                if (btn.dataset.itinerary === itinerary) {{
                    btn.classList.remove('bg-white', 'border', 'border-slate-200', 'text-slate-700');
                    btn.classList.add('bg-blue-500', 'shadow-md', 'text-white');
                }} else {{
                    btn.classList.remove('bg-blue-500', 'shadow-md', 'text-white');
                    btn.classList.add('bg-white', 'border', 'border-slate-200', 'text-slate-700');
                }}
            }});
        }}

        function generateCustomItinerary() {{
            if (!selectedItinerary) {{
                alert('일정을 선택해주세요');
                return;
            }}
            
            // 섹션 표시
            const section = document.getElementById('attractions-section');
            section.style.display = 'block';
            
            // 렌더링
            renderAttractions();
            
            // 부드럽게 스크롤
            section.scrollIntoView({{ behavior: 'smooth' }});
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
                visibleCount = data.attractions.length;
            }} else {{
                visibleCount += 2;
            }}
            renderAttractions();
        }}
        
        // 초기 렌더링
        renderAttractions();
    </script>
    </body></html>
    """
    return render_template_string(html_template)

# ========================================
# 앱 실행
# ========================================
if __name__ == "__main__":
    # 포트 5000에서 실행, debug 모드 활성화
    app.run(port=5000, debug=True)
if __name__ == "__main__":
    # 포트 5000에서 실행, debug 모드 활성화
    app.run(port=5000, debug=True)

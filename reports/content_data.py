import json

# 1. 32-tier Trait Descriptions (4 traits x 8 levels)
TRAIT_TIERS = {
    'ei': {
        'E4': {'label': '압도적 외향 (E+++)', 'title': '지치지 않는 소셜 엔진', 'desc': '현지인, 동행객 가리지 않고 매일 새로운 사람들과 교류하며 여행의 에너지를 폭발시키는 진정한 분위기 메이커입니다.'},
        'E3': {'label': '확고한 외향 (E++)', 'title': '활기찬 네트워커', 'desc': '외부 활동과 왁자지껄한 분위기에서 활력을 듬뿍 얻습니다. 사람들과 함께 어울릴 때 여행의 만족도가 수직 상승합니다.'},
        'E2': {'label': '부드러운 외향 (E+)', 'title': '여유로운 사교가', 'desc': '가벼운 대화와 적당한 액티비티를 선호하며, 낯선 환경에서도 금방 미소를 띠며 사람들과 자연스럽게 어울립니다.'},
        'E1': {'label': '유연한 외향 (E)', 'title': '은은한 에너자이저', 'desc': '사람들과 어울리며 에너지를 얻는 편이지만, 때로는 혼자만의 시간도 유연하게 즐길 줄 아는 밸런스형 여행자입니다.'},
        'I1': {'label': '유연한 내향 (I)', 'title': '선택적 사교가', 'desc': '내면의 평화를 중시하면서도, 마음이 맞는 동행이나 특별한 공간에서는 숨겨둔 에너지를 발산하는 매력적인 타입입니다.'},
        'I2': {'label': '부드러운 내향 (I+)', 'title': '소수 정예 탐험가', 'desc': '시끌벅적한 무리보다는 소수의 편안한 사람들과 깊은 대화를 나누는 것을 선호하며, 활동 후엔 자신만의 휴식이 필요합니다.'},
        'I3': {'label': '확고한 내향 (I++)', 'title': '사색의 유랑자', 'desc': '화려한 관광지보다는 고즈넉한 풍경이나 조용한 골목길을 거닐며 스스로의 내면과 대화하는 시간을 진심으로 사랑합니다.'},
        'I4': {'label': '압도적 내향 (I+++)', 'title': '고립의 미학', 'desc': '외부의 방해를 최소화한 완벽한 고요함을 추구하며, 온전히 자신에게 집중하는 환경에서 최고의 힐링을 경험합니다.'},
    },
    'sn': {
        'S4': {'label': '압도적 감각 (S+++)', 'title': '디테일 마스터', 'desc': '눈앞에 펼쳐진 풍경의 질감, 음식의 향기 등 지금 당장 오감으로 느낄 수 있는 현실의 디테일을 놀라울 정도로 생생하게 포착합니다.'},
        'S3': {'label': '확고한 감각 (S++)', 'title': '현실주의 여행자', 'desc': '체감할 수 있는 확실한 경험과 검증된 명소를 선호합니다. 눈으로 보고 손으로 직접 만져보는 생동감 넘치는 여행을 즐깁니다.'},
        'S2': {'label': '부드러운 감각 (S+)', 'title': '소소한 관찰자', 'desc': '여행지에서 마주하는 소소하고 일상적인 풍경의 아름다움과 현지의 맛있는 음식에서 편안한 즐거움을 찾습니다.'},
        'S1': {'label': '유연한 감각 (S)', 'title': '현실과 상상의 타협점', 'desc': '보통은 현실적인 체험을 선호하지만, 이따금씩 여행지에 얽힌 비하인드 스토리나 상상력을 자극하는 요소에도 큰 흥미를 느낍니다.'},
        'N1': {'label': '유연한 직관 (N)', 'title': '상상하는 관찰자', 'desc': '대체로 영감을 중요하게 생각하면서도 현실적인 감각을 놓치지 않으며, 풍경 이면의 스토리를 가볍게 음미할 줄 압니다.'},
        'N2': {'label': '부드러운 직관 (N+)', 'title': '낭만적 몽상가', 'desc': '단순한 풍경 감상을 넘어 그 장소가 품고 있는 보이지 않는 분위기와 스토리텔링에 흠뻑 빠져드는 감성적인 여행자입니다.'},
        'N3': {'label': '확고한 직관 (N++)', 'title': '의미 탐구자', 'desc': '눈에 보이는 화려함보다는 여행이 주는 철학적 의미나 숨겨진 영감을 찾아내며, 끊임없이 지적, 감성적 상상력을 펼칩니다.'},
        'N4': {'label': '압도적 직관 (N+++)', 'title': '영감의 크리에이터', 'desc': '현실의 제약을 뛰어넘어 여행지에서 거대한 영감과 아이디어를 끄집어내는 데 탁월하며, 본인만의 독창적인 우주를 유영합니다.'},
    },
    'tf': {
        'T4': {'label': '압도적 사고 (T+++)', 'title': '냉철한 분석가', 'desc': '동선의 논리성, 가성비, 객관적 정보의 정확성을 극도로 중시하며, 감정에 휘둘리지 않는 완벽하고 깔끔한 여행을 디자인합니다.'},
        'T3': {'label': '확고한 사고 (T++)', 'title': '스마트한 전략가', 'desc': '문제가 발생하면 당황하기보다 합리적인 해결책부터 모색합니다. 효율적이고 원활하게 돌아가는 여행 시스템에서 큰 만족을 찾습니다.'},
        'T2': {'label': '부드러운 사고 (T+)', 'title': '원칙주의 조율자', 'desc': '대체로 효율과 논리를 중요하게 생각하지만, 지나치게 딱딱하지 않게 상황을 합리적으로 판단하여 동행자들에게 신뢰감을 줍니다.'},
        'T1': {'label': '유연한 사고 (T)', 'title': '따뜻한 실용주의', 'desc': '본질적으로 합리성을 추구하면서도 여행의 감성과 분위기를 해치지 않게 조절할 줄 아는 부드러운 이성파 여행자입니다.'},
        'F1': {'label': '유연한 감정 (F)', 'title': '이성적인 공감러', 'desc': '분위기와 감정을 소중히 여기면서도 필요할 때는 꽤나 현실적이고 실용적인 판단을 내릴 줄 아는 밸런스형 여행자입니다.'},
        'F2': {'label': '부드러운 감정 (F+)', 'title': '다정다감한 동행러', 'desc': '여행지의 풍경만큼이나 동행하는 사람 간의 따뜻한 교감을 중요하게 생각하며, 서로의 기분을 세심하게 살피는 배려심이 빛납니다.'},
        'F3': {'label': '확고한 감정 (F++)', 'title': '공감의 마술사', 'desc': '모든 순간의 감정과 분위기를 스펀지처럼 흡수하며 눈물 날 듯한 감동과 낭만적인 경험을 최고의 여행 가치로 삼습니다.'},
        'F4': {'label': '압도적 감정 (F+++)', 'title': '감성의 정점', 'desc': '여행지에서 만나는 찰나의 순간, 낯선 이의 작은 친절에도 영혼이 흔들리는 벅찬 감동을 느끼며 모든 과정을 가슴으로 기억합니다.'},
    },
    'jp': {
        'J4': {'label': '압도적 판단 (J+++)', 'title': '완벽 제어 시스템', 'desc': '플랜 A부터 Z까지, 분 단위로 쪼개진 엑셀 스케줄표가 있어야 마음이 놓이는 철두철미하고 빈틈없는 계획의 마스터입니다.'},
        'J3': {'label': '확고한 판단 (J++)', 'title': '믿음직한 가이드', 'desc': '예약, 교통, 동선 등 핵심적인 부분들이 매끄럽게 준비되어 있을 때 진정으로 여행을 즐길 수 있는 안정 지향형 여행자입니다.'},
        'J2': {'label': '부드러운 판단 (J+)', 'title': '유연한 계획러', 'desc': '기본적인 가이드라인과 굵직한 일정은 꼭 세워두지만, 현지의 상황에 따라 작은 변화들은 스트레스 없이 기분 좋게 수용합니다.'},
        'J1': {'label': '유연한 판단 (J)', 'title': '오픈 마인드 플래너', 'desc': '최소한의 뼈대만 잡아두고 그 안에서는 자유롭게 채워나가는 것을 선호하는, 계획과 즉흥의 경계를 타는 여행자입니다.'},
        'P1': {'label': '유연한 인식 (P)', 'title': '계획적인 모험가', 'desc': '기본 성향은 자유로움을 향하지만, 너무 놓치기 아쉬운 핫플레이스 하나쯤은 미리 찾아두는 최소한의 준비성은 갖추고 있습니다.'},
        'P2': {'label': '부드러운 인식 (P+)', 'title': '발길 닿는 대로', 'desc': '촘촘한 스케줄의 압박을 싫어하며, 아침에 눈을 떴을 때의 기분과 날씨에 따라 유연하게 목적지를 탐색하는 것을 즐깁니다.'},
        'P3': {'label': '확고한 인식 (P++)', 'title': '본능적 유랑자', 'desc': '계획보다는 지금 이 순간 마주치는 우연한 만남과 즉흥적인 선택들이 여행을 마법처럼 만들어준다고 확실하게 믿는 타입입니다.'},
        'P4': {'label': '압도적 인식 (P+++)', 'title': '통제 불능의 자유영혼', 'desc': '무계획이 곧 최고의 계획! 예측할 수 없는 짜릿한 돌발 상황조차 완벽한 액티비티로 승화시키는 궁극의 자유분방항 여행자입니다.'},
    }
}

# 2. 81-tier Persona Synthesis Tool 
# E, M, I / S, M, N / T, M, F / J, M, P combinations. 
# We'll generate the huge dictionary dynamically so the file isn't 2000 lines long, 
# but it will be 100% available to the application at runtime.

E_OPTS = {
    "E": "{user_name}님은 외부의 활발한 에너지와 새로운 환경에서 스파크를 일으키는 타입이네요.",
    "M": "{user_name}님은 상황에 따라 사람들과의 어울림과 차분한 사색을 유연하게 오가시네요.",
    "I": "{user_name}님은 번잡한 곳을 피해 고요하고 내밀한 자신만의 시간에서 에너지를 얻으시네요."
}

S_OPTS = {
    "S": "여행지에서는 눈앞에 보이는 현실의 아름다움과 생생한 오감을 있는 그대로 즐기는 편입니다.",
    "M": "눈앞의 현실적인 매력과 마음속 상상력을 자연스럽게 넘나들며 여행을 음미하는 편입니다.",
    "N": "단순한 풍경을 넘어 그 이면에 숨겨진 이야기와 다채로운 영감의 세계를 탐구하는 것을 좋아합니다."
}

T_OPTS = {
    "T": "객관적이고 합리적인 판단으로 여행의 효율을 높이는 데 능숙하며,",
    "M": "효율성과 분위기 사이에서 유연하게 균형을 잡을 줄 알며,",
    "F": "모든 순간의 기분과 동행객의 감정을 따뜻하게 살피는 것에 큰 가치를 두며,"
}

J_OPTS = {
    "J": "체계적으로 준비된 계획을 통해 완성도 높은 여행을 만들어가는 기획자입니다.",
    "M": "기본적인 계획과 현장의 즉흥성을 모두 즐길 줄 아는 밸런스형 여행자입니다.",
    "P": "발길 닿는 대로 펼쳐지는 예상치 못한 마법을 즐기는 자유로운 모험가입니다."
}

def generate_81_personas():
    personas = {}
    titles = {
        "ESTJ": "계획 관리자", "ENTJ": "경로 대장", "ESFJ": "안전 파수꾼", "ENFJ": "팀 조율자",
        "ISTJ": "꼼꼼한 기록자", "ISFJ": "친절 가이드", "INTJ": "분석형 탐험가", "INFJ": "통찰력 있는 여행자",
        "ESTP": "액티브 탐험가", "ESFP": "분위기 메이커", "ENTP": "발굴 요원", "ENFP": "영감 수집가",
        "ISTP": "현장 해결사", "ISFP": "감성 휴양가", "INTP": "지식 탐험가", "INFP": "낭만 여행가"
    }
    
    for e_k, e_v in E_OPTS.items():
        for s_k, s_v in S_OPTS.items():
            for t_k, t_v in T_OPTS.items():
                for j_k, j_v in J_OPTS.items():
                    code = e_k + s_k + t_k + j_k
                    
                    # Determine closest MBTI base
                    base_e = "E" if e_k in ["E", "M"] else "I" # Treat M as E by default for title mapping just as fallback, but nuanced
                    if base_e == "E" and e_k == "M": base_e = "E" # Will override properly later if needed.
                    base_mbti = (
                        ("E" if e_k == "E" else ("I" if e_k == "I" else "E")) +
                        ("S" if s_k == "S" else ("N" if s_k == "N" else "S")) +
                        ("T" if t_k == "T" else ("F" if t_k == "F" else "T")) +
                        ("J" if j_k == "J" else ("P" if j_k == "P" else "J"))
                    )
                    
                    content = f"{e_v} {s_v} {t_v} {j_v}"
                    
                    if "M" in code:
                        modifier = "다채로운 매력의"
                    else:
                        modifier = "확고한 스타일의"
                        
                    ext_title = f"{modifier} {titles.get(base_mbti, '여행자')}"
                    
                    personas[code] = {
                        "title": ext_title,
                        "description": content
                    }
    return personas

PERSONA_SUMMARIES = generate_81_personas()


# 3. Helper Functions
def get_trait_intensity_code(score):
    """
    Score -1.0 ~ +1.0 (Normalized from Raw Sum)
    Returns matching level suffix: 4, 3, 2, 1 for positive/negative 
    For EI: + is E, - is I
    For SN: + is S, - is N
    For TF: + is T, - is F
    For JP: + is J, - is P
    """
    s = float(score)
    mag = abs(s)
    if mag >= 0.66: level = 4
    elif mag >= 0.33: level = 3
    elif mag >= 0.11: level = 2
    else: level = 1
    
    return level

def get_trait_3tier_code(score):
    """ E/M/I 3-tier mapping for the 81 personas """
    s = float(score)
    if s > 0.33: return 1   # Positive side
    elif s < -0.33: return -1 # Negative side
    return 0               # Middle

def get_analysis_data(scores, user_name="여행자"):
    """ Return the exactly correct set of texts for a user's scores """
    result = {}
    
    # Calculate 8-tier traits
    e_val = scores.get('ei', 0)
    s_val = scores.get('sn', 0)
    t_val = scores.get('tf', 0)
    p_val = scores.get('jp', 0)
    
    result['traits'] = {
        'ei': TRAIT_TIERS['ei'][f"E{get_trait_intensity_code(e_val)}" if e_val >= 0 else f"I{get_trait_intensity_code(e_val)}"],
        'sn': TRAIT_TIERS['sn'][f"S{get_trait_intensity_code(s_val)}" if s_val >= 0 else f"N{get_trait_intensity_code(s_val)}"],
        'tf': TRAIT_TIERS['tf'][f"T{get_trait_intensity_code(t_val)}" if t_val >= 0 else f"F{get_trait_intensity_code(t_val)}"],
        'jp': TRAIT_TIERS['jp'][f"J{get_trait_intensity_code(p_val)}" if p_val >= 0 else f"P{get_trait_intensity_code(p_val)}"]
    }
    
    # Calculate 81-tier persona
    # E/M/I
    ei_tier = get_trait_3tier_code(e_val)
    code_1 = "E" if ei_tier == 1 else ("I" if ei_tier == -1 else "M")
    
    sn_tier = get_trait_3tier_code(s_val)
    code_2 = "S" if sn_tier == 1 else ("N" if sn_tier == -1 else "M")
    
    tf_tier = get_trait_3tier_code(t_val)
    code_3 = "T" if tf_tier == 1 else ("F" if tf_tier == -1 else "M")
    
    jp_tier = get_trait_3tier_code(p_val)
    code_4 = "J" if jp_tier == 1 else ("P" if jp_tier == -1 else "M")
    
    persona_code = f"{code_1}{code_2}{code_3}{code_4}"
    
    base_persona_data = PERSONA_SUMMARIES.get(persona_code, PERSONA_SUMMARIES["MMMM"])
    
    # Base MBTI exact string from numerical polarity
    base_mbti = (
        ("E" if e_val >= 0 else "I") +
        ("S" if s_val >= 0 else "N") +
        ("T" if t_val >= 0 else "F") +
        ("J" if p_val >= 0 else "P")
    )
    
    titles = {
        "ESTJ": "계획 관리자", "ENTJ": "경로 대장", "ESFJ": "안전 파수꾼", "ENFJ": "팀 조율자",
        "ISTJ": "꼼꼼한 기록자", "ISFJ": "친절 가이드", "INTJ": "분석형 탐험가", "INFJ": "통찰력 있는 여행자",
        "ESTP": "액티브 탐험가", "ESFP": "분위기 메이커", "ENTP": "발굴 요원", "ENFP": "영감 수집가",
        "ISTP": "현장 해결사", "ISFP": "감성 휴양가", "INTP": "지식 탐험가", "INFP": "낭만 여행가"
    }

    modifier = "다채로운 매력의" if "M" in persona_code else "확고한 스타일의"
    correct_title = f"{modifier} {titles.get(base_mbti, '여행자')}"
    
    result['persona'] = {
        "title": correct_title,
        "description": base_persona_data["description"].replace("{user_name}", user_name)
    }
    result['persona_code'] = persona_code
    
    return result


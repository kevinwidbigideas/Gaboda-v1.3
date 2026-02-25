from flask import Blueprint, session
import html as html_lib
import os
import json
import pandas as pd
from app import get_db
from datetime import datetime
from utils import COMMON_HEAD, get_header

itinerary_bp = Blueprint('itinerary', __name__, url_prefix='/itinerary')


# --- WHI core logic (minimal, inline) ---
from dataclasses import dataclass
from itertools import combinations
from typing import Dict, List, Optional, Any
import random

USE_CALIBRATION = True
MIN_SCORE_FLOOR = 35.0
INT_LOW_TH = 0.222
INT_HIGH_TH = 0.778
STAMINA_LOW_TH = 0.25
STAMINA_MID_TH = 0.50
DRINKER_TH = 0.5

@dataclass
class User:
    id: str
    name: str
    personalities: Dict[str, float]
    stamina: float
    alcohol: float
    is_anchor: bool = False
    @property
    def is_drinker(self) -> bool:
        return self.alcohol >= DRINKER_TH

class CSVRepository:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
    def fetch_users(self, target_ids: List[str]) -> List[User]:
        df = pd.read_csv(self.csv_path)
        df["ID"] = df["ID"].astype(str)
        users = []
        for _, row in df[df["ID"].isin(target_ids)].iterrows():
            users.append(
                User(
                    id=row["ID"],
                    name=row["ID"],
                    personalities={
                        "EI": float(row["Score_EI"]),
                        "SN": float(row["Score_SN"]),
                        "TF": float(row["Score_TF"]),
                        "JP": float(row["Score_JP"]),
                    },
                    stamina=float(row["Stamina"]),
                    alcohol=float(row["Alcohol"]),
                )
            )
        return users


class DBRepository:
    def fetch_users(self, target_ids: List[str]) -> List[User]:
        if not target_ids:
            return []
        db = get_db()
        cur = db.cursor()
        q = "SELECT ID, Name, Score_EI, Score_SN, Score_TF, Score_JP, Stamina, Alcohol FROM travis_data WHERE ID IN ({})".format(
            ",".join(["?"] * len(target_ids))
        )
        cur.execute(q, target_ids)
        rows = cur.fetchall()
        users = []
        for row in rows:
            user_id = str(row[0])
            name = str(row[1]) if row[1] is not None else user_id
            users.append(
                User(
                    id=user_id,
                    name=name,
                    personalities={
                        "EI": float(row[2]),
                        "SN": float(row[3]),
                        "TF": float(row[4]),
                        "JP": float(row[5]),
                    },
                    stamina=float(row[6]),
                    alcohol=float(row[7]),
                )
            )
        return users


class ResourceManager:
    def __init__(self, seed: Optional[int] = None):
        self.map: Dict[str, List[str]] = {}
        self.rng = random.Random(seed)
    def load_json(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            code = item.get("code")
            if not code:
                continue
            if "text_variants" in item:
                self.map[code] = item["text_variants"]
            elif "text" in item:
                self.map[code] = [item["text"]]
    def get(self, code: Optional[str]) -> Optional[str]:
        if not code or code not in self.map:
            return None
        return self.rng.choice(self.map[code])

class WHICalculator:
    GRADE_RULES = [
        ("S+", 18, lambda d, a, b: d <= 0.111 and ((a > 0.5 and b > 0.5) or (a <= 0.5 and b <= 0.5))),
        ("S-", 12, lambda d, a, b: d <= 0.111),
        ("C+", 8,  lambda d, a, b: d <= 0.333),
        ("N",  3,  lambda d, a, b: d <= 0.444),
        ("W1", -4, lambda d, a, b: d <= 0.667),
        ("W2", -9, lambda d, a, b: d < 1.0),
        ("X", -15, lambda d, a, b: d >= 1.0),
    ]
    DIM_WEIGHTS = {"EI": 0.35, "SN": 0.25, "TF": 0.20, "JP": 0.20}
    @staticmethod
    def calibrate(score: float) -> float:
        if not USE_CALIBRATION:
            return round(score, 1)
        return round(MIN_SCORE_FLOOR + (100 - MIN_SCORE_FLOOR) * (score / 100), 1)
    @staticmethod
    def _intensity(diff: float) -> str:
        if diff <= INT_LOW_TH:
            return "LOW"
        if diff >= INT_HIGH_TH:
            return "HIGH"
        return "MID"
    @staticmethod
    def _calc_pair(u1: User, u2: User, tone: str) -> Dict[str, Any]:
        role = "ANCH" if (u1.is_anchor or u2.is_anchor) else "NON"
        total = 0.0
        personality_codes = []
        for dim, w in WHICalculator.DIM_WEIGHTS.items():
            a, b = u1.personalities[dim], u2.personalities[dim]
            diff = abs(a - b)
            for grade, score, cond in WHICalculator.GRADE_RULES:
                if cond(diff, a, b):
                    final = score * 1.2 if role == "ANCH" and score < 0 else score
                    total += final * w
                    if grade in ["W1", "W2", "X"]:
                        personality_codes.append(
                            f"P__DIM_{dim}__RISK_{grade}__INT_{WHICalculator._intensity(diff)}"
                        )
                    break
        p_norm = max(0, min(1, (total + 15) / 33))
        s_norm = max(0, min(1, (1 - abs(u1.stamina - u2.stamina))))
        a_norm = 1 if u1.is_drinker == u2.is_drinker else 0
        raw = 100 * (0.65 * p_norm + 0.25 * s_norm + 0.10 * a_norm)
        final_whi = WHICalculator.calibrate(raw)
        stamina_level = "LOW" if abs(u1.stamina - u2.stamina) < STAMINA_LOW_TH else \
                        "MID" if abs(u1.stamina - u2.stamina) < STAMINA_MID_TH else "HIGH"
        alcohol_code = None
        if u1.is_drinker != u2.is_drinker:
            alcohol_code = f"A__TYPE_MISMATCH__ROLE_{role}__TONE_{tone}"
        return {
            "pair": [u1.id, u2.id],
            "final_whi": final_whi,
            "role": role,
            "personality_codes": personality_codes,
            "stamina_code": f"S__DIFF_{stamina_level}__ROLE_{role}__TONE_{tone}",
            "alcohol_code": alcohol_code,
        }
    @staticmethod
    def get_group_result(users: List[User], anchor_id: Optional[str], anchor_type: str, tone: str):
        anchor = next((u for u in users if u.id == anchor_id), None)
        for u in users:
            u.is_anchor = (u == anchor)
        all_pairs = [WHICalculator._calc_pair(u1, u2, tone) for u1, u2 in combinations(users, 2)]
        if anchor:
            anchor_pairs = [p for p in all_pairs if anchor.id in p["pair"]]
            member_pairs = [p for p in all_pairs if anchor.id not in p["pair"]]
            group_whi = round(sum(p["final_whi"] for p in anchor_pairs) / len(anchor_pairs), 1)
            mode = "B"
        else:
            anchor_pairs = []
            member_pairs = all_pairs
            scores = [p["final_whi"] for p in all_pairs]
            group_whi = round(0.7 * min(scores) + 0.3 * sum(scores) / len(scores), 1)
            mode = "A"
        state_code = f"G__MODE_{mode}__SCORE_{int(group_whi // 10 * 10)}__ANCH_{anchor_type}__TONE_{tone}"
        return {
            "group_whi": group_whi,
            "group_state_code": state_code,
            "anchor_relations": anchor_pairs,
            "member_relations": member_pairs,
            "members": [u.id for u in users],
        }

class ReportBuilder:
    def __init__(self, rm: ResourceManager):
        self.rm = rm
    def _merge(self, texts: List[str]) -> Optional[str]:
        if not texts:
            return None
        if len(texts) == 1:
            return texts[0]
        return "여행을 함께하는 과정에서 몇 가지 차이가 함께 나타날 수 있습니다. " + " ".join(texts)
    def _compose_personality(self, codes, role, anchor_type, tone):
        texts = []
        for c in codes:
            parts = [
                self.rm.get(f"P__ROLE_{role}__TONE_{tone}"),
                self.rm.get(c),
                self.rm.get(f"ANCH_{anchor_type}__TONE_{tone}") if anchor_type != "NONE" else None
            ]
            texts.append(" ".join([p for p in parts if p]))
        return self._merge(texts)
    def _render_pairs(self, pairs, anchor_type, tone):
        out = []
        for p in pairs:
            out.append({
                "pair": p["pair"],
                "final_whi": p["final_whi"],
                "texts": {
                    "personality": self._compose_personality(p["personality_codes"], p["role"], anchor_type, tone),
                    "stamina": self.rm.get(p["stamina_code"]),
                    "alcohol": self.rm.get(p["alcohol_code"]),
                }
            })
        return out
    def build(self, result, anchor_type, tone):
        return {
            "group_whi": result["group_whi"],
            "group": {
                "state_code": result["group_state_code"],
                "text": self.rm.get(result["group_state_code"]),
            },
            "anchor_relations": self._render_pairs(result["anchor_relations"], anchor_type, tone),
            "member_relations": self._render_pairs(result["member_relations"], anchor_type, tone),
            "meta": {"members": result["members"]},
        }

@itinerary_bp.route('/')
def show_itinerary():
    destination = session.get('trip_destination') or '일본'
    destination_label = html_lib.escape(destination)
    destination_js = json.dumps(destination)
    region_js = json.dumps(session.get('trip_region') or session.get('trip_destination') or '')
    hotel_js = json.dumps(session.get('trip_hotel_address') or '')
    trip_start = session.get('trip_start')
    trip_end = session.get('trip_end')
    departure_date_js = json.dumps(trip_start or "")
    arrival_date_js = json.dumps(trip_end or "")
    
    # 시간 정보 추가
    trip_start_time = session.get('trip_start_time')
    trip_end_time = session.get('trip_end_time')
    departure_time_js = json.dumps(trip_start_time or "")
    arrival_time_js = json.dumps(trip_end_time or "")
    
    # 앵커 정보
    anchor_id = session.get('trip_anchor')
    anchor_js = json.dumps(anchor_id or "")

    duration_label = "미정"
    duration_days = None
    if trip_start and trip_end:
        try:
            start_dt = datetime.strptime(trip_start, "%Y-%m-%d")
            end_dt = datetime.strptime(trip_end, "%Y-%m-%d")
            days = (end_dt - start_dt).days + 1
            if days > 0:
                nights = max(days - 1, 0)
                duration_label = f"{nights}박 {days}일"
                duration_days = days
        except Exception:
            duration_label = "미정"
            duration_days = None
    duration_days_js = json.dumps(str(duration_days) if duration_days else "")
    # 1. 리소스/데이터 경로
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resource_dir = os.path.join(base_dir, 'llm_resource', 'state_code_json')
    # 2. 입력값 (세션에서 동행자 통계 사용)
    member_stats = session.get('itinerary_member_stats') or {}
    if not isinstance(member_stats, dict) or len(member_stats.keys()) < 2:
        member_ids = session.get('itinerary_member_ids') or []
        if isinstance(member_ids, list) and len(member_ids) >= 2:
            try:
                db = get_db()
                cur = db.cursor()
                placeholders = ",".join(["?"] * len(member_ids))
                cur.execute(
                    f"""
                    SELECT ID, Name, Score_EI, Score_SN, Score_TF, Score_JP, Stamina, Alcohol
                    FROM travis_data
                    WHERE ID IN ({placeholders})
                    """,
                    tuple(member_ids),
                )
                rows = cur.fetchall()
                member_stats = {
                    row[0]: {
                        "id": row[0],
                        "name": row[1],
                        "Score_EI": row[2],
                        "Score_SN": row[3],
                        "Score_TF": row[4],
                        "Score_JP": row[5],
                        "Stamina": row[6],
                        "Alcohol": row[7],
                    }
                    for row in rows
                    if row and row[0]
                }
                session['itinerary_member_stats'] = member_stats
            except Exception as e:
                print(f"[itinerary] member stats reload failed: {e}")
        if not isinstance(member_stats, dict) or len(member_stats.keys()) < 2:
            return "<html><body style='font-family:sans-serif; padding:24px;'>일정 멤버가 2명 이상 필요합니다.</body></html>"
            
    # Serialize for JS
    members_list_val = list(member_stats.keys())
    members_js = json.dumps(members_list_val)
    
    # 멤버 이름 리스트 추출 (ID 순서대로)
    member_names_list = [member_stats[mid].get('name', mid) for mid in members_list_val]
    member_names_js = json.dumps(member_names_list, ensure_ascii=False)
    
    member_details_val = list(member_stats.values())
    member_details_js = json.dumps(member_details_val, ensure_ascii=False)

    users = []
    for user_id, stats in member_stats.items():
        if not stats:
            continue
        try:
            users.append(
                User(
                    id=str(stats.get('id') or user_id),
                    name=str(stats.get('name') or user_id),
                    personalities={
                        "EI": float(stats.get("Score_EI")),
                        "SN": float(stats.get("Score_SN")),
                        "TF": float(stats.get("Score_TF")),
                        "JP": float(stats.get("Score_JP")),
                    },
                    stamina=float(stats.get("Stamina")),
                    alcohol=float(stats.get("Alcohol")),
                )
            )
        except Exception:
            continue

    if len(users) < 2:
        return "<html><body style='font-family:sans-serif; padding:24px;'>멤버 정보를 찾을 수 없습니다.</body></html>"

    # 실제 선택된 앵커 사용 (없으면 첫번째 멤버)
    sess_anchor = session.get('trip_anchor')
    if sess_anchor and any(u.id == sess_anchor for u in users):
        anchor_id = sess_anchor
    else:
        anchor_id = users[0].id
    anchor_js = json.dumps(anchor_id)

    anchor_type = "NONE"
    tone = "NEUTRAL"
    result = WHICalculator.get_group_result(users, anchor_id, anchor_type, tone)
    rm = ResourceManager()
    for fname in [
        'state_group_text.json',
        'state_personality_core_text.json',
        'state_personality_tone_text.json',
        'anchor_context_text.json',
        'state_stamina_alcohol_text.json',
    ]:
        rm.load_json(os.path.join(resource_dir, fname))
    report = ReportBuilder(rm).build(result, anchor_type, tone)
    # 4. 그룹 리포트 HTML 변환 (간단)
    # 모든 pair를 하나의 리스트로 통합 (anchor/member 구분 없이)
    all_pairs = report['anchor_relations'] + report['member_relations']

    whi_score = report['group_whi']
    if whi_score >= 85:
        whi_comment = "케미가 매우 뛰어난 그룹입니다! 서로의 여행 스타일이 잘 맞아요."
        whi_tags = ["#찰떡궁합", "#완벽케미", "#시너지", "#여행메이트"]
    elif whi_score >= 75:
        whi_comment = "케미가 높은 그룹이에요! 대부분의 상황에서 잘 어울릴 수 있습니다."
        whi_tags = ["#좋은분위기", "#합이잘맞음", "#여행친구"]
    elif whi_score >= 65:
        whi_comment = "평균 이상의 케미를 가진 그룹입니다. 약간의 조율만 있으면 좋아요."
        whi_tags = ["#조율필요", "#무난케미", "#함께여행"]
    elif whi_score >= 55:
        whi_comment = "보통 수준의 케미입니다. 서로 배려하면 충분히 즐거운 여행이 될 수 있어요."
        whi_tags = ["#배려여행", "#보통케미", "#함께가요"]
    else:
        whi_comment = "케미 차이가 큰 그룹입니다. 일정이나 역할 분담에 신경을 써보세요!"
        whi_tags = ["#조율필수", "#케미주의", "#역할분담"]



    member_ids = report['meta']['members']
    stamina_list = [u.stamina for u in users]
    avg_stamina = sum(stamina_list) / len(stamina_list)
    if avg_stamina >= 0.8:
        stamina_comment = "이 그룹은 체력이 매우 좋은 편이에요! 긴 일정도 소화할 수 있습니다."
        stamina_tags = ["#체력만렙", "#장거리OK", "#액티브"]
    elif avg_stamina >= 0.6:
        stamina_comment = "체력이 평균 이상인 그룹입니다. 대부분의 여행 일정에 무리가 없어요."
        stamina_tags = ["#평균이상체력", "#무난일정", "#여유여행"]
    elif avg_stamina >= 0.4:
        stamina_comment = "체력이 보통인 그룹이에요. 무리한 일정은 피하는 것이 좋아요."
        stamina_tags = ["#적당히쉬자", "#체력관리", "#휴식필수"]
    else:
        stamina_comment = "체력이 약한 멤버가 많아요. 충분한 휴식이 포함된 일정을 추천합니다."
        stamina_tags = ["#휴식중요", "#체력주의", "#힐링여행"]


    min_stamina = min(stamina_list)
    min_idx = stamina_list.index(min_stamina)
    min_member = users[min_idx].name
    if avg_stamina - min_stamina >= 0.25:
        stamina_gap_comment = f"특히 <b>{min_member}</b> 님은 체력이 비교적 약한 편이에요. 일정을 짤 때 배려해주면 더 좋은 여행이 될 수 있습니다!"
        stamina_gap_tags = ["#체력배려", "#멤버케어", "#유연일정"]
    else:
        stamina_gap_comment = "모든 멤버의 체력이 비슷해서 일정 소화에 큰 무리는 없어 보여요 :)"
        stamina_gap_tags = ["#체력균형", "#무난일정"]


    alcohol_list = [u.alcohol for u in users]
    avg_alcohol = sum(alcohol_list) / len(alcohol_list)
    drinker_count = sum(1 for u in users if u.is_drinker)
    if drinker_count == len(users):
        alcohol_comment = "모든 멤버가 술자리를 즐길 수 있는 그룹입니다."
        alcohol_tags = ["#술친구", "#파티타임", "#분위기UP"]
    elif drinker_count == 0:
        alcohol_comment = "모든 멤버가 비음주자라서, 술 없는 일정도 자연스러워요."
        alcohol_tags = ["#논알콜", "#건강여행", "#힐링"]
    else:
        alcohol_comment = "음주 성향이 다른 멤버가 섞여 있어요. 서로의 스타일을 존중해 주세요!"
        alcohol_tags = ["#음주존중", "#다양성", "#배려여행"]

    # --- 그룹 요약 해시태그 (state_group_text에서 주요 단어 추출) ---
    group_text = report['group']['text'] or ''
    import re
    # 한글 명사/키워드 추출(간단, 실제로는 형태소 분석 추천)
    group_keywords = re.findall(r'[가-힣]{2,}', group_text)
    group_tags = [f"#{w}" for w in list(dict.fromkeys(group_keywords))[:3]] if group_keywords else []

    all_tags = whi_tags + stamina_tags + stamina_gap_tags + alcohol_tags
    # --- 멤버별 관계 리포트 UI ---
    # 멤버 id → User 객체 매핑
    user_map = {u.id: u for u in users}
    id_to_name = {u.id: u.name for u in users}
    # 멤버별 pair 관계 정리
    member_pairs = {u.id: [] for u in users}
    for p in all_pairs:
        a, b = p['pair']
        member_pairs[a].append((b, p))
        member_pairs[b].append((a, p))

    # trait 라벨 맵
    trait_labels = {
        "EI": "외향-내향",
        "SN": "감각-직관",
        "TF": "사고-감정",
        "JP": "판단-인식"
    }
    trait_words = {
        "EI": ("외향적", "내향적"),
        "SN": ("감각적", "직관적"),
        "TF": ("사고적", "감정적"),
        "JP": ("판단적", "인식적")
    }
    dim_weights = {"EI": 0.35, "SN": 0.25, "TF": 0.20, "JP": 0.20}

    def get_best_worst_traits(u1, u2):
        """가장 잘 맞는 항목과 안 맞는 항목 각 1개씩 반환"""
        diffs = []
        for dim in ["EI", "SN", "TF", "JP"]:
            diff = abs(u1.personalities[dim] - u2.personalities[dim])
            weight = dim_weights[dim]
            diffs.append((diff, weight, dim))
        # 차이로 정렬, 같으면 가중치 높은 순
        diffs_sorted = sorted(diffs, key=lambda x: (x[0], -x[1]))
        best_dim = diffs_sorted[0][2]  # 가장 비슷한 항목
        worst_dim = diffs_sorted[-1][2]  # 가장 다른 항목
        return best_dim, worst_dim

    def trait_comment_pair(u1, u2):
        """best & worst 두 항목만 코멘트 반환"""
        best_dim, worst_dim = get_best_worst_traits(u1, u2)
        
        best_diff = abs(u1.personalities[best_dim] - u2.personalities[best_dim])
        worst_diff = abs(u1.personalities[worst_dim] - u2.personalities[worst_dim])
        
        if best_diff < 0.15:
            best_text = f"{trait_words[best_dim][0]} 성향이 매우 비슷해요!"
        elif best_diff < 0.35:
            best_text = f"{trait_words[best_dim][0]} 성향으로 잘 맞아요."
        else:
            best_text = f"{trait_words[best_dim][0]} 부분이 비교적 맞아요."
        
        if worst_diff < 0.35:
            worst_text = f"{trait_words[worst_dim][0]} 스타일이 약간 달라요."
        elif worst_diff < 0.6:
            worst_text = f"{trait_words[worst_dim][0]} 스타일이 꽤 달라요."
        else:
            worst_text = f"{trait_words[worst_dim][0]} 스타일이 매우 달라요."
        
        return best_text, worst_text

    # 멤버별 UI 생성
    member_html = "<div style='margin-bottom:18px;'><b>멤버별 케미 보기</b></div>"
    member_html += "<div>"
    for u in users:
        member_html += f"<div class='member-block' style='margin-bottom:10px;'>"
        display_name = id_to_name.get(u.id, u.id)
        member_html += f"<button onclick=\"toggleMember('{u.id}')\" style='font-weight:bold; font-size:1.1em; background:#f1f5f9; border:none; border-radius:8px; padding:8px 18px; margin-bottom:4px; cursor:pointer;'>👤 {display_name}</button>"
        member_html += f"<div id='member-{u.id}' class='member-detail' data-tab-index='0' style='display:none; margin-left:18px; margin-top:6px; margin-bottom:8px; background:#f8fafc; border-radius:8px; padding:10px 14px; border:1px solid #e5e7eb;'>"
        # 탭 헤더
        member_html += "<div style='display:flex; gap:8px; margin-bottom:10px; flex-wrap:wrap;'>"
        tab_idx = 0
        for other_id, _ in member_pairs[u.id]:
            if other_id == u.id:
                continue
            active_style = ""
            other_name = id_to_name.get(other_id, other_id)
            member_html += f"<button class='inner-tab' onclick=\"showInnerTab('{u.id}','{other_id}')\" id='tabbtn-{u.id}-{other_id}' style='padding:5px 14px; border-radius:7px; border:1px solid #e5e7eb; background:#f1f5f9; color:#2563eb; font-weight:500; margin-bottom:2px; margin-right:2px; cursor:pointer; font-size:0.98em;{active_style}'>{other_name}</button>"
            tab_idx += 1
        member_html += "</div>"
        # 탭 컨텐츠
        tab_idx = 0
        for other_id, pair in member_pairs[u.id]:
            if other_id == u.id:
                continue
            other = user_map[other_id]
            whi = pair['final_whi']
            if whi >= 85:
                whi_line = "최고의 케미!"
            elif whi >= 75:
                whi_line = "아주 잘 맞아요."
            elif whi >= 65:
                whi_line = "무난하게 어울림."
            elif whi >= 55:
                whi_line = "보통, 약간 조율 필요."
            else:
                whi_line = "충돌 가능성, 배려 필요!"
            member_html += f"<div class='inner-tab-content' id='tabcont-{u.id}-{other_id}' style='display:none; margin-bottom:10px; border-top:1px solid #e5e7eb; padding-top:8px;'>"
            left_name = id_to_name.get(u.id, u.id)
            right_name = id_to_name.get(other_id, other_id)
            member_html += f"<b>{left_name} & {right_name}</b> <span style='color:#2563eb;'>{whi_line}</span>"
            best_text, worst_text = trait_comment_pair(u, other)
            member_html += f"<ul style='margin:4px 0 0 12px; color:#555; font-size:0.97em;'><li><b>케미:</b> {best_text}</li><li><b>주의:</b> {worst_text}</li></ul>"
            if pair['texts']['personality']:
                member_html += f"<div style='color:#888; margin-top:2px;'>{pair['texts']['personality']}</div>"
            member_html += "</div>"
            tab_idx += 1
        member_html += "</div></div>"
    member_html += "</div>"

    # --- 그룹 6각형 차트 데이터 준비 ---
    avg_ei = sum(u.personalities["EI"] for u in users) / len(users)
    avg_sn = sum(u.personalities["SN"] for u in users) / len(users)
    avg_tf = sum(u.personalities["TF"] for u in users) / len(users)
    avg_jp = sum(u.personalities["JP"] for u in users) / len(users)
    avg_stamina = sum(u.stamina for u in users) / len(users)
    avg_alcohol = sum(u.alcohol for u in users) / len(users)
    
    # SVG 육각형 레이더 차트
    def radar_chart():
        values = [avg_ei, avg_sn, avg_tf, avg_jp, avg_stamina, avg_alcohol]
        
        # 각 축의 값에 따라 레이블 결정 (0.5 기준)
        labels = []
        labels.append("폭발적 에너지" if avg_ei > 0.5 else "차분한 여유")
        labels.append("현실 감각" if avg_sn > 0.5 else "직관적 영감")
        labels.append("이성적 판단" if avg_tf > 0.5 else "감성적 공감")
        labels.append("계획적 실행" if avg_jp > 0.5 else "유연한 즉흥")
        labels.append("체력 충만" if avg_stamina > 0.5 else "여유로운 템포")
        labels.append("흥 넘침" if avg_alcohol > 0.5 else "맑은 정신")
        
        # 각 항목별 색상
        colors = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#3b82f6", "#a855f7"]
        
        cx, cy, r = 140, 140, 90  # 중심, 반지름 더 크게
        
        # 6개 꼭짓점 좌표 계산 (12시 방향부터 시계방향)
        import math
        points = []
        for i in range(6):
            angle = math.pi / 2 - (2 * math.pi * i / 6)  # 12시부터 시작
            # 값을 좀 더 드라마틱하게 (0.5를 기준으로 확대)
            enhanced_val = 0.5 + (values[i] - 0.5) * 1.3
            enhanced_val = max(0.2, min(1.0, enhanced_val))  # 0.2~1.0 범위
            x = cx + r * enhanced_val * math.cos(angle)
            y = cy - r * enhanced_val * math.sin(angle)
            points.append((x, y))
        
        polygon_points = " ".join([f"{x},{y}" for x, y in points])
        
        # 배경 육각형 그리드 (0.25, 0.5, 0.75, 1.0)
        grid_lines = ""
        for level in [0.3, 0.5, 0.7, 1.0]:
            grid_points = []
            for i in range(6):
                angle = math.pi / 2 - (2 * math.pi * i / 6)
                x = cx + r * level * math.cos(angle)
                y = cy - r * level * math.sin(angle)
                grid_points.append((x, y))
            grid_polygon = " ".join([f"{x},{y}" for x, y in grid_points])
            opacity = 0.25 if level == 1.0 else 0.12
            grid_lines += f'<polygon points="{grid_polygon}" fill="none" stroke="#cbd5e1" stroke-width="1.5" opacity="{opacity}"/>'
        
        # 축 선 (각각 다른 색상)
        axis_lines = ""
        for i in range(6):
            angle = math.pi / 2 - (2 * math.pi * i / 6)
            x = cx + r * math.cos(angle)
            y = cy - r * math.sin(angle)
            axis_lines += f'<line x1="{cx}" y1="{cy}" x2="{x}" y2="{y}" stroke="{colors[i]}" stroke-width="1.5" opacity="0.3"/>'
        
        # 각 점에 색상 원 추가
        point_circles = ""
        for i, (x, y) in enumerate(points):
            point_circles += f'<circle cx="{x}" cy="{y}" r="4" fill="{colors[i]}" stroke="white" stroke-width="1.5"/>'
        
        # 레이블 (색상 적용)
        label_html = ""
        for i in range(6):
            angle = math.pi / 2 - (2 * math.pi * i / 6)
            x = cx + (r + 30) * math.cos(angle)
            y = cy - (r + 30) * math.sin(angle)
            label_html += f'<text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="middle" font-size="13" fill="{colors[i]}" font-weight="700">{labels[i]}</text>'
        
        svg = f'''
        <svg width="300" height="300" viewBox="0 0 280 280" style="margin:10px auto; display:block;">
            {grid_lines}
            {axis_lines}
            <polygon points="{polygon_points}" fill="url(#grad1)" fill-opacity="0.4" stroke="#2563eb" stroke-width="2.5" stroke-linejoin="round"/>
            <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#3b82f6;stop-opacity:0.6" />
                    <stop offset="100%" style="stop-color:#8b5cf6;stop-opacity:0.6" />
                </linearGradient>
            </defs>
            {point_circles}
            {label_html}
        </svg>
        '''
        return svg

    group_html = (
        f"<h2>그룹 리포트</h2>"
        f"<div style='font-size:1.1rem; margin-bottom:10px;'><b>그룹 WHI 점수:</b> {whi_score}</div>"
        f"{radar_chart()}"
        f"<div style='margin-bottom:10px; color:#2563eb;'><b>한줄평:</b> {whi_comment}</div>"
        f"<div style='margin-bottom:10px;'><b>그룹 요약:</b> {group_text}</div>"
        f"<div style='margin-bottom:10px;'><b>스테미나 평가:</b> {stamina_comment}</div>"
        f"<div style='margin-bottom:10px;'><b>체력 편차:</b> {stamina_gap_comment}</div>"
        f"<div style='margin-bottom:18px;'><b>알콜 성향:</b> {alcohol_comment}</div>"
        f"<div style='margin-bottom:10px; color:#888; font-size:0.98em;'><b>해시태그:</b> {' '.join(all_tags)}</div>"
        f"<div style='margin-bottom:18px;'><b>멤버:</b> {', '.join([id_to_name.get(mid, mid) for mid in report['meta']['members']])}</div>"
        f"<div style='margin-bottom:18px;'>" + member_html + "</div>"
    )
    # 5. 기존 탭 UI에 삽입
    html = f'''
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        {COMMON_HEAD}
        <title>Travis 여행 계획</title>
        <style>
            body {{ font-family: 'Pretendard', sans-serif; background: #f8fafc; margin: 0; }}
            .tab-container {{ max-width: 700px; margin: 40px auto; background: #fff; border-radius: 18px; box-shadow: 0 2px 12px rgba(0,0,0,0.07); padding: 0 0 32px 0; }}
            .tabs {{ display: flex; border-bottom: 2px solid #e5e7eb; }}
            .tab {{ flex: 1; text-align: center; padding: 18px 0; font-size: 1.2rem; font-weight: 600; cursor: pointer; color: #64748b; background: none; border: none; outline: none; transition: color 0.2s; }}
            .tab.active {{ color: #2563eb; border-bottom: 3px solid #2563eb; background: #f1f5f9; }}
            .tab-content {{ display: none; padding: 32px 36px 0 36px; min-height: 320px; }}
            .tab-content.active {{ display: block; }}
            .member-block button:focus {{ outline: 2px solid #2563eb; }}
            .inner-tab.active {{ background:#2563eb !important; color:#fff !important; }}
            .inner-tab-content {{ display:none; }}
        </style>
    </head>
    <body>
        {get_header('itinerary')}
        <div class="tab-container">
            <div class="tabs">
                <button class="tab active" onclick="showTab(0)">그룹 리포트</button>
                <button class="tab" onclick="showTab(1)">여행 일정</button>
            </div>
            <div class="tab-content active" id="tab0">
                {group_html}
            </div>
            <div class="tab-content" id="tab1">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:24px;">
                    <h2 style="margin:0; font-size:24px; font-weight:700; color:#1e293b;">{destination_label}을 위한 Travis의 제안</h2>
                    <div style="display:flex; gap:24px; font-size:14px;">
                        <div style="text-align:right;">
                            <p style="font-size:11px; font-weight:600; color:#64748b; margin:0 0 4px 0;">목적지</p>
                            <p style="font-size:14px; font-weight:700; color:#1e293b; margin:0;">{destination_label}</p>
                        </div>
                        <div style="text-align:right;">
                            <p style="font-size:11px; font-weight:600; color:#64748b; margin:0 0 4px 0;">여행 기간</p>
                            <p style="font-size:14px; font-weight:700; color:#1e293b; margin:0;">{duration_label}</p>
                        </div>
                    </div>
                </div>
                <div id="itinerary-result">
                    <div id="itinerary-loading" style="text-align:center; padding:40px; color:#64748b;">
                        <p style="font-size:14px;">일정을 생성하는 중입니다... 잠시만 기다려주세요.</p>
                    </div>
                    <div id="itinerary-content" style="display:none;"></div>
                    <div id="itinerary-error" style="display:none; color:#dc2626; padding:16px; background:#fee2e2; border-radius:8px; border:1px solid #fca5a5;"></div>
                </div>
                
                <!-- 플로팅 버튼: 개인 맞춤 제안 -->
                <button id="personal-rec-float-btn" onclick="togglePersonalRecPanel()" style="position:fixed; right:30px; bottom:30px; width:60px; height:60px; border-radius:50%; background:#2563eb; color:#fff; border:none; box-shadow:0 4px 12px rgba(0,0,0,0.15); cursor:pointer; font-size:24px; z-index:1000; transition:all 0.3s; display:none;" onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'">
                    👤
                </button>
            </div>
            
            <!-- 사이드 패널: 개인별 맞춤 제안 -->
            <div id="personal-rec-panel" style="position:fixed; right:-450px; top:0; width:450px; height:100vh; background:#fff; box-shadow:-4px 0 20px rgba(0,0,0,0.1); z-index:999; transition:right 0.3s ease-in-out; overflow-y:auto;">
                <div style="padding:20px; background:#2563eb; color:#fff; display:flex; justify-content:space-between; align-items:center;">
                    <h2 style="margin:0; font-size:18px; font-weight:700;">👤 개인별 맞춤 제안</h2>
                    <button onclick="togglePersonalRecPanel()" style="background:transparent; border:none; color:#fff; font-size:24px; cursor:pointer; line-height:1;">&times;</button>
                </div>
                
                <div style="padding:20px;">
                    <p style="font-size:13px; color:#64748b; margin-bottom:20px;">각 여행객을 위한 개인화된 제안을 확인해보세요.</p>
                    
                    <div id="personal-rec-tabs" style="display:flex; gap:8px; margin-bottom:20px; flex-wrap:wrap; border-bottom:2px solid #e2e8f0; padding-bottom:8px;">
                        <!-- 개인 탭 버튼들이 여기 생성됨 -->
                    </div>
                    
                    <div id="personal-rec-content" style="margin-top:20px;"></div>
                    
                    <div id="personal-rec-loading" style="text-align:center; padding:40px; color:#64748b; display:none;">
                        <p style="font-size:14px;">개인 맞춤 제안을 생성하는 중입니다...</p>
                    </div>
                    
                    <div id="personal-rec-error" style="display:none; color:#dc2626; padding:16px; background:#fee2e2; border-radius:8px; border:1px solid #fca5a5; margin-top:20px; font-size:13px;"></div>
                </div>
            </div>
        </div>
        <script>
            // 전역 변수에 그룹 정보와 일정 저장
            var globalGroupInfo = null;
            var globalDestination = {destination_js};
            var globalItinerary = null;
            var groupMemberIds = {members_js};  // 실제 멤버 ID 리스트
            var groupMemberDetails = {member_details_js};  // 멤버 상세 정보 (id, name 포함)
            var personalRecPanelOpen = false;
            var personalRecGenerated = false;
            
            function togglePersonalRecPanel() {{
                console.log('togglePersonalRecPanel 호출됨');
                var panel = document.getElementById('personal-rec-panel');
                personalRecPanelOpen = !personalRecPanelOpen;
                
                if (personalRecPanelOpen) {{
                    console.log('패널 열기');
                    panel.style.right = '0';
                    // 패널이 열릴 때 개인 맞춤 제안 생성 (아직 생성 안 했으면)
                    if (!personalRecGenerated) {{
                        console.log('generatePersonalRecommendations 호출 예정');
                        generatePersonalRecommendations();
                        personalRecGenerated = true;
                    }} else {{
                        console.log('이미 내용이 있음, 생성 스킵');
                    }}
                }} else {{
                    console.log('패널 닫기');
                    panel.style.right = '-450px';
                }}
            }}
            
            function showTab(idx) {{
                var tabs = document.querySelectorAll('.tab');
                var contents = document.querySelectorAll('.tab-content');
                tabs.forEach((t, i) => {{
                    t.classList.toggle('active', i === idx);
                    contents[i].classList.toggle('active', i === idx);
                }});
                
                // 여행 일정 탭(탭1)이 열리면 플로팅 버튼 표시
                var floatBtn = document.getElementById('personal-rec-float-btn');
                if (floatBtn) {{
                    floatBtn.style.display = idx === 1 ? 'block' : 'none';
                }}
            }}
            function toggleMember(id) {{
                var detail = document.getElementById('member-' + id);
                if (!detail) return;
                var isOpen = detail.style.display === 'block';
                detail.style.display = isOpen ? 'none' : 'block';
                if (!isOpen) {{
                    var tabs = detail.querySelectorAll('.inner-tab');
                    var conts = detail.querySelectorAll('.inner-tab-content');
                    tabs.forEach(btn => btn.classList.remove('active'));
                    conts.forEach(c => c.style.display = 'none');
                    if (tabs.length > 0 && conts.length > 0) {{
                        var idx = detail.dataset.tabIndex ? parseInt(detail.dataset.tabIndex, 10) : 0;
                        if (isNaN(idx) || idx < 0 || idx >= tabs.length) idx = 0;
                        tabs[idx].classList.add('active');
                        conts[idx].style.display = 'block';
                    }}
                }}
            }}
            function showInnerTab(uid, oid) {{
                var tabs = document.querySelectorAll(`#member-${{uid}} .inner-tab`);
                var conts = document.querySelectorAll(`#member-${{uid}} .inner-tab-content`);
                tabs.forEach(btn => btn.classList.remove('active'));
                conts.forEach(c => c.style.display = 'none');
                document.getElementById(`tabbtn-${{uid}}-${{oid}}`).classList.add('active');
                document.getElementById(`tabcont-${{uid}}-${{oid}}`).style.display = 'block';
            }}
            
            function generateItinerary() {{
                // 하드코딩된 값 (result 페이지에서 받을 예정)
                var destination = {destination_js};
                var itinerary_days = {duration_days_js} || "3";
                var region = {region_js};
                var hotel = {hotel_js};
                var departure_date = {departure_date_js};
                var arrival_date = {arrival_date_js};
                var departure_time = {departure_time_js};
                var arrival_time = {arrival_time_js};
                
                // 멤버별 상세 정보 추가
                var memberDetails = {member_details_js};
                
                // 그룹 정보 구성 (Python 주입)
                var groupInfo = {{
                    members: {members_js},
                    member_names: {member_names_js},
                    member_details: memberDetails,
                    anchor: {anchor_js},
                    group_whi: "상위 그룹",
                    destination: destination,
                    region: region,
                    hotel: hotel,
                    flight_arrival_time: arrival_time,
                    flight_departure_time: departure_time
                }};
                
                // 글로벌 변수에 저장
                globalGroupInfo = groupInfo;
                globalDestination = destination;
                
                // 결과창 표시
                var resultDiv = document.getElementById('itinerary-result');
                var loadingDiv = document.getElementById('itinerary-loading');
                var contentDiv = document.getElementById('itinerary-content');
                var errorDiv = document.getElementById('itinerary-error');
                
                resultDiv.style.display = 'block';
                loadingDiv.style.display = 'block';
                contentDiv.style.display = 'none';
                errorDiv.style.display = 'none';
                
                console.log("API 호출 준비: /api/generate-itinerary");
                
                // 실제 API 호출
                fetch('/api/generate-itinerary', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        group_info: groupInfo,
                        destination: destination,
                        itinerary_days: itinerary_days,
                        departure_date: departure_date,
                        arrival_date: arrival_date,
                        arrival_time: arrival_time,
                        departure_time: departure_time
                    }})
                }})
                .then(response => response.json())
                .then(result => {{
                    console.log("API 응답 받음:", result);
                    loadingDiv.style.display = 'none';
                    
                    if (result.ok && result.data) {{
                        // 전체 응답을 globalItinerary에 저장 (itinerary + personal_recommendations 포함)
                        globalItinerary = result.data;
                        
                        // 여행 일정만 렌더링
                        if (result.data.itinerary) {{
                            renderItinerary(result.data);
                            contentDiv.style.display = 'block';
                        }} else {{
                            errorDiv.textContent = '일정 데이터가 없습니다.';
                            errorDiv.style.display = 'block';
                        }}
                    }} else {{
                        console.error("API 에러:", result.error);
                        errorDiv.textContent = result.error || '일정 생성 중 오류가 발생했습니다.';
                        errorDiv.style.display = 'block';
                    }}
                }})
                .catch(error => {{
                    console.error("네트워크 에러:", error);
                    loadingDiv.style.display = 'none';
                    errorDiv.textContent = '서버 연결 오류: ' + error.message;
                    errorDiv.style.display = 'block';
                }});
            }}
            
            function renderItinerary(data) {{
                var contentDiv = document.getElementById('itinerary-content');
                var html = '';
                
                // 일별 일정
                if (data.itinerary && Array.isArray(data.itinerary)) {{
                    html += '<h2 style="font-size:18px; font-weight:700; color:#1e293b; margin-bottom:16px;">세부 일정</h2>';
                    
                    data.itinerary.forEach(day => {{
                        html += '<div style="background:#fff; border:1px solid #cbd5e1; border-radius:12px; padding:20px; margin-bottom:16px; overflow:hidden;">';
                        html += '<h3 style="font-size:16px; font-weight:700; color:#2563eb; margin-bottom:12px;">Day ' + day.day + ': ' + escapeHtml(day.title || '') + '</h3>';
                        
                        if (day.activities && Array.isArray(day.activities)) {{
                            html += '<div style="space-y:0;">';
                            day.activities.forEach((act, idx) => {{
                                html += '<div style="padding:12px 0; ' + (idx > 0 ? 'border-top:1px solid #e2e8f0;' : '') + '">';
                                html += '<div style="display:flex; gap:12px;">';
                                html += '<span style="font-weight:700; color:#64748b; min-width:60px;">' + escapeHtml(act.time || '') + '</span>';
                                html += '<div style="flex:1;">';
                                html += '<div style="font-weight:600; color:#334155;">' + escapeHtml(act.title || '') + '</div>';
                                if (act.reason) {{
                                    html += '<div style="font-size:13px; color:#64748b; margin-top:4px;">이유: ' + escapeHtml(act.reason) + '</div>';
                                }}
                                if (act.attraction && String(act.attraction).toLowerCase() !== 'null') {{
                                    html += '<div style="font-size:13px; color:#475569; margin-top:2px;">📍 ' + escapeHtml(act.attraction) + '</div>';
                                }}
                                html += '</div>';
                                html += '</div>';
                                html += '</div>';
                            }});
                            html += '</div>';
                        }}
                        
                        html += '</div>';
                    }});
                }}
                
                // 팁
                if (data.tips) {{
                    html += '<div style="background:#dbeafe; border:1px solid #93c5fd; border-radius:12px; padding:16px; margin-bottom:24px;">';
                    html += '<h3 style="font-weight:700; color:#1e40af; margin-bottom:8px;">💡 여행 팁</h3>';
                    html += '<p style="color:#1e3a8a; font-size:14px; line-height:1.6;">' + escapeHtml(data.tips) + '</p>';
                    html += '</div>';
                }}
                
                // 준비물
                if (data.packing && Array.isArray(data.packing)) {{
                    html += '<details style="margin-bottom:24px;">';
                    html += '<summary style="cursor:pointer; padding:12px; background:#f1f5f9; border-radius:8px; font-weight:600; color:#334155;">여행 준비물 체크리스트</summary>';
                    html += '<div style="padding:16px; background:#f8fafc; border:1px solid #cbd5e1; border-top:none; border-radius:0 0 8px 8px;">';
                    html += '<div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">';
                    data.packing.forEach(item => {{
                        html += '<label style="display:flex; align-items:center; gap:8px; cursor:pointer;">';
                        html += '<input type="checkbox" style="cursor:pointer;" />';
                        html += '<span style="font-size:14px; color:#475569;">' + escapeHtml(item) + '</span>';
                        html += '</label>';
                    }});
                    html += '</div>';
                    html += '</div>';
                    html += '</details>';
                }}
                
                contentDiv.innerHTML = html;
            }}
            
            function escapeHtml(text) {{
                var div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }}
            
            // ==================== 개인 맞춤 제안 관련 함수 ====================
            
            // 사용자 정보 가져오기 (실제 DB 데이터 활용)
            function getPersonInfo(personId) {{
                // groupMemberDetails에서 해당 ID의 정보 찾기
                var person = groupMemberDetails.find(function(m) {{
                    return m.id === personId;
                }});
                
                if (person) {{
                    return {{
                        "id": person.id,
                        "name": person.name || person.id,  // name이 없으면 ID 사용
                        "personalities": {{
                            "EI": person.Score_EI || 0.5,
                            "SN": person.Score_SN || 0.5,
                            "TF": person.Score_TF || 0.5,
                            "JP": person.Score_JP || 0.5
                        }},
                        "stamina": person.Stamina || 0.5,
                        "alcohol": person.Alcohol || 0.5
                    }};
                }}
                
                // 찾지 못한 경우 기본값 반환
                return {{
                    "id": personId,
                    "name": personId,
                    "personalities": {{"EI": 0.5, "SN": 0.5, "TF": 0.5, "JP": 0.5}},
                    "stamina": 0.5,
                    "alcohol": 0.5
                }};
            }}
            
            function generatePersonalRecommendations() {{
                console.log('generatePersonalRecommendations 호출됨');
                // 일정이 없으면 안 됨
                if (!globalItinerary) {{
                    console.log('일정 정보 없음');
                    document.getElementById('personal-rec-error').textContent = '먼저 여행 일정을 생성해주세요.';
                    document.getElementById('personal-rec-error').style.display = 'block';
                    return;
                }}
                
                console.log('개인 맞춤 제안 렌더링');
                document.getElementById('personal-rec-loading').style.display = 'block';
                document.getElementById('personal-rec-error').style.display = 'none';
                document.getElementById('personal-rec-tabs').innerHTML = '';
                document.getElementById('personal-rec-content').innerHTML = '';
                
                // 이미 받아온 personal_recommendations가 있는지 확인
                if (globalItinerary.personal_recommendations) {{
                    console.log('이미 받아온 개인 맞춤 제안 사용:', globalItinerary.personal_recommendations);
                    
                    // 포맷 변환: 객체 → 배열
                    var results = [];
                    for (var personId in globalItinerary.personal_recommendations) {{
                        results.push({{
                            personId: personId,
                            data: {{
                                ok: true,
                                data: {{
                                    person_id: personId,
                                    suggestions: globalItinerary.personal_recommendations[personId].suggestions || []
                                }}
                            }}
                        }});
                    }}
                    
                    document.getElementById('personal-rec-loading').style.display = 'none';
                    renderPersonalRecommendations(results);
                }} else {{
                    console.log('개인 맞춤 제안이 없어서 API 호출');
                    // 기존 API 호출 로직 (fallback)
                    var promises = groupMemberIds.map(personId => {{
                        var personInfo = getPersonInfo(personId);
                        console.log('API 호출 준비:', personId, personInfo.name);
                        
                        return fetch('/api/generate-personal-recommendations', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{
                                person_id: personId,
                                person_name: personInfo.name,
                                person_info: personInfo,
                                group_members: groupMemberIds.map(id => getPersonInfo(id).name),
                                group_info: globalGroupInfo,
                                itinerary: globalItinerary,
                                destination: globalDestination
                            }})
                        }})
                        .then(res => {{
                            console.log('API 응답 받음:', personId, res.status);
                            return res.json();
                        }})
                        .then(data => {{
                            console.log('API 데이터 파싱:', personId, data);
                            return {{
                                personId: personId,
                                data: data
                            }};
                        }})
                        .catch(err => {{
                            console.error('API 호출 실패:', personId, err);
                            return {{
                                personId: personId,
                                error: err.message
                            }};
                        }});
                    }});
                    
                    Promise.all(promises).then(results => {{
                        console.log('모든 개인 맞춤 제안 생성 완료:', results);
                        document.getElementById('personal-rec-loading').style.display = 'none';
                        renderPersonalRecommendations(results);
                    }}).catch(err => {{
                        console.error('개인 맞춤 제안 생성 실패:', err);
                        document.getElementById('personal-rec-loading').style.display = 'none';
                        document.getElementById('personal-rec-error').textContent = '개인 맞춤 제안 생성 중 오류가 발생했습니다: ' + err.message;
                        document.getElementById('personal-rec-error').style.display = 'block';
                    }});
                }}
            }}
            
            function renderPersonalRecommendations(results) {{
                console.log('renderPersonalRecommendations 호출됨, results:', results);
                var tabsDiv = document.getElementById('personal-rec-tabs');
                var contentDiv = document.getElementById('personal-rec-content');
                
                console.log('tabsDiv:', tabsDiv, 'contentDiv:', contentDiv);
                
                // 탭 영역 비우기
                tabsDiv.innerHTML = '';
                
                // 아코디언 방식으로 렌더링
                var accordionHtml = '';
                
                results.forEach((result, idx) => {{
                    var personId = result.personId;
                    
                    // 각 유저별 아코디언 블록
                    accordionHtml += '<div style="margin-bottom:12px; border:1px solid #e2e8f0; border-radius:8px; overflow:hidden;">';
                    
                    // 유저 이름 헤더 (클릭 가능) - 실제 이름 표시
                    var personInfo = getPersonInfo(personId);
                    var displayName = personInfo.name || personId;
                    
                    accordionHtml += '<button onclick="togglePersonAccordion(' + idx + ')" style="width:100%; padding:16px; background:#f8fafc; border:none; text-align:left; cursor:pointer; display:flex; justify-content:space-between; align-items:center; font-weight:600; font-size:15px; color:#1e293b; transition:background 0.2s;" onmouseover="this.style.background=\\'#f1f5f9\\'" onmouseout="this.style.background=\\'#f8fafc\\'">';
                    accordionHtml += '<span>👤 ' + escapeHtml(displayName) + '</span>';
                    accordionHtml += '<span id="accordion-icon-' + idx + '" style="font-size:18px; transition:transform 0.3s;">▼</span>';
                    accordionHtml += '</button>';
                    
                    // 제안 컨텐츠 (처음엔 숨김)
                    accordionHtml += '<div id="accordion-content-' + idx + '" style="display:none; padding:16px; background:#fff;">';
                    
                    if (result.error) {{
                        accordionHtml += '<div style="color:#dc2626; padding:16px; background:#fee2e2; border-radius:8px; border:1px solid #fca5a5;">';
                        accordionHtml += '오류: ' + escapeHtml(result.error);
                        accordionHtml += '</div>';
                    }} else if (result.data.ok) {{
                        var recData = result.data.data;
                        if (recData.suggestions && Array.isArray(recData.suggestions)) {{
                            recData.suggestions.forEach((suggestion, sIdx) => {{
                                accordionHtml += '<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:16px; margin-bottom:12px;">';
                                
                                // Day 정보와 현재 일정
                                accordionHtml += '<div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">';
                                accordionHtml += '<span style="display:inline-block; background:#2563eb; color:#fff; padding:3px 10px; border-radius:5px; font-weight:700; font-size:11px;">Day ' + suggestion.day + '</span>';
                                accordionHtml += '<span style="font-size:12px; color:#64748b;">현재: ' + escapeHtml(suggestion.current_activity) + '</span>';
                                accordionHtml += '</div>';
                                
                                // 제안 타입 배지
                                var typeLabel = suggestion.modification_type === 'addition' ? '추가 제안' 
                                              : suggestion.modification_type === 'replacement' ? '변경 제안'
                                              : '대체안';
                                var typeBgColor = suggestion.modification_type === 'addition' ? '#dcfce7'
                                                : suggestion.modification_type === 'replacement' ? '#fef3c7'
                                                : '#fce7f3';
                                var typeTextColor = suggestion.modification_type === 'addition' ? '#15803d'
                                                  : suggestion.modification_type === 'replacement' ? '#a16207'
                                                  : '#be185d';
                                
                                accordionHtml += '<div style="display:inline-block; background:' + typeBgColor + '; color:' + typeTextColor + '; padding:3px 10px; border-radius:5px; font-weight:600; font-size:11px; margin-bottom:10px;">' + typeLabel + '</div>';
                                
                                // 제안 내용
                                accordionHtml += '<div style="background:#fff; border-left:3px solid #3b82f6; padding:10px 12px; border-radius:4px; margin-bottom:10px;">';
                                accordionHtml += '<p style="margin:0; font-size:13px; color:#334155; line-height:1.6;">' + escapeHtml(suggestion.suggestion) + '</p>';
                                accordionHtml += '</div>';
                                
                                // 이유
                                accordionHtml += '<div style="color:#64748b; font-size:12px; margin-top:8px;">';
                                accordionHtml += '<strong style="color:#475569;">💡 이유:</strong> ' + escapeHtml(suggestion.reason);
                                accordionHtml += '</div>';
                                
                                accordionHtml += '</div>';
                            }});
                        }} else {{
                            accordionHtml += '<p style="color:#64748b; font-size:13px;">제안이 없습니다.</p>';
                        }}
                    }} else {{
                        accordionHtml += '<div style="color:#dc2626; padding:16px; background:#fee2e2; border-radius:8px; border:1px solid #fca5a5;">';
                        accordionHtml += '오류: ' + escapeHtml(result.data.error || '알 수 없는 오류');
                        accordionHtml += '</div>';
                    }}
                    
                    accordionHtml += '</div>'; // accordion-content 종료
                    accordionHtml += '</div>'; // 아코디언 블록 종료
                }});
                
                console.log('accordionHtml 생성 완료, 길이:', accordionHtml.length);
                console.log('accordionHtml 일부:', accordionHtml.substring(0, 200));
                contentDiv.innerHTML = accordionHtml;
                console.log('contentDiv에 HTML 설정 완료');
            }}
            
            function togglePersonAccordion(idx) {{
                var content = document.getElementById('accordion-content-' + idx);
                var icon = document.getElementById('accordion-icon-' + idx);
                
                if (content.style.display === 'none') {{
                    // 열기
                    content.style.display = 'block';
                    icon.style.transform = 'rotate(180deg)';
                }} else {{
                    // 닫기
                    content.style.display = 'none';
                    icon.style.transform = 'rotate(0deg)';
                }}
            }}
            
            // 첫번째 탭 자동 활성화 및 여행 일정 자동 생성
            document.addEventListener('DOMContentLoaded', function() {{
                document.querySelectorAll('.member-detail').forEach(function(detail) {{
                    var tabs = detail.querySelectorAll('.inner-tab');
                    var conts = detail.querySelectorAll('.inner-tab-content');
                    if (tabs.length > 0 && conts.length > 0) {{
                        tabs[0].classList.add('active');
                        conts[0].style.display = 'block';
                    }}
                }});
                
                // 여행 일정 자동 생성
                generateItinerary();
            }});
        </script>
    </body>
    </html>
    '''
    return html

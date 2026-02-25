# =========================================================
# TraVTI WHI v0.9
# - Score -> State Code -> Resource JSON -> Report Build
# - Deterministic (No LLM, variant-based)
# - Anchor score 유지 + 모든 pair 리포트 노출
# =========================================================

import json
import random
from dataclasses import dataclass
from itertools import combinations
from typing import Dict, List, Optional, Any

import pandas as pd


# =========================================================
# 1) Configuration
# =========================================================
USE_CALIBRATION = True
MIN_SCORE_FLOOR = 35.0

DEFAULT_TONE = "NEUTRAL"        # NEUTRAL / CARE / WARN
DEFAULT_ANCHOR_TYPE = "NONE"   # NONE / PARENT / COUPLE / VIP

INT_LOW_TH = 0.222
INT_HIGH_TH = 0.778

STAMINA_LOW_TH = 0.25
STAMINA_MID_TH = 0.50

DRINKER_TH = 0.5


# =========================================================
# 2) Data Model
# =========================================================
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


# =========================================================
# 3) Repository
# =========================================================
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


# =========================================================
# 4) Resource Manager (variant support)
# =========================================================
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


# =========================================================
# 5) WHI Calculator
# =========================================================
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


# =========================================================
# 6) Report Builder
# =========================================================
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


# =========================================================
# 7) Main
# =========================================================
if __name__ == "__main__":
    CSV_FILE = "travis_final_1000_personas_20260128.csv"
    INPUT_IDS = ["TRV-NEW-0001", "TRV-NEW-0005", "TRV-NEW-0006"]
    ANCHOR_ID = "TRV-NEW-0001"
    ANCHOR_TYPE = "PARENT"
    TONE = "NEUTRAL"

    users = CSVRepository(CSV_FILE).fetch_users(INPUT_IDS)

    result = WHICalculator.get_group_result(users, ANCHOR_ID, ANCHOR_TYPE, TONE)

    rm = ResourceManager()
    rm.load_json("/content/resources/state_group_text.json")
    rm.load_json("/content/resources/state_personality_core_text.json")
    rm.load_json("/content/resources/state_personality_tone_text.json")
    rm.load_json("/content/resources/anchor_context_text.json")
    rm.load_json("/content/resources/state_stamina_alcohol_text.json")

    report = ReportBuilder(rm).build(result, ANCHOR_TYPE, TONE)
    print(json.dumps(report, ensure_ascii=False, indent=2))

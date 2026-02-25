아래 내용은 **코파일럿 에이전트에게 그대로 복붙**해서 “이 코드/리소스 구조를 이해하고 수정·확장할 수 있게” 만드는 목적의 **설명용 MD**입니다. (프로젝트 문서/리소스 구조 근거 포함)

---

# TraVTI WHI v0.9 — 계산 → 상태코드 → 리소스 조합 → 리포트 생성 흐름 (Copilot Agent용)

## 0) 전체 파이프라인 한 줄 요약

1. **CSV에서 유저 벡터 로드**(EI/SN/TF/JP, Stamina, Alcohol)
2. **모든 pair(조합)**에 대해 **WHI_pair** 계산 + 리스크 코드 생성
3. **그룹 WHI_group** 계산(Anchor 유무에 따라 Mode A/B)
4. **WHI_group을 score bin으로 바꾸고 group_state_code 생성**
5. state_code들을 **리소스 JSON에서 문장으로 조회**하고, 레이어(톤/코어/앵커) 합쳐 **리포트 JSON 출력**

---

## 1) WHI 계산이 어떻게 되는지 (Pairwise WHI)

### 1.1 입력 값 (User)

각 유저는 아래를 가진다.

* `personalities`: `EI, SN, TF, JP` (0.0~1.0 정규화 값)
* `stamina`: 0.0~1.0
* `alcohol`: 0.0~1.0
* `is_anchor`: (그룹 계산 단계에서 지정됨)
* `is_drinker`: `alcohol >= 0.5`이면 True

> 설문/정규화 논리 자체는 “TraVTI 수정본”에 정의된 방식(문항별 점수 → 축별 합산 → 0~1 정규화)을 전제로 한다. 
> WHI 알고리즘의 철학/모드/벌점 규칙은 “TraVTI WHI v0.9” 문서에 정의돼 있다. 

---

### 1.2 성향(65%) 점수 계산: “등급 규칙(Grade Rules) → 가중합 → 정규화”

#### (A) 차원별 diff 계산

각 성향 축 `d ∈ {EI,SN,TF,JP}`에 대해:

* `a = u1.personalities[d]`
* `b = u2.personalities[d]`
* `diff = abs(a - b)`

#### (B) diff를 등급으로 매핑 (GRADE_RULES)

코드에는 아래 규칙을 순서대로 적용한다:

* `S+` : +18

  * 조건: `diff <= 0.111` **AND** (둘 다 High(>0.5) 또는 둘 다 Low(<=0.5))
* `S-` : +12

  * 조건: `diff <= 0.111`
* `C+` : +8

  * 조건: `diff <= 0.333`
* `N`  : +3

  * 조건: `diff <= 0.444`
* `W1` : -4

  * 조건: `diff <= 0.667`
* `W2` : -9

  * 조건: `diff < 1.0`
* `X`  : -15

  * 조건: `diff >= 1.0` (즉 diff==1.0)

> 이 규칙 체계(차이+강도 기반 등급화, W1/W2/X 리스크 강조)는 문서 정의와 동일한 컨셉이다. 

#### (C) 앵커가 포함된 pair의 “벌점 민감도”

pair 계산 중 `role = "ANCH"` 조건(둘 중 한 명이라도 anchor)이면:

* **점수가 음수인 경우(W1/W2/X 같은 벌점)**만 `score * 1.2`
* 양수 시너지(S+, S-, C+, N)는 증폭하지 않음

→ 문서의 “부모/의전 앵커는 리스크를 더 크게 체감” 가정과 일치 

#### (D) 차원 가중치(DIM_WEIGHTS)로 합산

각 축 등급 점수를 다음 가중치로 합산:

* EI 0.35
* SN 0.25
* TF 0.20
* JP 0.20

코드상 계산:

* `total += (final_grade_point) * w`

#### (E) “리스크 코드” 생성 (성향 문장용)

등급이 `W1/W2/X`인 경우만 personality 리스크 코드가 생성된다.

* 코드 포맷:
  `P__DIM_{dim}__RISK_{W1|W2|X}__INT_{LOW|MID|HIGH}`

여기서 INT는 diff에 의해 결정:

* `LOW` : diff ≤ 0.222
* `MID` : 0.222 < diff < 0.778
* `HIGH`: diff ≥ 0.778

> 이 “성향 코어 코드 목록”은 별도 JSON에 존재한다. 

---

### 1.3 체력(25%) 점수 계산: Stamina sync

코드에서는 체력 점수를 단순히:

* `s_norm = max(0, min(1, (1 - abs(u1.stamina - u2.stamina))))`

즉,

* stamina가 같을수록 1에 가깝고,
* 차이가 클수록 0에 가까워짐.

추가로 “체력 차이 상태코드”를 만든다:

* `absdiff = abs(u1.stamina - u2.stamina)`
* `LOW` : absdiff < 0.25
* `MID` : absdiff < 0.50
* `HIGH`: 그 외

코드 포맷:

* `S__DIFF_{LOW|MID|HIGH}__ROLE_{ANCH|NON}__TONE_{tone}`

> 체력/음주 코드 스펙은 JSON에 정리되어 있다. 

---

### 1.4 음주(10%) 점수 계산: drinker match

코드에서는 “둘 다 drinker or 둘 다 non-drinker”면 1, 아니면 0:

* `a_norm = 1 if u1.is_drinker == u2.is_drinker else 0`

음주 mismatch인 경우만 코드 생성:

* `A__TYPE_MISMATCH__ROLE_{ANCH|NON}__TONE_{tone}`

> 음주 코드 스펙은 JSON에 정리되어 있다. 

---

### 1.5 최종 WHI_pair: 65/25/10 가중합 → 0~100 → (선택) 보정

#### (A) 성향 총점(total)을 0~1로 정규화

코드:

* `p_norm = clamp((total + 15) / 33, 0, 1)`

(여기서 `total`의 범위를 -15~+18 근처로 가정하고 0~1로 매핑하는 구조)

#### (B) 최종 raw WHI

* `raw = 100 * (0.65 * p_norm + 0.25 * s_norm + 0.10 * a_norm)`

#### (C) calibrate(점수 보정)

`USE_CALIBRATION=True`이면:

* `final_whi = MIN_SCORE_FLOOR + (100 - MIN_SCORE_FLOOR) * (raw / 100)`
* default: `MIN_SCORE_FLOOR = 35.0`

즉, raw가 0이어도 최종은 35로 “바닥을 깔아주는” 형태.

---

## 2) 계산된 WHI에서 state_code가 어떻게 나오나 (Group State Code)

### 2.1 모든 pair 계산

그룹 유저가 N명이라면, `combinations(users, 2)`로 **N*(N-1)/2 개 pair**를 만들고 위 `WHI_pair`를 전부 계산한다.

결과는 각 pair마다:

* pair id 2개
* final_whi
* role (ANCH/NON)
* personality_codes (W1/W2/X만 들어있음)
* stamina_code
* alcohol_code (mismatch 때만)

---

### 2.2 그룹 점수 WHI_group 계산: Anchor 유무로 Mode 결정

#### Mode B (Anchor가 있음)

* anchor_id가 실제 멤버 중 존재하면 anchor로 지정
* anchor가 포함된 pair만 골라서 평균을 냄

코드:

* `group_whi = avg(whi of anchor_pairs)`
* `mode = "B"`
* anchor_pairs는 리포트의 `anchor_relations`로 별도 노출됨
* anchor가 아닌 멤버끼리 pair는 `member_relations`로 노출됨

> 문서에서도 “1인 앵커 모드 = 앵커 만족도 평균이 그룹점수”로 설명한다. 

#### Mode A (Anchor가 없음)

* 모든 pair 점수 중:

  * `min(scores)` 70%
  * `avg(scores)` 30%
* `group_whi = 0.7*min + 0.3*avg`
* `mode="A"`

> 문서의 Mode A 정의와 동일 컨셉. 

---

### 2.3 group_state_code 생성 규칙

코드:

* `state_code = f"G__MODE_{mode}__SCORE_{int(group_whi // 10 * 10)}__ANCH_{anchor_type}__TONE_{tone}"`

즉,

* MODE: A 또는 B (현재 코드상 C는 구현 안됨)
* SCORE: `group_whi`를 10점 단위로 내림 (예: 67.6 → 60)
* ANCH: anchor_type (NONE/PARENT/COUPLE/VIP)
* TONE: tone (NEUTRAL/CARE/WARN)

> 그룹 코드 스펙 자체는 group 리소스 JSON에 존재한다. 

⚠️ **중요: 현재 코드의 SCORE bin 포맷이 리소스와 불일치 가능**

* 코드: `SCORE_90`, `SCORE_80`, `SCORE_70`, ...
* 리소스 예시: `SCORE_90P`, `SCORE_80`, `SCORE_70`, ... (90P 같은 특수 bin이 존재) 
  → **에이전트가 먼저 해야 할 것:** group_state_code의 SCORE bin 규칙을 리소스와 맞추기
  (예: 90 이상이면 `90P`, 80~89면 `80`, …, 50 미만이면 `LT50` 같은 방식으로)

---

## 3) JSON 리소스를 어떻게 조합해서 리포트를 짜는지 (Resource Layering)

### 3.1 ResourceManager: “code → 텍스트 variants” 조회기

ResourceManager는 여러 JSON 파일을 로드해서 `self.map[code] = [variants...]` 형태로 합친다.

* 각 JSON item은 최소 `"code"`를 가진다.
* text는 두 가지 형태를 지원:

  * `"text_variants": [ ... ]`  → variant 랜덤 선택
  * `"text": "..."` → 단일 문장

`get(code)`는 해당 code의 variant 중 하나를 랜덤으로 반환(시드 넣으면 재현 가능).

---

### 3.2 리소스 레이어(파일) 구조

리포트 문장은 한 파일에서 “완성 문장”을 가져오는게 아니라, **레이어를 합쳐서** 만든다.

현재 로딩하는 레이어는 5종:

1. `state_group_text.json`

   * 그룹 요약 code(`G__MODE_...`) → 그룹 한 문단
   * 스펙: group code 목록 

2. `state_personality_core_text.json`

   * 성향 리스크 code(`P__DIM_...__RISK_...__INT_...`) → “갈등/조정 포인트” 사실문
   * 스펙: personality core code 목록 

3. `state_personality_tone_text.json`

   * 성향 문장 앞/뒤에 붙는 “말투/완충” 레이어
   * 코드: `P__ROLE_{ANCH|NON}__TONE_{NEUTRAL|CARE|WARN}` 

4. `anchor_context_text.json`

   * 앵커 관계 맥락(부모/커플/VIP) 렌즈 레이어
   * 코드: `ANCH_{PARENT|VIP|COUPLE}__TONE_{...}` 

5. `state_stamina_alcohol_text.json`

   * 체력/음주 관련 안내 문장
   * 코드: `S__DIFF_...__ROLE_...__TONE_...`, `A__TYPE_...__ROLE_...__TONE_...` 

---

### 3.3 Pair 리포트에서 “성향 문장”을 만드는 조합 규칙

ReportBuilder의 핵심은 `_compose_personality()`.

입력:

* `codes`: (해당 pair에서 나온 personality_codes 리스트)

  * 주의: W1/W2/X만 들어오며, 0개일 수도 있음
* `role`: "ANCH" or "NON" (pair에 anchor 포함 여부)
* `anchor_type`: PARENT/COUPLE/VIP/NONE
* `tone`: NEUTRAL/CARE/WARN

각 리스크 코드 c에 대해 아래 3개를 붙인다:

1. 톤 레이어: `P__ROLE_{role}__TONE_{tone}`
2. 코어 레이어: `c` (예: `P__DIM_JP__RISK_W2__INT_HIGH`)
3. 앵커 렌즈: `ANCH_{anchor_type}__TONE_{tone}` (anchor_type이 NONE이 아니면)

즉 한 리스크 포인트는 최종적으로:

> (말투/완충) + (팩트성 리스크 설명) + (관계 렌즈 한줄)

이 3파트를 공백으로 합친 뒤, 리스크 포인트가 여러 개면 `_merge()`로 다시 합친다.

#### `_merge()` 동작

* 문장이 1개면 그대로 반환
* 여러 개면 맨 앞에 고정 프리픽스를 붙임:

  * `"여행을 함께하는 과정에서 몇 가지 차이가 함께 나타날 수 있습니다. " + " ".join(texts)`

---

### 3.4 Pair 리포트에서 “체력/음주 문장” 조합

* stamina 문장: `rm.get(stamina_code)` 그대로
* alcohol 문장: mismatch일 때만 코드가 있으니 `rm.get(alcohol_code)` (없으면 None)

---

### 3.5 최종 report JSON 구조

ReportBuilder.build() 결과는 아래 형태:

```json
{
  "group_whi": 67.6,
  "group": {
    "state_code": "G__MODE_B__SCORE_60__ANCH_PARENT__TONE_NEUTRAL",
    "text": "(group_state_code로 조회한 문장)"
  },
  "anchor_relations": [
    {
      "pair": ["A","B"],
      "final_whi": 66.2,
      "texts": {
        "personality": "(tone+core+anchor_context 합친 문장)",
        "stamina": "(stamina_code 문장)",
        "alcohol": "(alcohol_code 문장 or null)"
      }
    }
  ],
  "member_relations": [ ... ],
  "meta": { "members": ["..."] }
}
```

---

## 4) Copilot Agent가 흔히 실수하는 포인트 (체크리스트)

1. **Group SCORE bin 포맷 불일치 해결**

   * 코드: `SCORE_{int(group_whi//10*10)}`
   * 리소스: `SCORE_90P / 80 / 70 / 60 / 50 / LT50` 같은 이산 bin 
     → group score를 리소스 bin으로 매핑하는 함수가 필요.

2. **personality_core code는 ROLE/TONE이 없다**

   * core는 `P__DIM_...__RISK_...__INT_...`까지만 
   * 말투는 별도 `P__ROLE_...__TONE_...` 레이어가 담당 

3. **Anchor type은 “그룹 맥락”이고 role은 “pair에 anchor 포함 여부”**

   * anchor_type: PARENT/COUPLE/VIP/NONE (UI/시나리오에서 들어오는 값)
   * role: 실제 pair 계산에서 anchor 멤버가 포함되면 ANCH

4. **리소스는 “완성 문장”이 아니라 레이어 합성 결과**

   * 따라서 특정 레이어 문장이 반복되면 리포트 품질이 바로 떨어짐.
   * variant를 충분히 넣는 이유가 여기 있음.

---

## 5) 실행 관점: 이 코드가 “LLM 없이” 리포트를 만드는 방식

* 계산은 전부 deterministic(난수 seed 고정 가능)
* 리포트 품질은:

  1. state_code 설계가 얼마나 촘촘한지
  2. 각 레이어의 문장 variant가 얼마나 잘 분산되는지
  3. 합성 순서(톤→코어→앵커)가 얼마나 “중복 없이 자연스럽게” 이어지는지
     에 의해 결정됨.

---

### 참고: 코드/문서 근거

* WHI v0.9 철학/모드/벌점 정의 
* 설문 문항/정규화 설계(Score 0~1) 
* 톤 레이어 코드 정의 `P__ROLE_*` 
* 앵커 렌즈 레이어 코드 정의 `ANCH_*` 
* 성향 코어 코드 정의 `P__DIM_*` 
* 체력/음주 코드 정의 `S__*`, `A__*` 
* 그룹 코드 정의 `G__*` 

---
리소스들은 전부 state_code_json 폴더 안에 정리되어 있음.



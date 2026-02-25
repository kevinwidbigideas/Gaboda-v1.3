# 현재 그룹 결과 출력 정리 (LLM 제외)

## 범위
- 기준: 현재 실제 라우팅 기준 그룹 결과 화면 (`/itinerary`의 **그룹 리포트 탭**)
- 제외: LLM 생성 결과/프롬프트/모델 응답 로직
- 포함: 
  1) 유저 간 pair 분석 출력 문구
  2) WHI 기반 그룹 리포트 출력 문구
  3) 테마/비주얼(색상, 레이아웃, 컴포넌트 스타일)

---

## 0) 출력 흐름(LLM 제외)
1. `blueprints/result.py`에서 `saveOccasion()` 호출 시 세션에 멤버/앵커 저장
   - `session['itinerary_member_ids']`
   - `session['itinerary_member_stats']`
   - `session['trip_anchor']`
2. 저장 성공 후 `/itinerary` 이동
3. `blueprints/itinerary.py` `show_itinerary()`에서:
   - 세션 기반 사용자 목록 구성
   - `WHICalculator.get_group_result()`로 pair/그룹 점수 계산
   - `ReportBuilder.build()`로 그룹/관계 텍스트 조립
   - HTML 문자열로 그룹 리포트 탭 렌더

---

## 1) 유저 간 pair 분석 출력 (문구/구조)

### 1-1. UI 구조
- 섹션 제목: `멤버별 케미 보기`
- 1차 토글: 멤버 버튼(`👤 {이름}`) 클릭 시 상세 열림/닫힘
- 2차 탭: 해당 멤버와의 상대 멤버 탭 버튼
- 탭 콘텐츠: 각 pair별 요약 + 코멘트 + (선택)리소스 문구

### 1-2. pair 요약 한줄(WHI 구간 문구)
`pair['final_whi']` 값으로 아래 문구 표시:
- `>= 85`: `최고의 케미!`
- `>= 75`: `아주 잘 맞아요.`
- `>= 65`: `무난하게 어울림.`
- `>= 55`: `보통, 약간 조율 필요.`
- `< 55`: `충돌 가능성, 배려 필요!`

표시 형태:
- `{이름A} & {이름B} {whi_line}`

### 1-3. pair 상세 코멘트(케미/주의)
각 pair에서 성향 차이 계산 후 2줄 고정 출력:
- `케미:` best trait 문구
- `주의:` worst trait 문구

문구 패턴:
- best(차이 작음): `~ 성향이 매우 비슷해요!` / `~ 성향으로 잘 맞아요.` / `~ 부분이 비교적 맞아요.`
- worst(차이 큼): `~ 스타일이 약간 달라요.` / `~ 스타일이 꽤 달라요.` / `~ 스타일이 매우 달라요.`

### 1-4. pair 리소스 문구(선택 출력)
`pair['texts']['personality']`가 있으면 하단에 회색 보조 문구 출력.
이 텍스트는 다음 조합으로 생성:
- `state_personality_tone_text.json` (톤/역할 문구)
- `state_personality_core_text.json` (성향 리스크 코어 문구)
- `anchor_context_text.json` (앵커 타입 컨텍스트)

즉, 현재 pair 분석은 **(고정 규칙 문구 + 리소스 매핑 문구)** 혼합 방식.

---

## 2) WHI 기반 그룹 리포트 출력 (문구/구조)

### 2-1. 상단 주요 출력 항목
`group_html`에서 다음 순서로 표시:
1. `그룹 리포트`
2. `그룹 WHI 점수: {점수}`
3. 6축 레이더 차트(SVG)
4. `한줄평: {whi_comment}`
5. `그룹 요약: {group_text}`
6. `스테미나 평가: {stamina_comment}`
7. `체력 편차: {stamina_gap_comment}`
8. `알콜 성향: {alcohol_comment}`
9. `해시태그: {all_tags}`
10. `멤버: {멤버명 목록}`
11. 멤버별 케미 보기(pair 섹션)

### 2-2. 그룹 한줄평(WHI 구간 문구)
`whi_score` 기준:
- `>= 85`: `케미가 매우 뛰어난 그룹입니다! 서로의 여행 스타일이 잘 맞아요.`
- `>= 75`: `케미가 높은 그룹이에요! 대부분의 상황에서 잘 어울릴 수 있습니다.`
- `>= 65`: `평균 이상의 케미를 가진 그룹입니다. 약간의 조율만 있으면 좋아요.`
- `>= 55`: `보통 수준의 케미입니다. 서로 배려하면 충분히 즐거운 여행이 될 수 있어요.`
- `< 55`: `케미 차이가 큰 그룹입니다. 일정이나 역할 분담에 신경을 써보세요!`

### 2-3. 그룹 요약 문구(`group_text`)
- `ReportBuilder`에서 `group_state_code`로 리소스 조회
- 소스: `llm_resource/state_code_json/state_group_text.json`
- 즉, 점수/모드/앵커/톤 코드에 따라 고정 텍스트 1개 선택

### 2-4. 스태미나/체력 편차 문구
평균 체력(`avg_stamina`) 기준:
- 높음/중상/보통/낮음 4구간 문구 출력

체력 편차(`avg_stamina - min_stamina`) 기준:
- `>= 0.25`: 특정 멤버명 포함 배려 문구
- 그 외: `모든 멤버의 체력이 비슷해서 일정 소화에 큰 무리는 없어 보여요 :)`

### 2-5. 알콜 성향 문구
`drinker_count` 기준:
- 전원 음주: `모든 멤버가 술자리를 즐길 수 있는 그룹입니다.`
- 전원 비음주: `모든 멤버가 비음주자라서, 술 없는 일정도 자연스러워요.`
- 혼합: `음주 성향이 다른 멤버가 섞여 있어요. 서로의 스타일을 존중해 주세요!`

### 2-6. 해시태그 출력
- `all_tags = whi_tags + stamina_tags + stamina_gap_tags + alcohol_tags`
- 그룹 요약 텍스트에서 한글 키워드 추출한 `group_tags` 계산은 있으나, 실제 최종 출력은 `all_tags` 중심

---

## 3) 테마/비주얼 출력 방식

### 3-1. 전체 톤
- 배경: 연한 슬레이트(`body background #f8fafc`)
- 카드형 컨테이너: 흰색 + 둥근 모서리 + 얕은 그림자
- 포인트 컬러: 블루 계열(`#2563eb`, `#3b82f6`)

### 3-2. 그룹 리포트 탭 UI
- 상단 2탭(`그룹 리포트`, `여행 일정`) 구조
- active 탭: 파란색 텍스트/하단 보더
- 멤버 블록: 연한 회색 배경 박스 + 내부 탭
- 내부 탭 active: 파란 배경 + 흰 글자

### 3-3. 레이더 차트(6축 SVG)
축 항목:
- EI: `폭발적 에너지` / `차분한 여유`
- SN: `현실 감각` / `직관적 영감`
- TF: `이성적 판단` / `감성적 공감`
- JP: `계획적 실행` / `유연한 즉흥`
- Stamina: `체력 충만` / `여유로운 템포`
- Alcohol: `흥 넘침` / `맑은 정신`

시각 요소:
- 6색 축 라인(빨강/주황/노랑/초록/파랑/보라)
- 블루-퍼플 그라디언트 폴리곤
- 점 마커 + 컬러 라벨

### 3-4. 스타일 구현 방식
- `itinerary.py` 내 HTML 문자열에 인라인 스타일 + `<style>` 블록 혼합
- 일부 공통 헤더/상단 UI는 `utils.py`의 공통 헤더(`COMMON_HEAD`, `get_header`) 재사용
- 별도 템플릿 파일 분리 없이 서버에서 문자열 렌더링

---

## 4) 참고 코드 위치
- 그룹 결과 메인 렌더: `blueprints/itinerary.py` (`show_itinerary`)
- 세션 저장/이동 시작점: `blueprints/result.py` (`saveOccasion`)
- 문구 리소스:
  - `llm_resource/state_code_json/state_group_text.json`
  - `llm_resource/state_code_json/state_personality_core_text.json`
  - `llm_resource/state_code_json/state_personality_tone_text.json`
  - `llm_resource/state_code_json/anchor_context_text.json`
  - `llm_resource/state_code_json/state_stamina_alcohol_text.json`

---

## 메모
- 현재 그룹 결과 출력은 **규칙 기반 점수 계산 + 상태코드 리소스 매핑 + 하드코딩된 구간 문구**의 조합입니다.
- LLM 호출 없이도 그룹 리포트/페어 분석 문구가 완성되도록 구성되어 있습니다.
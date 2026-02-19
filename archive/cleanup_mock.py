import os

file_path = r"c:\gaboda_v1.3\llm_resource\itinerary_llm_draft\llm_client_draft.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Define start marker
start_marker = '    - DESTINATION-AWARE: Generates location-appropriate restaurants and attractions\n    """'
# Define end marker (start of call_llm)
end_marker = 'def call_llm(prompt: str, api_key: Optional[str] = None, timeout: int = 30) -> Optional[str]:'

# Split
parts = content.split(start_marker)
if len(parts) != 2:
    print(f"Error: Start marker not found. Content length: {len(content)}")
    # Debug: Print around potential area
    exit(1)

pre_part = parts[0] + start_marker
post_part_full = parts[1]

parts2 = post_part_full.split(end_marker)
if len(parts2) != 2:
    print("Error: End marker not found")
    exit(1)

post_part = end_marker + parts2[1]

# New body
new_body = """
    # Simplified DYNAMIC Logic
    days = duration if duration else 2
    
    # Calculate flight times
    airport_departure_time = "13:00"
    if arrival_date:
        import re
        time_match = re.search(r'(\d{1,2}):(\d{2})', arrival_date)
        if time_match:
            arrival_hour = int(time_match.group(1))
            departure_hour = arrival_hour - 4
            if departure_hour < 6: departure_hour = 6
            airport_departure_time = f"{departure_hour:02d}:00"

    itinerary = {"itinerary": []}
    
    # Generic loop
    for day_num in range(1, days + 1):
        activities = []
        is_last_day = (day_num == days)
        h = 10
        
        # 1. Morning / Checkin
        if day_num == 1:
            activities.append({
                "time": f"{h:02d}:30",
                "title": "도착 및 체크인",
                "attraction": "숙소",
                "reason": "여정 시작",
                "link": "https://www.google.com/search?q=hotel"
            })
            h += 2
        else:
            activities.append({
                "time": "09:00",
                "title": "아침 식사",
                "attraction": f"{destination} 조식 맛집",
                "reason": "하루 시작",
                "link": f"https://www.google.com/search?q={destination}+breakfast"
            })
            
        # 2. Morning Spot
        activities.append({
            "time": f"{h:02d}:00",
            "title": "오전 관광",
            "attraction": f"{destination} 주요 명소 {day_num}",
            "reason": "관광",
            "link": f"https://www.google.com/search?q={destination}+attractions"
        })
        h += 3
        
        # 3. Lunch
        activities.append({
            "time": f"{h:02d}:00",
            "title": "점심 식사",
            "attraction": f"{destination} 점심 맛집 {day_num}",
            "reason": "점심",
            "link": f"https://www.google.com/search?q={destination}+lunch"
        })
        h += 2
        
        # 4. Afternoon
        if not is_last_day:
             activities.append({
                "time": f"{h:02d}:00",
                "title": "오후 액티비티",
                "attraction": f"{destination} 핫플레이스 {day_num}",
                "reason": "오후 활동",
                "link": f"https://www.google.com/search?q={destination}+place"
            })
             h += 4
             
             # 5. Dinner
             activities.append({
                 "time": "19:00",
                 "title": "저녁 식사",
                 "attraction": f"{destination} 디너 맛집 {day_num}",
                 "reason": "저녁",
                 "link": f"https://www.google.com/search?q={destination}+dinner"
             })
        else:
             # Last day departure
             activities.append({
                 "time": airport_departure_time,
                 "title": "공항 이동",
                 "attraction": "공항",
                 "reason": "귀국",
                 "link": "https://www.google.com/search?q=airport"
             })

        itinerary['itinerary'].append({
            "day": day_num, 
            "activities": activities
        })
    
    return itinerary

"""

new_content = pre_part + new_body + "\n\n" + post_part

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Successfully updated mock generator.")

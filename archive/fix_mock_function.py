import re

file_path = r"c:\gaboda_v1.3\llm_resource\itinerary_llm_draft\llm_client_draft.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Pattern to match the function signature and docstring
# We want to keep signature and docstring
# But replace the body.
# Signature: def _mock_itinerary_from_prompt(...
# Docstring ends with """

# Let's find the start of the function
start_func = content.find("def _mock_itinerary_from_prompt")
if start_func == -1:
    print("Could not find function start")
    exit(1)

# Find the start of the next function
end_func = content.find("def call_llm", start_func)
if end_func == -1:
    print("Could not find next function start")
    exit(1)

# Now look for the end of the docstring inside this range
# The docstring starts after signature.
docstring_end_marker = '    - DESTINATION-AWARE: Generates location-appropriate restaurants and attractions\n    """'
docstring_end_pos = content.find(docstring_end_marker, start_func)

if docstring_end_pos == -1:
    # Try finding just """ if the text doesn't match exactly due to line endings
    print("Could not find specific docstring end marker, trying generic search")
    # There should be a """ after the function start
    # The first """ is start of docstring, second is end.
    first_triple = content.find('"""', start_func)
    second_triple = content.find('"""', first_triple + 3)
    if second_triple == -1 or second_triple > end_func:
         print("Could not find docstring end")
         exit(1)
    docstring_end_pos = second_triple
    # Include the quotes
    docstring_end_pos += 3
else:
    # Include the length of marker
    docstring_end_pos += len(docstring_end_marker)


# Body to insert
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

pre_part = content[:docstring_end_pos]
post_part = content[end_func:]

# Construct new content
new_content = pre_part + new_body + "\n\n" + post_part

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Replaced content from index {docstring_end_pos} to {end_func}")

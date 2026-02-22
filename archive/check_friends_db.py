import sqlite3

DB_PATH = r"C:\temp\travis.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 친구 이름 검색
friends = ['재혁', '혁수', 'kevin', '민웅']

for friend in friends:
    cursor.execute("SELECT ID, TraVTI_Label FROM survey_responses WHERE ID = ?", (friend,))
    row = cursor.fetchone()
    if row:
        print(f"✓ {friend}: ID={row[0]}, TraVTI_Label={row[1]}")
    else:
        print(f"✗ {friend}: 찾을 수 없음")

# 모든 행 출력 (처음 20개)
print("\n=== 모든 행 ===")
cursor.execute("SELECT ID, TraVTI_Label FROM survey_responses LIMIT 20")
for row in cursor.fetchall():
    print(f"ID: {row[0]:<20} | TraVTI_Label: {row[1]}")

conn.close()

"""
Flask 애플리케이션 초기화 및 설정
"""
from flask import Flask, g, session
import sqlite3
import os
import secrets

# Flask 앱 초기화
app = Flask(__name__)
# 세션 데이터를 암호화하기 위한 시크릿 키 설정
app.secret_key = "gaboda_secret"
_SERVER_NONCE = secrets.token_hex(16)

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


@app.before_request
def _reset_session_on_restart():
    if session.get('_server_nonce') != _SERVER_NONCE:
        session.clear()
        session['_server_nonce'] = _SERVER_NONCE

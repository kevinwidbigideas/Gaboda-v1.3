"""
Flask 애플리케이션 초기화 및 설정
"""
from flask import Flask, g, session, request, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client

import os
import secrets

# Flask 앱 초기화
# Flask 앱 초기화
app = Flask(__name__)
# 세션 데이터를 암호화하기 위한 시크릿 키 설정
app.secret_key = "gaboda_secret"
_SERVER_NONCE = secrets.token_hex(16)

# Load environment variables
load_dotenv()

# Supabase Client Initialization
supabase_url: str = os.environ.get("SUPABASE_URL")
supabase_key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = None
if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"Supabase init failed: {e}")


@app.before_request
def _reset_session_on_restart():
    if session.get('_server_nonce') != _SERVER_NONCE:
        session.clear()
        session['_server_nonce'] = _SERVER_NONCE

# Attach Supabase to app for blueprints to use
app.supabase = supabase

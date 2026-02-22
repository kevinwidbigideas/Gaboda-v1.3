"""
로그인 유도 프롬프트 라우트
"""
from flask import Blueprint, render_template_string
from utils import COMMON_HEAD, get_header

auth_prompt_bp = Blueprint('auth_prompt', __name__)

AUTH_PROMPT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    {{ common_head|safe }}
    <title>잠시만요!</title>
</head>
<body class="bg-slate-50 min-h-screen flex flex-col">
    {{ header|safe }}
    
    <main class="flex-grow flex flex-col items-center justify-center p-6">
        <!-- Title Section -->
        <div class="text-center mb-10">
            <div class="inline-block p-4 bg-white rounded-full shadow-sm mb-4">
                <span class="material-symbols-outlined text-6xl text-blue-500">how_to_reg</span>
            </div>
            <h1 class="text-3xl font-bold text-slate-800">Travis와의 첫 여행이 끝났네요.</h1>
        </div>

        <!-- Card Section -->
        <div class="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center">
            <div class="mb-8">
                <p class="text-lg text-slate-800 font-medium mb-2">이제 여행 시나리오에 기반한<br>당신의 여행 페르소나를 분석합니다.</p>
                <p class="text-xl font-bold text-blue-600">결과 페이지를 선택하세요.</p>
            </div>
            
            <div class="space-y-4">
                <!-- Option 1: Login -->
                <div class="p-4 border-2 border-blue-100 rounded-xl bg-blue-50 hover:border-blue-300 transition-colors text-left cursor-pointer" onclick="document.getElementById('login-modal').classList.remove('hidden')">
                    <div class="flex items-start gap-3">
                        <span class="material-symbols-outlined text-blue-600 mt-1">lock_open</span>
                        <div>
                            <h3 class="font-bold text-slate-800">로그인/회원가입 하고 상세 분석 결과 보기</h3>
                            <ul class="text-sm text-slate-600 mt-2 space-y-1 list-disc list-inside">
                                <li>친구들과 여행 케미 비교 기능</li>
                                <li>3인 이상의 친구들과 상세 그룹 분석 리포트</li>
                                <li>나의 여행 유형 상세 분석 리포트</li>
                                <li class="relative group cursor-help">
                                    <span class="text-blue-600 font-bold underline decoration-dotted underline-offset-2">Travis 서비스 얼리엑세스 코드 제공!</span>
                                    <!-- Tooltip -->
                                    <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 p-3 bg-slate-800 text-white text-xs rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 text-left pointer-events-none">
                                        <div class="font-bold text-blue-300 mb-1 pb-1 border-b border-slate-600">얼리엑세스 혜택은?</div>
                                        <ul class="space-y-1.5 list-disc list-inside text-slate-200">
                                            <li>Travis 테스트 기간에 테스터로 초대</li>
                                            <li>Travis 서비스 시 회원등급 업그레이드</li>
                                            <li>Travis의 각종 프로모션 제일 먼저 지급</li>
                                            <li>그 외 다양한 혜택 제공</li>
                                        </ul>
                                        <!-- Arrow -->
                                        <div class="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-slate-800"></div>
                                    </div>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>

                <!-- Option 2: Skip -->
                <a href="/result" class="block p-4 border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors text-left">
                    <div class="flex items-center gap-3">
                        <span class="material-symbols-outlined text-slate-400">arrow_forward</span>
                        <div>
                            <h3 class="font-semibold text-slate-700">회원가입 없이 바로 결과 보기</h3>
                            <p class="text-xs text-slate-500 mt-1">친구 케미 비교 및 상세 분석은 제공되지 않습니다.</p>
                        </div>
                    </div>
                </a>
            </div>
        </div>
    </main>
</body>
</html>
"""

@auth_prompt_bp.route('/auth-prompt')
def auth_prompt():
    """로그인 유도 프롬프트 페이지"""
    return render_template_string(AUTH_PROMPT_TEMPLATE, 
                                common_head=COMMON_HEAD, 
                                header=get_header('auth_prompt'))

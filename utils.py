"""
공용 유틸리티 및 헬퍼 함수
"""
import random
import os

# ========================================
# 공통 HTML 헤더 (모든 페이지에서 사용)
# ========================================
COMMON_HEAD = """
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700;800;900&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,typography,container-queries"></script>
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<style>body { font-family: 'Pretendard', sans-serif; }</style>
"""

import uuid
def generate_next_id():
    """고유한 새 ID를 생성합니다"""
    return f"TRV-NEW-{uuid.uuid4().hex[:8].upper()}"

def get_header(current_page):
    """현재 페이지에 따른 네비게이션 헤더 반환"""
    hamburger_btn_html = ""
    sidebar_html = ""

    if current_page != 'test':
        hamburger_btn_html = """
                    <button id="menu-toggle-header" class="p-2 rounded-md hover:bg-slate-100">
                        <span class="flex flex-col gap-1 items-center">
                            <span class="block w-6 h-0.5 bg-slate-800 rounded"></span>
                            <span class="block w-6 h-0.5 bg-slate-800 rounded"></span>
                            <span class="block w-6 h-0.5 bg-slate-800 rounded"></span>
                        </span>
                    </button>"""

        sidebar_html = """
    <div id="sidebar-backdrop-common" class="fixed inset-0 bg-black/40 backdrop-blur-sm z-[90] hidden opacity-0 transition-opacity duration-300"></div>

    <aside id="sidebar-common" class="fixed top-0 right-0 h-full w-full sm:w-[360px] bg-white z-[100] translate-x-full transition-transform duration-300 ease-in-out shadow-2xl overflow-y-auto">
        <div class="p-6">
                <div class="flex justify-end mb-6">
                <button id="close-menu-common" class="p-1 text-gray-500 hover:text-black text-2xl font-bold">X</button>
            </div>
            <div class="px-2">
                <a id="header-login-btn" href="/login" class="block text-lg font-medium mb-6 text-gray-800 cursor-pointer hover:text-blue-500 transition-colors">로그인 / 회원가입</a>
                <div id="user-id-display" class="hidden mb-6">
                    <div class="rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50 to-white p-4 shadow-sm">
                        <div class="flex items-start justify-between gap-3">
                            <div>
                                <div class="text-[11px] font-bold text-blue-500 mb-1">WELCOME</div>
                                <span id="user-id-text" class="block text-lg font-bold text-slate-800">로그인</span>
                            </div>
                            <a id="my-travti-link" href="/my-info-edit" class="text-xs font-bold text-blue-600 hover:text-blue-700">내 정보 수정</a>
                        </div>
                        <div class="mt-3 flex flex-wrap gap-2">
                            <span id="sidebar-travti-chip" class="hidden px-2.5 py-1 rounded-full text-[11px] font-bold bg-indigo-50 text-indigo-600 border border-indigo-100"></span>
                            <span id="sidebar-mbti-chip" class="hidden px-2.5 py-1 rounded-full text-[11px] font-bold bg-blue-50 text-blue-600 border border-blue-100"></span>
                            <a id="sidebar-test-chip" href="/test" class="hidden px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-100 hover:bg-amber-100 transition-colors">TraVTI 검사하기</a>
                        </div>
                    </div>
                </div>
                <div class="space-y-1">
                    <a class="block py-4 text-lg font-medium border-b border-gray-100 hover:text-blue-500 transition-colors" href="/my-travti">마이페이지</a>
                    <a class="block py-4 text-lg font-medium border-b border-gray-100 hover:text-blue-500 transition-colors" href="/my-travti?tab=traits">내 여행 성향</a>
                    <a class="block py-4 text-lg font-medium border-b border-gray-100 hover:text-blue-500 transition-colors" href="/my-travti?tab=groups">내 그룹</a>
                    <a class="block py-4 text-lg font-medium border-b border-gray-100 text-slate-400 cursor-not-allowed" href="#" onclick="event.preventDefault(); alert('내 여행 기능은 준비 중입니다.');">내 여행 (Coming Soon)</a>
                </div>
            </div>
        </div>
        <div class="absolute bottom-0 w-full p-6 border-t border-gray-100 bg-gray-50 space-y-4">
            <button id="logout-btn" class="hidden w-full bg-red-500 text-white py-2 px-4 rounded-lg font-medium hover:bg-red-600 transition-colors">로그아웃</button>
            <div>
                <p class="text-xs text-gray-400 mb-1">고객센터 1588-XXXX</p>
                <p class="text-xs text-gray-400">© Travis Inc. All rights reserved.</p>
            </div>
        </div>
    </aside>"""

    nav_html = """
    <header id="site-header" class="sticky top-0 z-[80] border-b border-slate-200 bg-white">
        <div class="flex items-center justify-between w-full px-6 md:px-10 py-4">
            <div class="max-w-3xl mx-auto w-full flex items-center justify-between">
                <a href="/" class="text-blue-500 cursor-pointer hover:opacity-80 transition-opacity">
                    <h2 class="text-slate-900 text-xl font-extrabold">Travis</h2>
                </a>
                <div class="flex items-center gap-4">
                    <!-- Logged Out State -->
                    <a id="desktop-login-btn" href="/login" class="hidden md:block px-5 py-2.5 bg-slate-900 text-white rounded-full hover:bg-slate-800 transition-colors text-sm font-bold shadow-md shadow-slate-900/10">로그인 / 회원가입</a>
                    
                    <!-- Logged In State -->
                    <div id="desktop-user-area" class="hidden items-center gap-4">
                        <div class="flex flex-col items-end text-right mr-2">
                            <span id="desktop-user-welcome" class="text-xs text-slate-500 font-medium"></span>
                            <div id="desktop-user-persona" class="text-sm font-bold text-slate-800"></div>
                        </div>
                        <div class="h-8 w-px bg-slate-200 mx-1"></div>
                        <a id="desktop-mypage-btn" href="/my-travti" class="text-blue-600 hover:text-blue-700 font-bold transition-colors text-sm">마이페이지</a>
                        <button id="desktop-logout-btn" class="text-slate-400 hover:text-red-500 font-medium transition-colors text-sm">로그아웃</button>
                    </div>

""" + hamburger_btn_html + """
                </div>
            </div>
        </div>
    </header>

""" + sidebar_html + """

     <script>
        (function(){
            // Supabase Config
            const SUPABASE_URL = '""" + os.environ.get("SUPABASE_URL", "") + """';
            const SUPABASE_KEY = '""" + os.environ.get("SUPABASE_KEY", "") + """';
            let supabase = null;
            
            try {
                if (window.supabase && SUPABASE_URL && SUPABASE_KEY) {
                    supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
                } else if (!SUPABASE_URL) {
                    console.warn('Supabase URL is missing. Auth features may not work.');
                }
            } catch(e) {
                console.error('Supabase Init Failed:', e);
            }

            // 로그인 상태 관리
            function initLoginState(){
                // Sidebar Elements
                const loginBtn = document.getElementById('header-login-btn');
                const userIdDisplay = document.getElementById('user-id-display');
                const userIdText = document.getElementById('user-id-text');
                const logoutBtn = document.getElementById('logout-btn');
                const sidebarTravtiChip = document.getElementById('sidebar-travti-chip');
                const sidebarMbtiChip = document.getElementById('sidebar-mbti-chip');
                const sidebarTestChip = document.getElementById('sidebar-test-chip');
                
                // Desktop Elements
                const desktopLoginBtn = document.getElementById('desktop-login-btn');
                const desktopUserArea = document.getElementById('desktop-user-area');
                const desktopWelcome = document.getElementById('desktop-user-welcome');
                const desktopPersona = document.getElementById('desktop-user-persona');
                
                fetch('/api/session_user')
                    .then(res => res.json())
                    .then(data => {
                        if(data && data.logged_in){
                            const name = data.name ? data.name : (data.email || 'User');
                            const label = data.travti_label;

                            // --- Logged In State ---
                            
                            // Sidebar
                            if(loginBtn) loginBtn.classList.add('hidden');
                            if(userIdDisplay) userIdDisplay.classList.remove('hidden');
                            if (userIdText) userIdText.textContent = `${name} 님`;
                            if(logoutBtn) logoutBtn.classList.remove('hidden');
                            if (sidebarTravtiChip) {
                                if (label && label !== 'None') {
                                    sidebarTravtiChip.textContent = label;
                                    sidebarTravtiChip.classList.remove('hidden');
                                } else {
                                    sidebarTravtiChip.classList.add('hidden');
                                }
                            }
                            if (sidebarMbtiChip) {
                                if (data.mbti && data.mbti !== 'None') {
                                    sidebarMbtiChip.textContent = data.mbti;
                                    sidebarMbtiChip.classList.remove('hidden');
                                } else {
                                    sidebarMbtiChip.classList.add('hidden');
                                }
                            }
                            if (sidebarTestChip) {
                                if (label && label !== 'None') sidebarTestChip.classList.add('hidden');
                                else sidebarTestChip.classList.remove('hidden');
                            }

                            // Desktop
                            if(desktopLoginBtn) {
                                desktopLoginBtn.classList.remove('md:block');
                                desktopLoginBtn.classList.add('hidden');
                            }
                            
                            if(desktopUserArea) {
                                desktopUserArea.classList.remove('hidden');
                                desktopUserArea.classList.add('md:flex');
                                
                                // Update Name
                                if(desktopWelcome) desktopWelcome.innerHTML = `<span class="font-bold text-slate-800">환영합니다,</span> <span class="text-blue-600 font-bold">${name}님!</span>`;
                                
                                // Update Persona
                                if(desktopPersona) {
                                    if(label && label !== 'None') {
                                        desktopPersona.innerHTML = `<span class="text-blue-600">Traveler ${label}</span>`;
                                    } else {
                                        desktopPersona.innerHTML = `<a href="/test" class="inline-block text-[10px] font-bold bg-blue-50 text-blue-600 border border-blue-200 px-2 py-0.5 rounded-full hover:bg-blue-100 transition-colors mt-0.5">TraVTI 알아보기 →</a>`;
                                    }
                                }
                            }

                        } else {
                            // --- Logged Out State ---
                            
                            // Sidebar
                            if(loginBtn) loginBtn.classList.remove('hidden');
                            if(userIdDisplay) userIdDisplay.classList.add('hidden');
                            if(logoutBtn) logoutBtn.classList.add('hidden');
                            if(sidebarTravtiChip) sidebarTravtiChip.classList.add('hidden');
                            if(sidebarMbtiChip) sidebarMbtiChip.classList.add('hidden');
                            if(sidebarTestChip) sidebarTestChip.classList.add('hidden');
                            
                            // Desktop
                            if(desktopLoginBtn) {
                                desktopLoginBtn.classList.remove('hidden');
                                desktopLoginBtn.classList.add('md:block');
                            }
                            
                            if(desktopUserArea) {
                                desktopUserArea.classList.add('hidden');
                                desktopUserArea.classList.remove('md:flex');
                            }
                        }
                    })
                    .catch(err => {
                        console.error('Session Check Failed:', err);
                        // Fallback: show login buttons (Sidebar)
                        if(loginBtn) loginBtn.classList.remove('hidden');
                        if(userIdDisplay) userIdDisplay.classList.add('hidden');
                        if(logoutBtn) logoutBtn.classList.add('hidden');
                        if(sidebarTravtiChip) sidebarTravtiChip.classList.add('hidden');
                        if(sidebarMbtiChip) sidebarMbtiChip.classList.add('hidden');
                        if(sidebarTestChip) sidebarTestChip.classList.add('hidden');
                        // Desktop fallback
                        if(desktopLoginBtn) {
                            desktopLoginBtn.classList.remove('hidden');
                            desktopLoginBtn.classList.add('md:block');
                        }
                        if(desktopUserArea) {
                            desktopUserArea.classList.add('hidden');
                            desktopUserArea.classList.remove('md:flex');
                        }
                    });
            }

            // 로그인/회원가입 모달 대체 (단일 라우트 이동)
            function openLoginModal(){
                window.location.href = '/login';
            }
            function closeLoginModal(){
                // No-op
            }

            async function signInWithProvider(provider) {
                if (!supabase) return alert('Supabase 설정 오류: URL/Key가 없습니다.');
                const { data, error } = await supabase.auth.signInWithOAuth({
                    provider: provider,
                    options: {
                        redirectTo: window.location.origin
                    }
                });
                if (error) alert('Login Error: ' + error.message);
            }

            async function performLogout(){
                if(supabase) await supabase.auth.signOut();
                fetch('/api/logout', { method: 'POST' })
                    .then(() => {
                        window.location.reload(); // Reload to refresh state
                    });
            }
            
            // Auth State Change Listener
            if (supabase) {
                supabase.auth.onAuthStateChange(async (event, session) => {
                    if (event === 'SIGNED_IN' && session) {
                        try {
                            const resp = await fetch('/api/login', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({ 
                                    access_token: session.access_token,
                                    refresh_token: session.refresh_token,
                                    user: session.user
                                })
                            });
                            if (resp.ok) {
                                closeLoginModal();
                                initLoginState(); // Update UI
                            } else {
                                console.error('Login sync failed');
                            }
                        } catch(e) {
                            console.error('Login sync failed', e);
                        }
                    }
                });
            }

            // 메뉴 보호 처리
            const protectedMenus = document.querySelectorAll('.menu-protected');
            protectedMenus.forEach(menu => {
                menu.addEventListener('click', function(e){
                    e.preventDefault();
                    const page = menu.dataset.page || '';
                    fetch('/api/session_user')
                        .then(res => res.json())
                        .then(data => {
                            if(!data || !data.logged_in){
                                alert('로그인이 필요합니다.');
                                openLoginModal();
                                return;
                            }

                            const userId = data.user_id;
                            if(page === '여행계획 작성'){
                                fetch('/api/check_actual_label?user_id=' + encodeURIComponent(userId))
                                    .then(res => res.json())
                                    .then(data => {
                                        if(data && data.has_travti_label){
                                            window.location.href = '/result';
                                        } else {
                                            alert('TraVTI 검사를 먼저 진행해주세요. 검사 페이지로 이동합니다.');
                                            window.location.href = '/test';
                                        }
                                    })
                                    .catch(err => {
                                        console.error('검사 상태 확인 오류', err);
                                        alert('서버와 통신할 수 없습니다. 잠시 후 다시 시도해주세요.');
                                    });
                                return;
                            }

                            if(page === '나의 여행계획'){
                                window.location.href = '/my-plans';
                                return;
                            }

                            if(page === '입국 서류' || page === '나의 입국서류정보'){
                                window.location.href = '/entry-form';
                                return;
                            }

                            alert('해당 메뉴는 준비중입니다.');
                        })
                        .catch(() => {
                            alert('서버와 통신할 수 없습니다. 잠시 후 다시 시도해주세요.');
                        });
                });
            });

            const openBtns = document.querySelectorAll('#menu-toggle-header');
            const sidebar = document.getElementById('sidebar-common');
            const backdrop = document.getElementById('sidebar-backdrop-common');
            const closeBtn = document.getElementById('close-menu-common');

            function openSidebar(){
                if(sidebar) sidebar.classList.remove('translate-x-full');
                if(backdrop) {
                    backdrop.classList.remove('hidden');
                    setTimeout(() => backdrop.classList.add('opacity-100'), 10);
                }
                document.body.style.overflow = 'hidden';
            }

            function closeSidebar(){
                if(sidebar) sidebar.classList.add('translate-x-full');
                if(backdrop) {
                    backdrop.classList.remove('opacity-100');
                    setTimeout(() => backdrop.classList.add('hidden'), 300);
                }
                document.body.style.overflow = 'auto';
            }

            // 이벤트 리스너 설정
            const _desktopLoginBtn = document.getElementById('desktop-login-btn');
            const _desktopLogoutBtn = document.getElementById('desktop-logout-btn');
            const _loginBtn = document.getElementById('header-login-btn');
            const _logoutBtn = document.getElementById('logout-btn');

            if(_desktopLoginBtn) _desktopLoginBtn.addEventListener('click', (e) => {
                e.preventDefault();
                openLoginModal();
            });
            if(_desktopLogoutBtn) _desktopLogoutBtn.addEventListener('click', performLogout);
            if(_loginBtn) _loginBtn.addEventListener('click', (e) => {
                e.preventDefault();
                openLoginModal();
            });
            if(_logoutBtn) _logoutBtn.addEventListener('click', performLogout);

            openBtns.forEach(b => b.addEventListener('click', openSidebar));
            if(closeBtn) closeBtn.addEventListener('click', closeSidebar);
            if(backdrop) backdrop.addEventListener('click', closeSidebar);

            // 초기 상태 설정
            initLoginState();
        })();
    </script>
    
    """
    return nav_html

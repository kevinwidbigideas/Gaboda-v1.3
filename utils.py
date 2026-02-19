"""
공용 유틸리티 및 헬퍼 함수
"""
import random

# ========================================
# 공통 HTML 헤더 (모든 페이지에서 사용)
# ========================================
COMMON_HEAD = """
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700;800;900&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,typography,container-queries"></script>
<style>body { font-family: 'Pretendard', sans-serif; }</style>
"""

def generate_next_id():
    """고유한 새 ID를 생성합니다 (동시성 문제 대응)"""
    from app import get_db
    db = get_db()
    cursor = db.cursor()
    
    max_attempts = 100
    for attempt in range(max_attempts):
        cursor.execute('SELECT MAX(CAST(SUBSTR(ID, 9) AS INTEGER)) FROM survey_responses WHERE ID LIKE "TRV-NEW-%"')
        row = cursor.fetchone()
        result = row[0] if row[0] else None
        
        if result is None:
            next_num = 1000
        else:
            next_num = result + 1
        
        new_id = f"TRV-NEW-{next_num}"
        
        # 이 ID가 이미 존재하는지 확인
        cursor.execute('SELECT COUNT(*) FROM survey_responses WHERE ID = ?', (new_id,))
        exists = cursor.fetchone()[0] > 0
        
        if not exists:
            return new_id
    
    # 최대 시도 횟수 초과 시 임의 번호 사용
    return f"TRV-NEW-{random.randint(10000, 99999)}"

def get_header(current_page):
    """현재 페이지에 따른 네비게이션 헤더 반환"""
    hamburger_btn_html = ""
    sidebar_html = ""

    if current_page != 'home' and current_page != 'test':
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
                <button id="header-login-btn" class="block text-lg font-medium mb-6 text-gray-800 cursor-pointer hover:text-blue-500 transition-colors">로그인</button>
                <div id="user-id-display" class="hidden mb-6">
                    <div class="flex items-center justify-between">
                        <span id="user-id-text" class="text-lg font-medium text-gray-800">로그인</span>
                        <a id="my-travti-link" href="/my-travti" class="text-sm font-semibold text-blue-500 hover:text-blue-600">내 TraVTI 확인</a>
                    </div>
                </div>
                <div class="space-y-1">
                    <a class="block py-4 text-lg font-medium border-b border-gray-100 hover:text-blue-500 transition-colors" href="/test">TraVTI 검사</a>
                    <a class="menu-protected block py-4 text-lg font-medium border-b border-gray-100 hover:text-blue-500 transition-colors" href="#" data-page="여행계획 작성">여행계획 작성</a>
                    <a class="menu-protected block py-4 text-lg font-medium border-b border-gray-100 hover:text-blue-500 transition-colors" href="#" data-page="입국 서류">나의 입국서류정보</a>
                    <a class="menu-protected block py-4 text-lg font-medium border-b border-gray-100 hover:text-blue-500 transition-colors" href="#" data-page="나의 여행계획">나의 여행계획</a>
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
                <div class="flex items-center gap-3">
                    <a href="/login" class="hidden md:block text-slate-600 hover:text-blue-600 font-medium transition-colors text-sm">로그인</a>
                    <a href="/signup" class="hidden md:block text-slate-600 hover:text-blue-600 font-medium transition-colors text-sm">회원가입</a>
""" + hamburger_btn_html + """
                </div>
            </div>
        </div>
    </header>

""" + sidebar_html + """

    <!-- 로그인 모달 -->
    <div id="login-modal" class="fixed inset-0 bg-black/50 z-[110] hidden flex items-center justify-center">
        <div class="bg-white rounded-lg shadow-lg p-8 max-w-sm w-11/12">
            <h2 class="text-2xl font-bold mb-6 text-center">로그인</h2>
            <button id="google-login-btn" class="w-full bg-white border border-gray-300 py-3 rounded-lg font-medium text-gray-800 hover:bg-gray-50 transition-colors flex items-center justify-center gap-2 mb-4">
                <img src="https://www.gstatic.com/images/branding/product/1x/googleg_32dp.png" alt="Google" class="w-5 h-5" />
                Google로 로그인
            </button>
            <button id="close-login-modal" class="w-full bg-gray-200 py-3 rounded-lg font-medium text-gray-800 hover:bg-gray-300 transition-colors">
                닫기
            </button>
        </div>
    </div>

     <script>
        (function(){
            // 로그인 상태 관리
            function initLoginState(){
                const loginBtn = document.getElementById('header-login-btn');
                const userIdDisplay = document.getElementById('user-id-display');
                const userIdText = document.getElementById('user-id-text');
                const logoutBtn = document.getElementById('logout-btn');
                fetch('/api/session_user')
                    .then(res => res.json())
                    .then(data => {
                        if(data && data.logged_in){
                            loginBtn.classList.add('hidden');
                            userIdDisplay.classList.remove('hidden');
                            const name = data.name ? data.name : data.user_id;
                            if (userIdText) {
                                userIdText.textContent = `${name} 님. 환영합니다`;
                            }
                            logoutBtn.classList.remove('hidden');
                        } else {
                            loginBtn.classList.remove('hidden');
                            userIdDisplay.classList.add('hidden');
                            logoutBtn.classList.add('hidden');
                        }
                    })
                    .catch(() => {
                        loginBtn.classList.remove('hidden');
                        userIdDisplay.classList.add('hidden');
                        logoutBtn.classList.add('hidden');
                    });
            }

            // 로그인 모달 처리
            const loginBtn = document.getElementById('header-login-btn');
            const googleLoginBtn = document.getElementById('google-login-btn');
            const closeModalBtn = document.getElementById('close-login-modal');
            const loginModal = document.getElementById('login-modal');

            function openLoginModal(){
                loginModal.classList.remove('hidden');
            }
            function closeLoginModal(){
                loginModal.classList.add('hidden');
            }

            function performLogin(){
                fetch('/api/login_random', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        if(data && data.user_id){
                            closeLoginModal();
                            initLoginState();
                        } else {
                            alert('로그인에 실패했습니다.');
                        }
                    })
                    .catch(() => alert('로그인에 실패했습니다.'));
            }

            function performLogout(){
                fetch('/api/logout', { method: 'POST' })
                    .then(() => {
                        initLoginState();
                        alert('로그아웃되었습니다.');
                        window.location.href = '/';
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
                sidebar.classList.remove('translate-x-full');
                backdrop.classList.remove('hidden');
                setTimeout(() => backdrop.classList.add('opacity-100'), 10);
                document.body.style.overflow = 'hidden';
            }

            function closeSidebar(){
                sidebar.classList.add('translate-x-full');
                backdrop.classList.remove('opacity-100');
                setTimeout(() => backdrop.classList.add('hidden'), 300);
                document.body.style.overflow = 'auto';
            }

            // 이벤트 리스너 설정
            if(loginBtn) loginBtn.addEventListener('click', openLoginModal);
            if(googleLoginBtn) googleLoginBtn.addEventListener('click', performLogin);
            if(closeModalBtn) closeModalBtn.addEventListener('click', closeLoginModal);

            const logoutBtn = document.getElementById('logout-btn');
            if(logoutBtn) logoutBtn.addEventListener('click', performLogout);

            openBtns.forEach(b => b.addEventListener('click', openSidebar));
            if(closeBtn) closeBtn.addEventListener('click', closeSidebar);
            if(backdrop) backdrop.addEventListener('click', closeSidebar);

            // 초기 상태 설정
            initLoginState();
        })();
    </script>
    """
    return nav_html

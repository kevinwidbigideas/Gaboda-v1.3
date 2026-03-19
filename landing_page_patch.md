1. 현재기준 뜨는 메인으로 들어가면 나오는 화면을 랜딩페이지로 만들려고함. 해당 화면에서 다른 화면으로 연결되는 화면은 없음.
http://127.0.0.1:5000/ -> 여기로 들어가면 바로 뜨는 화면
2. 로그인 버튼 및 사이드바(X 로그인 / 회원가입 마이페이지 내 여행 성향 내 그룹 내 여행 (Coming Soon)) 없애고.
3. 현재 기준 무료로 테스트해보기 일정 맡기기 등이 전부 travti테스트로 이어지게 설계되었는데 그 부분 "사전예약하기"로 변경해줘.
4. 사전예약을 받으면 이메일은 DB에 저장하고 (새로운 db테이블 만들거임)
5. 마지막 부분에 내리면 ready to travel? 부분에  아래의 사전예약 부분 코드 넣어줘.
 
 
 <!-- Footer / CTA -->
    <footer id="cta" class="py-32 relative text-center">
        <div class="max-w-4xl mx-auto px-6 reveal">
            <h2 class="text-5xl md:text-8xl font-black tracking-tighter mb-12">준비되셨나요?</h2>
            <p class="text-2xl text-slate-500 font-bold mb-16">세상에서 가장 쉬운 여행의 시작, Travis.</p>
            
            <div class="glass p-4 rounded-[32px] max-w-lg mx-auto flex flex-col sm:flex-row gap-3">
                <input type="email" placeholder="이메일 주소를 입력하세요" class="flex-1 bg-transparent border-0 focus:ring-0 text-lg font-bold px-6">
                <button class="bg-slate-900 text-white px-10 py-5 rounded-2xl font-black text-lg hover:shadow-xl transition-all">
                    사전 예약
                </button>
            </div>
            
            <div class="mt-32 pt-16 border-t border-slate-200 text-slate-400 font-bold text-sm tracking-widest uppercase">
                &copy; 2026 TRAVIS INC. ALL RIGHTS RESERVED.
            </div>
        </div>
    </footer>
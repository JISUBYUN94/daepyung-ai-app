import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import re
import time

# 웹사이트 제목 및 레이아웃 설정
st.set_page_config(page_title="사내 AI 특허 분석 시스템", layout="wide")
st.title("🛡️ 실시간 특허 침해 리스크 분석 시스템")
st.markdown("경쟁사 특허 요약문을 AI가 당사 공정과 대조하여 리스크를 즉시 분석합니다.")

# 사이드바: 설정 및 API 키 입력
with st.sidebar:
    st.header("⚙️ 설정")
    kipris_key = st.text_input("KIPRIS API Key", type="password")
    gemini_key = st.text_input("Gemini API Key", type="password")
    num_results = st.slider("가져올 특허 개수", 1, 20, 5)

# 메인 화면: 입력창
col1, col2 = st.columns(2)
with col1:
    search_keyword = st.text_input("검색할 특허 키워드", value="아이비엽 추출물")
with col2:
    our_process = st.text_area("대조할 당사 공정/기술", 
                              value="아이비엽을 30% 에탄올로 80°C에서 추출한 후 분무 건조하여 분말화하는 공정.")

# 분석 시작 버튼
if st.button("🚀 분석 시작"):
    if not kipris_key or not gemini_key:
        st.error("API 키를 모두 입력해 주세요.")
    else:
        # 1. KIPRIS 검색
        st.info("🔍 KIPRIS에서 데이터를 가져오는 중...")
        search_url = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getWordSearch"
        res = requests.get(search_url, params={"word": search_keyword, "ServiceKey": kipris_key, "numOfRows": num_results})
        
        items = re.findall(r'<item>(.*?)</item>', res.text, re.DOTALL | re.IGNORECASE)
        
        if not items:
            st.warning("검색 결과가 없습니다.")
        else:
            # AI 설정
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(model_name='gemini-2.5-pro', generation_config={"temperature": 0.1})
            
            results = []
            progress_bar = st.progress(0)
            
            for i, item_text in enumerate(items):
                # 💡 안전한 추출 로직으로 교체 (오타 수정 완료!)
                app_num_match = re.search(r'<applicationNumber>(.*?)</applicationNumber>', item_text, re.IGNORECASE)
                app_num = app_num_match.group(1).strip() if app_num_match else "번호없음"
                
                applicant_match = re.search(r'<applicantName>(.*?)</applicantName>', item_text, re.IGNORECASE)
                applicant = applicant_match.group(1).strip() if applicant_match else "출원인없음"
                
                title_match = re.search(r'<inventionTitle>(.*?)</inventionTitle>', item_text, re.IGNORECASE)
                title = title_match.group(1).strip() if title_match else "제목없음"
                
                astrt_match = re.search(r'<astrtCont>(.*?)</astrtCont>', item_text, re.DOTALL | re.IGNORECASE)
                
                clean_astrt = "요약문 없음"
                if astrt_match:
                    raw_astrt = re.sub(r'<!\[CDATA\[|\]\]>', ' ', astrt_match.group(1))
                    clean_astrt = " ".join(re.sub(r'<.*?>', ' ', raw_astrt).split())

                # AI 분석
                ai_report = "분석 불가 (요약문 없음)"
                if clean_astrt != "요약문 없음":
                    prompt = f"[요약문]: {clean_astrt}\n[당사기술]: {our_process}\n위험도, 저촉분석, 회피제안을 요약해줘."
                    try:
                        ai_report = model.generate_content(prompt).text
                    except Exception as e:
                        ai_report = f"AI 분석 에러: {e}"
                
                results.append({
                    "출원번호": app_num,
                    "출원인": applicant,
                    "특허명": title,
                    "AI 리스크 분석": ai_report
                })
                
                progress_bar.progress((i + 1) / len(items))
                time.sleep(2) # 안정성 확보를 위해 2초 대기

            # 결과 화면 표시
            df = pd.DataFrame(results)
            st.success("✅ 분석 완료!")
            st.dataframe(df, use_container_width=True)
            
            # 엑셀 다운로드 버튼
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button(label="📥 분석 결과 엑셀 다운로드", 
                               data=output.getvalue(), 
                               file_name=f"{search_keyword}_분석리포트.xlsx")

import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import re
import time

st.set_page_config(page_title="사내 AI 특허 분석 시스템", layout="wide")

# ==========================================
# 0. 사이드바: 설정 및 메뉴 선택
# ==========================================
with st.sidebar:
    st.header("⚙️ 기본 설정")
    kipris_key = st.text_input("KIPRIS API Key", type="password")
    gemini_key = st.text_input("Gemini API Key", type="password")
    num_results = st.slider("가져올 특허 개수", 5, 10, 30)
    
    st.divider() # 시각적 구분선
    
    # 💡 새로운 메뉴 기능 추가!
    st.header("📂 메뉴 선택")
    menu = st.radio("원하시는 기능을 선택하세요:", 
                    ["🛡️ AI 리스크 분석", "🔍 단순 특허 검색 (빠름)"])

# ==========================================
# 1. 첫 번째 메뉴: AI 리스크 분석 (기존 기능)
# ==========================================
if menu == "🛡️ AI 리스크 분석":
    st.title("🛡️ 실시간 특허 침해 리스크 분석 시스템")
    st.markdown("경쟁사 특허 요약문을 AI가 당사 공정과 대조하여 리스크를 즉시 분석합니다.")

    col1, col2 = st.columns(2)
    with col1:
        search_keyword = st.text_input("검색할 특허 키워드", value="아이비엽 추출물")
    with col2:
        our_process = st.text_area("대조할 당사 공정/기술", 
                                  value="아이비엽을 30% 에탄올로 80°C에서 추출한 후 분무 건조하여 분말화하는 공정.")

    if st.button("🚀 AI 분석 시작"):
        if not kipris_key or not gemini_key:
            st.error("사이드바에 KIPRIS와 Gemini API 키를 모두 입력해 주세요.")
        else:
            st.info("🔍 KIPRIS에서 데이터를 가져오는 중...")
            search_url = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getWordSearch"
            res = requests.get(search_url, params={"word": search_keyword, "ServiceKey": kipris_key, "numOfRows": num_results})
            items = re.findall(r'<item>(.*?)</item>', res.text, re.DOTALL | re.IGNORECASE)
            
            if not items:
                st.warning("검색 결과가 없습니다.")
            else:
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel(model_name='gemini-2.5-pro', generation_config={"temperature": 0.1})
                results = []
                progress_bar = st.progress(0)
                
                for i, item_text in enumerate(items):
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

                    ai_report = "분석 불가 (요약문 없음)"
                    if clean_astrt != "요약문 없음":
                        prompt = f"[요약문]: {clean_astrt}\n[당사기술]: {our_process}\n위험도, 저촉분석, 회피제안을 요약해줘."
                        try:
                            ai_report = model.generate_content(prompt).text
                        except Exception as e:
                            ai_report = f"AI 분석 에러: {e}"
                    
                    results.append({"출원번호": app_num, "출원인": applicant, "특허명": title, "AI 리스크 분석": ai_report})
                    progress_bar.progress((i + 1) / len(items))
                    time.sleep(2)

                df = pd.DataFrame(results)
                st.success("✅ 분석 완료!")
                st.dataframe(df, use_container_width=True)
                
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button(label="📥 AI 분석 리포트 엑셀 다운로드", data=output.getvalue(), file_name=f"{search_keyword}_AI분석.xlsx")


# ==========================================
# 2. 두 번째 메뉴: 단순 특허 검색 (신규 기능)
# ==========================================
elif menu == "🔍 단순 특허 검색 (빠름)":
    st.title("🔍 KIPRIS 단순 특허 검색")
    st.markdown("AI 분석 없이 특허 목록과 요약문만 아주 빠르게 검색하여 엑셀로 추출합니다.")
    
    # 여기서는 제미나이 키나 당사 공정 내용이 필요 없습니다.
    search_keyword_simple = st.text_input("검색할 특허 키워드를 입력하세요", value="아이비엽 추출물", key="simple_search")
    
    if st.button("⚡ 빠른 검색 시작"):
        if not kipris_key:
            st.error("사이드바에 KIPRIS API 키를 입력해 주세요.")
        else:
            st.info("🔍 KIPRIS에서 데이터를 빠르게 가져오는 중...")
            search_url = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getWordSearch"
            res = requests.get(search_url, params={"word": search_keyword_simple, "ServiceKey": kipris_key, "numOfRows": num_results})
            items = re.findall(r'<item>(.*?)</item>', res.text, re.DOTALL | 대소문자무시를_위한_플래그_수정_re.IGNORECASE)
            
            if not items:
                st.warning("검색 결과가 없습니다.")
            else:
                results_simple = []
                for item_text in items:
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
                    
                    results_simple.append({"출원번호": app_num, "특허명": title, "출원인": applicant, "요약문 원본": clean_astrt})
                
                df_simple = pd.DataFrame(results_simple)
                st.success("✅ 검색 완료! (AI 분석을 생략하여 즉시 완료되었습니다)")
                st.dataframe(df_simple, use_container_width=True)
                
                from io import BytesIO
                output_simple = BytesIO()
                with pd.ExcelWriter(output_simple, engine='openpyxl') as writer:
                    df_simple.to_excel(writer, index=False)
                st.download_button(label="📥 특허 목록 엑셀 다운로드", data=output_simple.getvalue(), file_name=f"{search_keyword_simple}_목록.xlsx")

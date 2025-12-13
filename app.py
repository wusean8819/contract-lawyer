import streamlit as st
import google.generativeai as genai
import importlib.metadata

# --- 1. 檢查真實版本 (抓兇手) ---
try:
    lib_version = importlib.metadata.version("google-generativeai")
except:
    lib_version = "無法讀取"

# --- 設定頁面 ---
st.set_page_config(page_title="24小時數位合約律師", page_icon="⚖️")
st.title("⚖️ 數位合約律師 (診斷模式)")

# 顯示版本號 (這行最重要)
st.info(f"🔍 目前系統安裝的 Google 套件版本：{lib_version}")
st.write("如果是 0.5.0 以下，代表雲端沒有更新成功，那是卡住的主因。")

# --- 設定 API Key ---
api_key = st.sidebar.text_input("請輸入 Google API Key", type="password")

if not api_key:
    st.warning("⬅️ 請輸入 Key")
else:
    try:
        genai.configure(api_key=api_key)
        
        # 使用最標準的 1.5 Flash
        model = genai.GenerativeModel('gemini-1.5-flash')

        contract_content = st.text_area("📄 貼上合約內容：", height=200, value="測試合約：甲乙雙方同意...")

        if st.button("🚀 開始分析 (非串流模式)"):
            with st.spinner("連線中...如果這裡卡住超過 10 秒就是環境問題"):
                # 關閉 stream，強迫它一次回傳，比較容易看到錯誤
                response = model.generate_content(f"請分析這份合約：{contract_content}")
                
                st.success("✅ 成功回傳！")
                st.markdown(response.text)

    except Exception as e:
        st.error(f"❌ 發生錯誤：{e}")

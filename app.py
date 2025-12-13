import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time

# --- 設定頁面資訊 ---
st.set_page_config(page_title="24小時數位合約律師", page_icon="⚖️")
st.title("⚖️ 你的 24 小時口袋數位合約律師")
st.markdown("別讓合約成為看不懂的天書。我們的 AI 防護罩為你預判風險。")

# --- 側邊欄：設定 API Key ---
api_key = st.sidebar.text_input("🔑 請輸入 Google API Key", type="password")

if not api_key:
    st.warning("⬅️ 請先在左側輸入 API Key")
else:
    try:
        # 1. 設定連線
        genai.configure(api_key=api_key)
        
        # ★★★ 關鍵技術：自動抓取你帳號能用的模型 ★★★
        with st.spinner("正在為您尋找最適合的 AI 大腦..."):
            available_models = []
            try:
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        # 只把名字乾淨的取出來 (去掉 models/ 前綴)
                        model_name = m.name.replace('models/', '')
                        available_models.append(model_name)
            except:
                pass

        # 智慧挑選邏輯：優先用 2.0 Flash (最快)，沒有就用清單裡的第一個
        if not available_models:
            # 萬一真的抓不到，才用預設值 (但你的版本 0.8.5 一定抓得到)
            target_model_name = 'gemini-2.0-flash'
        else:
            # 優先尋找含有 "2.0-flash" 的模型
            target_model_name = next((m for m in available_models if '2.0-flash' in m), None)
            # 如果沒有，找含有 "flash" 的最新版
            if not target_model_name:
                target_model_name = next((m for m in available_models if 'flash' in m), available_models[0])

        # 顯示我們最後選了誰 (讓你安心)
        st.sidebar.success(f"✅ 已自動連線模型：\n{target_model_name}")
        
        # 建立模型
        model = genai.GenerativeModel(target_model_name)

        # 2. 合約輸入區
        contract_content = st.text_area("📄 請將合約內容貼在這裡：", height=300)

        # 3. 分析按鈕
        if st.button("🚀 啟動數位防護罩"):
            if not contract_content.strip():
                st.warning("⚠️ 請貼上內容")
            else:
                st.divider()
                st.subheader("📊 分析報告")
                text_placeholder = st.empty()
                full_text = ""
                
                # 提示詞
                prompt = f"""
                你是專業律師。請分析以下合約的風險(紅/黃/綠燈)、關鍵陷阱與修改建議。
                
                合約內容：
                {contract_content}
                """

                # 4. 執行分析 (關閉安全柵欄，避免誤判法律用語)
                try:
                    safety_settings = {
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                    
                    response = model.generate_content(prompt, stream=True, safety_settings=safety_settings)
                    
                    # 打字機效果
                    for chunk in response:
                        if chunk.text:
                            full_text += chunk.text
                            text_placeholder.markdown(full_text + "▌")
                    
                    text_placeholder.markdown(full_text)
                    
                except Exception as e:
                    st.error(f"分析中斷，請重試。錯誤：{e}")

    except Exception as e:
        st.error(f"連線錯誤：{e}")

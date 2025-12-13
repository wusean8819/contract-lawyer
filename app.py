import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- 設定頁面資訊 ---
st.set_page_config(page_title="24小時數位合約律師", page_icon="⚖️")
st.title("⚖️ 你的 24 小時口袋數位合約律師")
st.markdown("現在版本：0.8.5 | 模型：Gemini 2.0 Flash (解鎖版)")

# --- 側邊欄：設定 API Key ---
api_key = st.sidebar.text_input("🔑 請輸入 Google API Key", type="password")

if not api_key:
    st.warning("⬅️ 請先在左側輸入 API Key")
else:
    try:
        # 1. 設定連線
        genai.configure(api_key=api_key)
        
        # ★★★ 關鍵 1：直接指定你清單裡有的 2.0 Flash ★★★
        model = genai.GenerativeModel('gemini-2.0-flash')

        # 2. 合約輸入區
        contract_content = st.text_area("📄 請將合約內容貼在這裡：", height=300)

        # 3. 分析按鈕
        if st.button("🚀 啟動數位防護罩"):
            if not contract_content.strip():
                st.warning("⚠️ 請貼上內容")
            else:
                st.divider()
                st.subheader("📊 分析報告")
                
                # 狀態顯示區 (讓你知道沒當機)
                status_text = st.empty()
                status_text.info("🔄 正在連線 Google 大腦...")
                
                result_area = st.empty()
                full_text = ""
                
                # 提示詞
                prompt = f"""
                你是專業律師。請分析以下合約的風險(紅/黃/綠燈)、關鍵陷阱與修改建議。
                合約內容：
                {contract_content}
                """

                # ★★★ 關鍵 2：徹底關閉安全過濾 (解決卡住的主因) ★★★
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                try:
                    # 開始分析
                    response = model.generate_content(
                        prompt, 
                        stream=True, 
                        safety_settings=safety_settings
                    )
                    
                    status_text.success("✅ 連線成功！正在撰寫報告...")
                    
                    # 打字機效果
                    for chunk in response:
                        if chunk.text:
                            full_text += chunk.text
                            result_area.markdown(full_text + "▌")
                    
                    # 完成
                    result_area.markdown(full_text)
                    status_text.empty() # 隱藏狀態列
                    
                except Exception as e:
                    st.error(f"分析過程發生錯誤：{e}")
                    st.error("如果顯示 429 Resource Exhausted，代表測試太多次了，請等 1 分鐘再試。")

    except Exception as e:
        st.error(f"連線設定錯誤：{e}")

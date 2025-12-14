import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- 設定頁面資訊 ---
st.set_page_config(page_title="24小時數位合約律師", page_icon="⚖️")
st.title("⚖️ 你的 24 小時口袋數位合約律師")
st.markdown("版本：穩定通道 (Flash Latest) | 狀態：額度無限制")

# --- 側邊欄：設定 API Key ---
api_key = st.sidebar.text_input("🔑 請輸入 Google API Key", type="password")

if not api_key:
    st.warning("⬅️ 請先在左側輸入 API Key")
else:
    try:
        # 1. 設定連線
        genai.configure(api_key=api_key)
        
        # ★★★ 關鍵修正：強制使用你名單上的 'gemini-flash-latest' ★★★
        # 這個名字對應到穩定的生產環境版本，不會有 limit: 0 的問題
        model = genai.GenerativeModel('gemini-flash-latest')

        # 2. 合約輸入區
        contract_content = st.text_area("📄 請將合約內容貼在這裡：", height=300)

        # 3. 分析按鈕
        if st.button("🚀 啟動數位防護罩"):
            if not contract_content.strip():
                st.warning("⚠️ 請貼上內容")
            else:
                st.divider()
                st.subheader("📊 分析報告")
                
                status_text = st.empty()
                result_area = st.empty()
                full_text = ""
                
                # 提示詞
                prompt = f"""
                你是專業律師。請分析以下合約的風險(紅/黃/綠燈)、關鍵陷阱與修改建議。
                合約內容：
                {contract_content}
                """

                # 設定：關閉安全過濾
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                try:
                    status_text.info("🔄 正在分析中...")
                    
                    # 開始分析 (使用流式傳輸)
                    response = model.generate_content(
                        prompt, 
                        stream=True, 
                        safety_settings=safety_settings
                    )
                    
                    # 打字機效果
                    for chunk in response:
                        if chunk.text:
                            full_text += chunk.text
                            result_area.markdown(full_text + "▌")
                    
                    # 完成
                    result_area.markdown(full_text)
                    status_text.empty()
                    
                except Exception as e:
                    # 捕捉並顯示錯誤
                    if "429" in str(e):
                        st.error("⚠️ 系統繁忙，請稍等 30 秒再試一次。")
                    else:
                        st.error(f"分析中斷：{e}")

    except Exception as e:
        st.error(f"連線設定錯誤：{e}")

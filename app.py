import streamlit as st
import google.generativeai as genai
import time

# --- 設定頁面資訊 ---
st.set_page_config(page_title="24小時數位合約律師", page_icon="⚖️")
st.title("⚖️ 你的 24 小時口袋數位合約律師")
st.markdown("別讓合約成為看不懂的天書。我們的 AI 防護罩為你預判風險，像紅綠燈一樣標示陷阱。")

# --- 側邊欄：設定 API Key ---
with st.sidebar:
    st.header("🔑 啟動金鑰")
    api_key = st.text_input("請輸入 Google API Key", type="password")
    
# --- 主程式邏輯 ---
if not api_key:
    st.warning("⬅️ 請先在左側欄位輸入 API Key 才能啟用律師服務。")
else:
    try:
        # 1. 設定連線
        genai.configure(api_key=api_key)
        
        # ★★★ 關鍵修改：使用你在清單中看到的「最新穩定版指標」 ★★★
        # 這會自動導向目前最穩的 Flash 版本，避免 2.0 實驗版的不穩定
        model = genai.GenerativeModel('gemini-flash-latest')

        # 2. 介面
        contract_content = st.text_area("📄 請將合約內容貼在這裡：", height=300)

        if st.button("🚀 啟動數位防護罩 (開始分析)"):
            if not contract_content.strip():
                st.warning("⚠️ 請先貼上合約內容喔！")
            else:
                st.divider()
                st.subheader("📊 分析報告")
                text_placeholder = st.empty()
                
                # 3. 組合提示詞 (精簡版)
                prompt = f"""
                你是一位專業律師。請針對以下合約內容進行風險評估：
                1. 風險評估(紅/黃/綠燈)
                2. 關鍵風險條款
                3. 修改建議
                
                合約內容：
                {contract_content}
                """
                
                # 4. 發送請求 (使用流式傳輸，確保不會卡死)
                try:
                    response = model.generate_content(prompt, stream=True)
                    
                    # 顯示打字機效果
                    full_text = ""
                    for chunk in response:
                        if chunk.text:
                            full_text += chunk.text
                            text_placeholder.markdown(full_text + "▌")
                            time.sleep(0.01) # 稍微緩衝，讓顯示更順暢
                    
                    text_placeholder.markdown(full_text) # 顯示最終結果
                    
                except Exception as inner_e:
                    # 如果連線失敗，會顯示具體原因
                    st.error(f"連線中斷，請重試。\n技術錯誤訊息：{inner_e}")

    except Exception as e:
        st.error(f"API Key 驗證失敗或是系統錯誤：{e}")

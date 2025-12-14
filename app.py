import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time

# --- 設定頁面資訊 ---
st.set_page_config(page_title="24小時數位合約律師", page_icon="⚖️")
st.title("⚖️ 你的 24 小時口袋數位合約律師")
st.markdown("版本：自動導航版 (Auto-Detect) | 環境：0.8.5 已修復")

# --- 側邊欄：設定 API Key ---
api_key = st.sidebar.text_input("🔑 請輸入 Google API Key", type="password")

if not api_key:
    st.warning("⬅️ 請先在左側輸入 API Key")
else:
    try:
        # 1. 設定連線
        genai.configure(api_key=api_key)
        
        # ★★★ 關鍵技術：自動導航 (Auto-Pilot) ★★★
        # 這段程式會去問 Google 你的帳號能用什麼，然後選「最穩」的那個
        with st.spinner("正在為您匹配最佳 AI 大腦..."):
            target_model_name = None
            try:
                available_models = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        # 記錄所有能用的模型名字
                        model_name = m.name.replace('models/', '')
                        available_models.append(model_name)
                
                # --- 智慧挑選邏輯 ---
                # 優先找 1.5-flash (因為它最穩，且沒有額度限制)
                if any('1.5-flash' in m for m in available_models):
                    target_model_name = next((m for m in available_models if '1.5-flash' in m), None)
                # 如果沒有，才找 2.0-flash (比較快但可能有額度限制)
                elif any('2.0-flash' in m for m in available_models):
                    target_model_name = next((m for m in available_models if '2.0-flash' in m), None)
                # 真的都沒有，就選第一個
                else:
                    target_model_name = available_models[0]
                    
            except Exception as e:
                # 萬一連線有問題，直接盲猜一個最保險的
                target_model_name = 'gemini-1.5-flash'

        # 顯示結果讓你知道它選了誰
        st.sidebar.success(f"✅ 已自動連線：\n{target_model_name}")
        
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
                
                status_text = st.empty()
                result_area = st.empty()
                full_text = ""
                
                # 提示詞
                prompt = f"""
                你是專業律師。請分析以下合約的風險(紅/黃/綠燈)、關鍵陷阱與修改建議。
                合約內容：
                {contract_content}
                """

                # 設定：關閉安全過濾 (避免誤判法律用語)
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                try:
                    status_text.info(f"🔄 正在使用 {target_model_name} 分析中...")
                    
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
                    st.error(f"分析中斷：{e}")
                    if "429" in str(e):
                        st.error("額度限制提示：請稍等 1 分鐘後再試。")

    except Exception as e:
        st.error(f"連線設定錯誤：{e}")


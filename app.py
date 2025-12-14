import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- 1. 頁面設定 (開啟寬螢幕模式) ---
st.set_page_config(
    page_title="Pro 數位合約律師",
    page_icon="⚖️",
    layout="wide"
)

# --- 2. 注入專業 CSS (美化字體與卡片) ---
st.markdown("""
<style>
    .stApp { font-family: "Microsoft JhengHei", sans-serif; }
    h1 { color: #2c3e50; font-weight: 700; }
    /* 表格美化 */
    table { width: 100%; border-radius: 10px; overflow: hidden; box-shadow: 0 0 20px rgba(0,0,0,0.05); }
    th { background-color: #4a5568; color: white; padding: 12px; }
    td { padding: 10px; border-bottom: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

# --- 3. 側邊欄與自動導航邏輯 ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2504/2504814.png", width=80)
    st.title("⚖️ 數位律師事務所")
    st.markdown("---")
    
    api_key = st.text_input("輸入 Google API Key", type="password")
    
    # ★★★ 關鍵修正：這裡把「自動導航」邏輯加回來了！ ★★★
    target_model_name = "尚未連線"
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # 自動去抓你帳號能用的模型
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name.replace('models/', ''))
            
            # 智慧挑選策略：優先找 flash-latest (最穩)，沒有才找 2.0
            if any('flash-latest' in m for m in available_models):
                target_model_name = next(m for m in available_models if 'flash-latest' in m)
            elif any('1.5-flash' in m for m in available_models):
                target_model_name = next(m for m in available_models if '1.5-flash' in m)
            elif any('2.0-flash' in m for m in available_models):
                target_model_name = next(m for m in available_models if '2.0-flash' in m)
            else:
                target_model_name = available_models[0] # 真的沒有就選第一個
                
            st.success(f"✅ 已自動連線：\n{target_model_name}")
            
        except:
            st.error("連線中斷，請檢查 Key")
            target_model_name = "gemini-1.5-flash" # 預設備案

    st.markdown("---")
    st.caption(f"🧠 當前大腦：{target_model_name}")
    st.info("💡 提示：越完整的合約內容，評分越準確。")

# --- 4. 主畫面 ---
st.title("🛡️ 24H 數位合約風險分析儀")
st.markdown("#### 讓 AI 為您的合約進行「健康檢查」，3 秒鐘抓出隱藏陷阱。")

if not api_key:
    st.warning("⬅️ 請先在左側輸入 API Key")
else:
    try:
        # 使用剛剛自動抓到的模型名字
        model = genai.GenerativeModel(target_model_name)

        with st.container():
            st.markdown("### 📄 案件受理")
            contract_content = st.text_area(
                "請將合約條款貼在下方：", 
                height=250, 
                placeholder="例如：\n第 12 條：若乙方欲終止合約，需賠償甲方 100 萬元..."
            )

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            analyze_btn = st.button("🚀 啟動深度風險分析", use_container_width=True, type="primary")

        if analyze_btn and contract_content.strip():
            st.divider()
            
            with st.status("🔍 律師正在閱卷中...", expanded=True) as status:
                st.write(f"正在連線 {target_model_name}...")
                st.write("正在計算風險分數...")
                
                # --- 5. 專業 Prompt (讓它畫表格) ---
                prompt = f"""
                你是一位經驗豐富的台灣律師。請針對下列合約進行風險評估。
                
                【重要指令】：請直接輸出 Markdown，並在最開頭包含此表格：
                
                # 📊 合約健康度診斷書

                | 評分項目 | 分析結果 |
                | :--- | :--- |
                | **🏆 合約安全分** | **[請評 0-100 分] 分** |
                | **🚦 風險燈號** | [🔴高風險 / 🟡中風險 / 🟢低風險] |
                | **💣 致命陷阱** | 發現 **[數字]** 個高風險條款 |

                ---
                
                接下來請依序輸出：
                ## 🚦 整體風險評估 (一句話總結)
                ## ⚠️ 紅燈條款 (列出最危險的3點與修改建議)
                ## 💡 隱藏陷阱 (未寫出的風險)
                ## ⚖️ 逐條詳細審查

                合約內容：
                {contract_content}
                """

                # 關閉安全過濾
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                # 呼叫 AI
                result_container = st.empty()
                full_text = ""
                
                try:
                    response = model.generate_content(
                        prompt, 
                        stream=True, 
                        safety_settings=safety_settings
                    )
                    
                    for chunk in response:
                        if chunk.text:
                            full_text += chunk.text
                            result_container.markdown(full_text + "▌")
                    
                    result_container.markdown(full_text)
                    status.update(label="✅ 分析完成！", state="complete", expanded=False)

                except Exception as e:
                    st.error(f"分析中斷：{e}")
                    if "429" in str(e):
                        st.error("⚠️ 額度限制：請稍等 1 分鐘後再試。")

        elif analyze_btn:
            st.warning("⚠️ 請貼上合約內容")

    except Exception as e:
        st.error(f"連線錯誤：{e}")

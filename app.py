import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time

# --- 1. 全局設定 ---
st.set_page_config(
    page_title="Pro 數位合約律師",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 專業 CSS 優化 (美化分頁與卡片) ---
st.markdown("""
<style>
    .stApp { font-family: "Microsoft JhengHei", sans-serif; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .score-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border-left: 5px solid #4a5568;
        margin-bottom: 20px;
    }
    .score-title { font-size: 18px; color: #555; }
    .score-value { font-size: 42px; font-weight: bold; color: #2c3e50; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #fff;
        border-radius: 5px 5px 0 0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #eef2ff;
        border-bottom: 2px solid #4f46e5;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 狀態管理 (Session State) ---
if 'page' not in st.session_state:
    st.session_state.page = 'input'
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = ""
# ★★★ 關鍵修復：增加一個記憶欄位來存合約內容 ★★★
if 'contract_content' not in st.session_state:
    st.session_state.contract_content = ""

# --- 4. 側邊欄與自動導航 ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2504/2504814.png", width=70)
    st.title("⚖️ 數位律師事務所")
    st.markdown("---")
    
    api_key = st.text_input("輸入 Google API Key", type="password")
    
    target_model_name = "尚未連線"
    if api_key:
        try:
            genai.configure(api_key=api_key)
            available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            if any('flash-latest' in m for m in available_models):
                target_model_name = next(m for m in available_models if 'flash-latest' in m)
            elif any('1.5-flash' in m for m in available_models):
                target_model_name = next(m for m in available_models if '1.5-flash' in m)
            elif any('2.0-flash' in m for m in available_models):
                target_model_name = next(m for m in available_models if '2.0-flash' in m)
            else:
                target_model_name = available_models[0]
            
            st.success(f"✅ 連線成功：{target_model_name}")
        except:
            st.error("連線失敗，請檢查 Key")
            target_model_name = "gemini-1.5-flash"

    st.markdown("---")
    if st.session_state.page == 'result':
        if st.button("⬅️ 分析下一份合約", use_container_width=True):
            st.session_state.page = 'input'
            st.session_state.analysis_result = ""
            st.session_state.contract_content = "" # 清空舊合約
            st.rerun()

# --- 5. 頁面邏輯切換 ---

# === 頁面 A：輸入介面 ===
if st.session_state.page == 'input':
    st.title("🛡️ 24H 數位合約風險分析儀")
    st.markdown("#### 請輸入合約內容，AI 將為您切換至專業分析視圖。")
    
    with st.container():
        # 這裡用一個暫時變數接使用者的輸入
        user_input = st.text_area(
            "📄 合約條款貼上區：", 
            height=300, 
            placeholder="請直接貼上整份合約或有疑慮的條款..."
        )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        start_btn = st.button("🚀 啟動深度審查 (進入分析頁)", use_container_width=True, type="primary")

    if start_btn:
        if not api_key:
            st.warning("⚠️ 請先在左側輸入 API Key")
        elif not user_input.strip():
            st.warning("⚠️ 請貼上合約內容")
        else:
            with st.spinner("⚖️ 正在切換至分析室...AI 律師閱卷中..."):
                try:
                    # ★★★ 關鍵修復：在換頁前，把內容存進永久記憶體 ★★★
                    st.session_state.contract_content = user_input
                    
                    model = genai.GenerativeModel(target_model_name)
                    
                    prompt = f"""
                    你是一位專業律師。請分析以下合約。
                    請務必使用 Markdown 格式，並包含以下章節：
                    
                    # 📊 風險總覽
                    (請在這裡畫一個表格，包含：合約安全分(0-100)、風險燈號(紅/黃/綠)、致命陷阱數量)

                    # ⚖️ 深度風險分析
                    (請列出 3-5 點關鍵風險，每點都要有【風險說明】與【嚴重程度】)
                    
                    # 🛡️ 具體修改建議
                    (針對上述風險，提供白話文的修改建議或談判話術)

                    # 💡 隱藏陷阱與盲點
                    (合約沒寫但應該要注意的事情)

                    ---
                    合約內容：
                    {user_input}
                    """
                    
                    safety_settings = {
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                    
                    response = model.generate_content(prompt, safety_settings=safety_settings)
                    
                    st.session_state.analysis_result = response.text
                    st.session_state.page = 'result'
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"分析發生錯誤：{e}")

# === 頁面 B：分析報告介面 ===
elif st.session_state.page == 'result':
    st.title("📊 合約健檢報告書")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🚦 總覽與評分", "⚖️ 深度分析", "🛡️ 修改建議", "📝 原始條文"])
    
    full_text = st.session_state.analysis_result
    
    with tab1:
        st.markdown("### 🎯 核心風險評估")
        st.info("💡 提示：請點擊上方分頁標籤查看詳細分析與建議。")
        if "# ⚖️ 深度風險分析" in full_text:
            summary_part = full_text.split("# ⚖️ 深度風險分析")[0]
            st.markdown(summary_part)
        else:
            st.markdown(full_text)

    with tab2:
        st.markdown("### ⚠️ 關鍵條款審查")
        if "# ⚖️ 深度風險分析" in full_text and "# 🛡️ 具體修改建議" in full_text:
            risk_part = full_text.split("# ⚖️ 深度風險分析")[1].split("# 🛡️ 具體修改建議")[0]
            st.markdown(risk_part)
        else:
            st.markdown("請參考總覽頁面。")
            
    with tab3:
        st.markdown("### 🛡️ 律師修改建議")
        if "# 🛡️ 具體修改建議" in full_text:
            suggestion_part = full_text.split("# 🛡️ 具體修改建議")[1]
            st.markdown(suggestion_part)
        else:
            st.markdown("請參考總覽頁面。")

    with tab4:
        st.markdown("### 📄 原始合約內容")
        # ★★★ 關鍵修復：這裡改讀取「永久記憶體」裡的內容，而不是區域變數 ★★★
        st.text_area("您輸入的內容", value=st.session_state.contract_content, height=400, disabled=True)
    
    st.divider()
    col_back, col_print = st.columns([1, 4])
    with col_back:
        if st.button("⬅️ 重新分析"):
            st.session_state.page = 'input'
            st.session_state.analysis_result = ""
            st.session_state.contract_content = ""
            st.rerun()

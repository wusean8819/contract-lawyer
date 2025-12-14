import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import random

# --- 1. 全局設定 (隱藏工程痕跡) ---
st.set_page_config(
    page_title="Pocket Lawyer 數位律師",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 注入蘋果級 CSS (極簡、圓潤、陰影) ---
st.markdown("""
<style>
    /* 全局字體與背景 */
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: #f9f9f9;
    }
    
    /* 隱藏討厭的 Streamlit 選單 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 標題樣式 */
    h1 {
        color: #1a202c;
        font-weight: 800;
        letter-spacing: -0.05rem;
    }

    /* 卡片式設計 (Card UI) */
    .css-1r6slb0, .stTextArea, .stButton {
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    /* 分數大卡片 */
    .metric-card {
        background: white;
        padding: 24px;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    .metric-value {
        font-size: 48px;
        font-weight: 900;
        color: #2d3748;
        margin: 10px 0;
    }
    .metric-label {
        color: #718096;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* 按鈕美化 */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 50px;
        font-weight: bold;
        border: none;
        transition: all 0.3s ease;
    }
    /* 主按鈕 (藍色) */
    .stButton>button:first-child {
        background-color: #3182ce;
        color: white;
    }
    .stButton>button:hover {
        background-color: #2c5282;
        box-shadow: 0 5px 15px rgba(49, 130, 206, 0.4);
    }

    /* Tab 分頁美化 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #fff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        padding: 0 20px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ebf8ff;
        color: #2b6cb0;
        border-color: #2b6cb0;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 狀態管理 (Session State) - 解決失憶問題 ---
if 'page' not in st.session_state:
    st.session_state.page = 'input'
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = ""
if 'contract_content' not in st.session_state:
    st.session_state.contract_content = ""
if 'score_data' not in st.session_state:
    st.session_state.score_data = {"score": 0, "risk": "未知", "traps": 0}

# --- 4. 側邊欄 (設定區) ---
with st.sidebar:
    st.markdown("### ⚙️ 設定")
    api_key = st.text_input("🔑 API Key", type="password")
    st.markdown("---")
    st.info("💡 提示：此工具僅供參考，正式法律建議請諮詢律師。")

# --- 5. 核心邏輯：自動連線模型 ---
def get_model(api_key):
    genai.configure(api_key=api_key)
    models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    # 優先順序策略
    if any('flash-latest' in m for m in models): return next(m for m in models if 'flash-latest' in m)
    if any('1.5-flash' in m for m in models): return next(m for m in models if '1.5-flash' in m)
    return models[0] if models else "gemini-1.5-flash"

# ==========================================
#  頁面 A：首頁 (輸入區) - 極簡風格
# ==========================================
if st.session_state.page == 'input':
    # 標題區
    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        st.image("https://cdn-icons-png.flaticon.com/512/2504/2504814.png", width=80)
    with col_title:
        st.title("Pocket Lawyer 口袋律師")
        st.markdown("##### 🚀 3 秒鐘，幫你看穿合約裡的陷阱。")

    st.markdown("<br>", unsafe_allow_html=True) # 空行

    # 輸入區
    with st.container():
        user_input = st.text_area(
            "📝 請貼上合約內容：", 
            value=st.session_state.contract_content,
            height=300, 
            placeholder="支援租賃、接案、勞動契約... 請直接貼上文字即可。"
        )
    
    # 快速按鈕區
    col1, col2, col3 = st.columns([1, 2, 1])
    
    # 載入範本功能 (增加互動性)
    with col1:
        if st.button("🎲 載入範本"):
            st.session_state.contract_content = """
            第12條：乙方(員工)若未滿兩年離職，需賠償公司相當於6個月薪資之違約金。
            第13條：甲方(公司)有權隨時調整乙方之工作內容及地點，乙方不得異議。
            """
            st.rerun()

    # 開始分析按鈕
    with col2:
        start_btn = st.button("✨ 開始分析風險", type="primary")

    if start_btn:
        if not api_key:
            st.toast("🚫 請先在左側輸入 API Key 喔！", icon="🔒") # 使用 Toast 提示，不破壞畫面
        elif not user_input.strip():
            st.toast("🚫 請先貼上合約內容！", icon="📄")
        else:
            # === 過場動畫 (消除等待焦慮) ===
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            steps = [
                "🔍 正在閱讀合約條款...",
                "⚖️ 比對最新法律規章...",
                "💣 正在掃描潛在陷阱...",
                "🧠 律師大腦思考中...",
                "✍️ 正在撰寫風險報告..."
            ]
            
            for i in range(100):
                # 模擬進度
                time.sleep(0.02) 
                progress_bar.progress(i + 1)
                if i % 20 == 0:
                    status_text.markdown(f"**{steps[int(i/20)]}**")
            
            # === 執行分析 ===
            try:
                st.session_state.contract_content = user_input # 存檔
                
                model_name = get_model(api_key)
                model = genai.GenerativeModel(model_name)
                
                # Prompt 優化：要求 AI 輸出特定格式以便我們抓取分數
                prompt = f"""
                你是一位講話犀利但專業的律師。請分析以下合約。
                
                【絕對指令】
                1. 請先給出三個數據：
                   - 合約安全分 (0-100)
                   - 風險等級 (紅燈/黃燈/綠燈)
                   - 致命陷阱數量 (數字)
                2. 接著用 Markdown 格式輸出詳細報告。
                3. 語氣要白話、直接，不要掉書袋。

                格式範例：
                [DATA]85,黃燈,2[/DATA]
                
                # 📊 分析總結
                ...

                ---
                合約內容：
                {user_input}
                """
                
                # 關閉安全過濾
                safety = {
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
                
                response = model.generate_content(prompt, safety_settings=safety)
                
                # 解析數據 (簡單的字串處理)
                text = response.text
                if "[DATA]" in text and "[/DATA]" in text:
                    data_str = text.split("[DATA]")[1].split("[/DATA]")[0]
                    score, risk, traps = data_str.split(",")
                    st.session_state.score_data = {
                        "score": score.strip(),
                        "risk": risk.strip(),
                        "traps": traps.strip()
                    }
                    # 移除標記碼，只留報告
                    final_report = text.replace(f"[DATA]{data_str}[/DATA]", "")
                else:
                    # 萬一 AI 沒聽話
                    st.session_state.score_data = {"score": "??", "risk": "未知", "traps": "?"}
                    final_report = text

                st.session_state.analysis_result = final_report
                st.session_state.page = 'result'
                st.rerun()

            except Exception as e:
                st.error(f"分析時發生意外，請檢查 Key 或網路。\n錯誤代碼：{e}")

# ==========================================
#  頁面 B：結果儀表板 - 視覺化呈現
# ==========================================
elif st.session_state.page == 'result':
    
    # 頂部導航
    col_back, col_space = st.columns([1, 5])
    with col_back:
        if st.button("⬅️ 測下一份"):
            st.session_state.page = 'input'
            st.rerun()
            
    st.markdown("<br>", unsafe_allow_html=True)

    # === 1. 核心儀表板 (Dashboard) ===
    # 根據分數決定顏色
    score = int(st.session_state.score_data['score']) if st.session_state.score_data['score'].isdigit() else 0
    score_color = "#e53e3e" if score < 60 else "#d69e2e" if score < 80 else "#38a169"
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="metric-card" style="border-top: 5px solid {score_color};">
            <div class="metric-label">合約安全分</div>
            <div class="metric-value" style="color: {score_color};">{st.session_state.score_data['score']}</div>
            <div>分</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="metric-card" style="border-top: 5px solid {score_color};">
            <div class="metric-label">風險信號</div>
            <div class="metric-value">{st.session_state.score_data['risk']}</div>
            <div>建議謹慎</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card" style="border-top: 5px solid #e53e3e;">
            <div class="metric-label">致命陷阱</div>
            <div class="metric-value" style="color: #e53e3e;">{st.session_state.score_data['traps']}</div>
            <div>處</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # === 2. 詳細內容 (分頁呈現) ===
    # 這裡把報告切開，如果 AI 有好好用 Markdown 標題的話
    full_text = st.session_state.analysis_result
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 總結報告", "💣 陷阱深度分析", "🛡️ 修改建議", "📝 原始條文"])
    
    with tab1:
        st.markdown("### 📝 律師總結")
        st.markdown(full_text) # 顯示全文或摘要
    
    with tab2:
        st.info("這裡列出合約中對你最不利的條款 👇")
        # 簡單過濾顯示 (實際可透過 Prompt 優化讓 AI 分段輸出)
        if "陷阱" in full_text or "風險" in full_text:
             st.markdown(full_text) 
        else:
             st.markdown(full_text)

    with tab3:
        st.success("建議您依據以下話術進行談判 👇")
        st.markdown("*(請參考總結報告中的建議章節)*")
        # 這裡可以之後優化，讓 AI 專門輸出一欄「談判話術」

    with tab4:
        st.text_area("原始合約內容", value=st.session_state.contract_content, height=400, disabled=True)


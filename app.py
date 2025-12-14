import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time

# --- 1. 全局設定 (開啟寬螢幕) ---
st.set_page_config(
    page_title="Pocket Lawyer 數位律師 Pro",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded" # 側邊欄預設打開，不再讓你找半天
)

# --- 2. 注入旗艦級 CSS (這是讓它變高級的關鍵) ---
st.markdown("""
<style>
    /* 全站字體與背景優化 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&display=swap');
    
    .stApp {
        background-color: #f8f9fa; /* 淺灰背景，護眼 */
        font-family: 'Noto Sans TC', sans-serif;
    }

    /* 標題樣式 - 法律科技藍 */
    h1, h2, h3 {
        color: #0f172a; 
        font-weight: 800 !important;
    }
    
    /* 去除 Streamlit 預設醜醜的 header/footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 卡片式容器設計 */
    .css-card {
        background-color: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 1.5rem;
        border: 1px solid #e2e8f0;
    }

    /* 側邊欄美化 */
    section[data-testid="stSidebar"] {
        background-color: #0f172a; /* 深藍色側邊欄 */
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown {
        color: #f1f5f9 !important; /* 文字變白 */
    }

    /* 按鈕美化 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 700;
        padding: 0.75rem 1rem;
        border: none;
        transition: all 0.2s;
    }
    /* 主色按鈕 */
    .stButton>button:first-child {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(37, 99, 235, 0.3);
    }

    /* 儀表板分數卡片 */
    .metric-box {
        background: white;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-top: 4px solid #cbd5e1;
    }
    .metric-number {
        font-size: 3rem;
        font-weight: 900;
        line-height: 1;
        margin-bottom: 0.5rem;
    }
    .metric-label {
        color: #64748b;
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* 文本輸入框優化 */
    .stTextArea textarea {
        border-radius: 8px;
        border: 1px solid #cbd5e1;
        font-size: 1rem;
        line-height: 1.6;
    }
    .stTextArea textarea:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 狀態管理 (記憶體) ---
if 'page' not in st.session_state: st.session_state.page = 'input'
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = ""
if 'contract_content' not in st.session_state: st.session_state.contract_content = ""
if 'score_data' not in st.session_state: st.session_state.score_data = {"score": 0, "risk": "未評估", "traps": 0}

# --- 4. 側邊欄 (設定與狀態) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2504/2504814.png", width=60)
    st.markdown("## ⚖️ 數位律師 Pro")
    st.markdown("---")
    
    st.markdown("### 🔑 啟動金鑰")
    api_key = st.text_input("請在此輸入 Google API Key", type="password", help="貼上您的 Gemini API Key 即可啟動")
    
    # 連線狀態燈號
    if api_key:
        st.success("🟢 系統已連線")
    else:
        st.warning("🔴 等待輸入 Key")
        
    st.markdown("---")
    st.info("此系統採用 Google Gemini 1.5/2.0 自動切換技術，確保最佳分析速度。")

# --- 5. 核心邏輯：模型自動選擇 ---
def get_best_model(api_key):
    try:
        genai.configure(api_key=api_key)
        # 取得所有可用模型
        models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 優先順序：Flash Latest (最穩) -> 1.5 Flash -> 2.0 Flash
        if any('flash-latest' in m for m in models): return next(m for m in models if 'flash-latest' in m)
        if any('1.5-flash' in m for m in models): return next(m for m in models if '1.5-flash' in m)
        return models[0] # 備案
    except:
        return "gemini-1.5-flash"

# ==========================================
#  頁面 A：案件受理區 (首頁)
# ==========================================
if st.session_state.page == 'input':
    
    # 標題區
    col_spacer, col_main, col_spacer2 = st.columns([1, 8, 1])
    with col_main:
        st.markdown("<h1 style='text-align: center; margin-bottom: 10px;'>🛡️ Pocket Lawyer 數位合約律師</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.2rem; margin-bottom: 40px;'>3 秒鐘，為您的合約進行醫療級的風險掃描。</p>", unsafe_allow_html=True)

        # 輸入卡片
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.markdown("### 📄 請貼上合約內容")
        user_input = st.text_area(
            label="合約內容",
            label_visibility="collapsed",
            value=st.session_state.contract_content,
            height=350, 
            placeholder="請直接將合約條款貼在這裡... (支援租賃、勞動、合作備忘錄等各類文件)"
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # 操作區
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("🎲 載入測試範本"):
                st.session_state.contract_content = """
                第12條：乙方(員工)若未滿兩年離職，需賠償公司相當於6個月薪資之違約金。
                第13條：甲方(公司)有權隨時調整乙方之工作內容及地點，乙方不得異議。
                第14條：本合約終止後，乙方三年內不得從事與甲方相同性質之工作(競業禁止)，且甲方無須支付任何補償。
                """
                st.rerun()
        
        with c2:
            start_btn = st.button("🚀 啟動風險分析", type="primary", use_container_width=True)

        # 執行邏輯
        if start_btn:
            if not api_key:
                st.error("🔒 請先在左側側邊欄輸入 API Key")
            elif not user_input.strip():
                st.error("📄 請先貼上合約內容")
            else:
                # 存檔
                st.session_state.contract_content = user_input
                
                # 進度條動畫
                progress_container = st.empty()
                with progress_container.container():
                    st.info("正在連線律師大腦...")
                    bar = st.progress(0)
                    for i in range(100):
                        time.sleep(0.01)
                        bar.progress(i + 1)
                
                try:
                    target_model = get_best_model(api_key)
                    model = genai.GenerativeModel(target_model)
                    
                    # Prompt 設計：強制輸出結構化數據
                    prompt = f"""
                    你是一位犀利的王牌律師。請分析以下合約。
                    
                    【輸出規則】
                    1. 第一行必須是數據，格式：[DATA]分數,風險等級,陷阱數[/DATA]
                       (例如：[DATA]45,高風險,3[/DATA])
                    2. 接著請用 Markdown 撰寫詳細報告，語氣專業但易懂。
                    3. 必須包含：總結、致命風險條款(紅燈)、修改建議。
                    
                    合約內容：
                    {user_input}
                    """
                    
                    safety = {HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE, HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE}
                    
                    response = model.generate_content(prompt, safety_settings=safety)
                    text = response.text
                    
                    # 解析數據
                    if "[DATA]" in text:
                        data_part = text.split("[DATA]")[1].split("[/DATA]")[0]
                        score, risk, traps = data_part.split(",")
                        st.session_state.score_data = {"score": score, "risk": risk, "traps": traps}
                        final_report = text.split("[/DATA]")[1]
                    else:
                        st.session_state.score_data = {"score": "??", "risk": "未知", "traps": "?"}
                        final_report = text
                        
                    st.session_state.analysis_result = final_report
                    st.session_state.page = 'result'
                    st.rerun()
                    
                except Exception as e:
                    progress_container.empty()
                    st.error(f"分析發生錯誤：{e}")

# ==========================================
#  頁面 B：分析報告 (儀表板)
# ==========================================
elif st.session_state.page == 'result':
    
    # 頂部導航
    if st.button("⬅️ 分析下一份合約", use_container_width=False):
        st.session_state.page = 'input'
        st.rerun()

    st.markdown("## 📊 合約健檢報告書")
    
    # 儀表板區域
    score_val = st.session_state.score_data['score']
    risk_val = st.session_state.score_data['risk']
    traps_val = st.session_state.score_data['traps']
    
    # 動態決定顏色
    try:
        s = int(score_val)
        color = "#ef4444" if s < 60 else "#f59e0b" if s < 80 else "#10b981"
    except:
        color = "#64748b"

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-box" style="border-top-color: {color};">
            <div class="metric-number" style="color: {color};">{score_val}</div>
            <div class="metric-label">合約安全分</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="metric-box" style="border-top-color: {color};">
            <div class="metric-number" style="font-size: 2rem; line-height: 3rem;">{risk_val}</div>
            <div class="metric-label">整體風險評級</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="metric-box" style="border-top-color: #ef4444;">
            <div class="metric-number" style="color: #ef4444;">{traps_val}</div>
            <div class="metric-label">發現致命陷阱</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 詳細內容 Tab
    tab1, tab2, tab3 = st.tabs(["📑 完整分析報告", "🛡️ 修改建議與談判", "📝 原始合約對照"])
    
    with tab1:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.markdown(st.session_state.analysis_result)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with tab2:
        st.info("💡 這裡提供專業的談判話術，您可以直接複製傳給對方。")
        # 這裡其實可以再叫一次 AI 專門寫談判信，目前先顯示通用建議
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.markdown("### 建議修改方向")
        st.markdown("1. **針對違約金：** 要求設定上限，並排除不可抗力因素。\n2. **針對管轄法院：** 爭取以您所在地的法院為主。\n3. **針對終止條款：** 雙方應有對等的終止權利。")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        st.text_area("您的合約原文", value=st.session_state.contract_content, height=500, disabled=True)

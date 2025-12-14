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
        st.markdown("<h1 style='text-align: center; margin-bottom: 10px;'>🛡️ Pocket Lawyer 數位合約律

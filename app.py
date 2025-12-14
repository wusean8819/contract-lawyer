import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import pypdf
import docx
import re 

# --- 1. 全局設定 ---
st.set_page_config(
    page_title="Pocket Lawyer 數位律師",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS 樣式 (修復進度條顯示問題) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
    
    :root {
        --primary: #2563eb;    
        --success: #10b981;    
        --danger: #ef4444;     
        --bg: #f8fafc;         
        --card: #ffffff;
    }

    .stApp { background-color: var(--bg); font-family: 'Noto Sans TC', sans-serif; }
    #MainMenu, footer, header {visibility: hidden;}
    
    /* 進度條 - 強制置頂並確保可見 */
    .progress-container {
        padding: 20px 0 40px 0;
        background: transparent;
    }
    .progress-track {
        display: flex; justify-content: space-between; align-items: center;
        position: relative; max-width: 800px; margin: 0 auto;
    }
    .progress-step {
        text-align: center; font-size: 0.9rem; color: #94a3b8; font-weight: 600; 
        position: relative; z-index: 2; background: var(--bg); padding: 0 10px;
    }
    .progress-step.active { color: var(--primary); }
    .progress-step.completed { color: var(--success); }
    
    .step-icon {
        width: 32px; height: 32px; background: #cbd5e1; border-radius: 50%;
        margin: 0 auto 8px; display: flex; align-items: center; justify-content: center;
        font-weight: bold; color: white; transition: all 0.3s;
    }
    .progress-step.active .step-icon { background: var(--primary); box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.2); }
    .progress-step.completed .step-icon { background: var(--success); }
    
    /* 連接線 */
    .progress-line-bg {
        position: absolute; top: 16px; left: 0; width: 100%; height: 3px; 
        background: #e2e8f0; z-index: 1;
    }
    
    /* 卡片設計 */
    .css-card {
        background: var(--card); padding: 2.5rem; border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;
        margin-bottom: 20px;
    }

    /* 儀表板 */
    .stat-box { text-align: center; padding: 10px; }
    .stat-num { font-size: 4rem; font-weight: 800; line-height: 1; margin-bottom: 5px; }
    .stat-label { font-size: 1rem; color: #64748b; font-weight: 500; }

    /* 按鈕優化 */
    .stButton>button {
        border-radius: 8px; font-weight: 600; height: 3.5rem; font-size: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;
    }
    .stButton>button:hover { border-color: var(--primary); color: var(--primary); }
    /* Primary 按鈕 */
    div[data-testid="stVerticalBlock"] > div > div > div > div > .stButton > button:active {
        background-color: var(--primary); color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 狀態管理 ---
if 'page' not in st.session_state: st.session_state.page = 'input'
if 'step' not in st.session_state: st.session_state.step = 1 
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = ""
if 'negotiation_tips' not in st.session_state: st.session_state.negotiation_tips = "" 
if 'contract_content' not in st.session_state: st.session_state.contract_content = ""
# 這裡初始化為 0 (int)，避免一開始就報錯
if 'score_data' not in st.session_state: st.session_state.score_data = {"score": 0, "risk": "未評估", "traps": 0}

# --- 4. 關鍵修復：強力數字提取器 ---
def safe_extract_score(text):
    """ 
    不管 AI 回傳什麼鬼東西 (例如 '1/10', 'Score: 80'), 
    我們都強制轉成 0-100 的整數。
    """
    try:
        # 1. 轉字串
        text_str = str(text)
        # 2. 抓出所有數字
        nums = re.findall(r'\d+', text_str)
        if not nums: return 0
        
        val = int(nums[0])
        
        # 3. 特殊邏輯：如果 AI 給 1/10 (即 1 分)，我們自動修正為 10 分
        if val <= 10 and ("10" in text_str or "/" in text_str):
            return val * 10
            
        # 4. 確保不超過 100
        return min(val, 100)
    except:
        return 0

def safe_extract_int(text):
    """ 一般數字提取 (用於陷阱數量) """
    try:
        nums = re.findall(r'\d+', str(text))
        return int(nums[0]) if nums else 0
    except: return 0

def render_progress(current_step):
    """ 渲染進度條 (純 HTML/CSS) """
    steps = ["上傳合約", "風險診斷", "詳細分析", "談判策略"]
    
    steps_html = ""
    for i, label in enumerate(steps, 1):
        status = "completed" if i < current_step else "active" if i == current_step else ""
        icon = "✓" if i < current_step else str(i)
        steps_html += f"""
        <div class="progress-step {status}">
            <div class="step-icon">{icon}</div>
            <div>{label}</div>
        </div>
        """
    
    st.markdown(f"""
    <div class="progress-container">
        <div class="progress-track">
            <div class="progress-line-bg"></div>
            {steps_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def get_model(key):
    try:
        genai.configure(api_key=key)
        models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if any('flash-latest' in m for m in models): return next(m for m in models if 'flash-latest' in m)
        return models[0] if models else "gemini-1.5-flash"
    except: return "gemini-1.5-flash"

def read_file(uploaded_file):
    try:
        text = ""
        if uploaded_file.type == "application/pdf":
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages: text += page.extract_text() + "\n"
        elif "word" in uploaded_file.type:
            doc = docx.Document(uploaded_file)
            text = "\n".join([para.text for para in doc.paragraphs])
        elif "text" in uploaded_file.type:
            text = uploaded_file.getvalue().decode("utf-8")
        return text
    except: return ""

# --- 5. Secrets ---
api_key = None
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
except: pass

with st.sidebar:
    st.header("⚙️ 設定")
    if not api_key:
        api_key = st.text_input("API Key", type="password")
    st.markdown("---")
    if st.button("🔄 重置"):
        st.session_state.clear()
        st.rerun()

# --- 主程式 ---

# 每一頁的最

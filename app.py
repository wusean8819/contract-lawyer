import streamlit as st
import google.generativeai as genai
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

# --- 2. CSS 樣式 (優化版) ---
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
    
    /* 進度條容器 */
    .progress-container {
        padding: 20px 0;
        margin-bottom: 20px;
        background-color: var(--bg);
        position: sticky; top: 0; z-index: 999; /* 強制置頂 */
    }
    .progress-track {
        display: flex; justify-content: space-between; align-items: center;
        max-width: 600px; margin: 0 auto; position: relative;
    }
    .progress-step {
        text-align: center; font-size: 0.9rem; color: #94a3b8; font-weight: 600; 
        position: relative; z-index: 2; background: var(--bg); padding: 0 10px; width: 80px;
    }
    .progress-step.active { color: var(--primary); }
    .progress-step.completed { color: var(--success); }
    
    .step-icon {
        width: 30px; height: 30px; background: #cbd5e1; border-radius: 50%;
        margin: 0 auto 5px; display: flex; align-items: center; justify-content: center;
        font-weight: bold; color: white; transition: all 0.3s;
    }
    .progress-step.active .step-icon { background: var(--primary); box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.2); }
    .progress-step.completed .step-icon { background: var(--success); }
    
    .progress-line-bg {
        position: absolute; top: 15px; left: 0; width: 100%; height: 2px; 
        background: #e2e8f0; z-index: 1;
    }

    /* 卡片優化 */
    .css-card {
        background: var(--card); padding: 2rem; border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;
        margin-bottom: 20px;
    }
    
    /* 錯誤訊息美化 */
    .stException { display: none !important; } /* 隱藏原生報錯 */
    .error-box {
        background: #fef2f2; border: 1px solid #fee2e2; color: #991b1b;
        padding: 15px; border-radius: 8px; margin: 10px 0;
    }

    /* 按鈕 */
    .stButton>button {
        border-radius: 8px; font-weight: 600; height: 3rem; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 狀態管理 (初始化) ---
# 確保所有變數都存在，防止 NameError
if 'page' not in st.session_state: st.session_state.page = 'input'
if 'step' not in st.session_state: st.session_state.step = 1 
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = ""
if 'negotiation_tips' not in st.session_state: st.session_state.negotiation_tips = "" 
if 'contract_content' not in st.session_state: st.session_state.contract_content = ""
if 'score_data' not in st.session_state: st.session_state.score_data = {"score": 0, "risk": "未評估", "traps": 0}

# --- 4. 輔助函數 ---
def safe_extract_score(text):
    """ 超級防呆：防止 1/10 或文字導致崩潰 """
    try:
        text_str = str(text).strip()
        fraction_match = re.search(r'(\d+)\s*/\s*(\d+)', text_str)
        if fraction_match:
            num = float(fraction_match.group(1))
            den = float(fraction_match.group(2))
            if den > 0: return int((num / den) * 100)
        nums = re.findall(r'\d+', text_str)
        if nums:
            val = int(nums[0])
            if val <= 10 and len(text_str) < 5: return val * 10
            return min(val, 100)
        return 0
    except: return 0

def safe_extract_int(text):
    try:
        nums = re.findall(r'\d+', str(text))
        return int(nums[0]) if nums else 0
    except: return 0

def render_progress(current_step):
    steps = ["上傳", "診斷", "分析", "談判"]
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

def get_model(key):
    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-1.5-flash")

# --- 5. 抓取 API Key ---
api_key = None
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
except: pass

with st.sidebar:
    st.header("⚙️ 設定")
    if not api_key:
        api_key = st.text_input("API Key", type="password")
        st.caption("💡 提示：在 Secrets 設定 GOOGLE_API_KEY 可免輸入")
    
    st.markdown("---")
    if st.button("🔄 重置系統"):
        st.session_state.clear()
        st.rerun()

# --- 主程式邏輯 (全域防護) ---
try:
    # 永遠顯示進度條
    render_progress(st.session_state.step)

    # === 頁面 1: 輸入 ===
    if st.session_state.page == 'input':
        st.markdown("<h1 style='text-align: center; color: #1e293b;'>Pocket Lawyer 數位律師</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b;'>拖放合約，AI 立即為您偵測法律陷阱。</p>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 6, 1])
        with col2:
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            uploaded_file = st.file_uploader("📂 上傳檔案 (PDF / Word / TXT)", type=["pdf", "docx", "txt"])
            
            if uploaded_file:
                text = read_file(uploaded_file)
                if len(text) > 10:
                    st.session_state.contract_content = text
                    st.success(f"✅ 已讀取：{uploaded_file.name}")
            
            user_input = st.text_area("或貼上條款內容：", value=st.session_state.contract_content, height=200)
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("🚀 開始分析", type="primary"):
                st.session_state.contract_content = user_input
                if not user_input.strip() and not api_key:
                    st.error("⚠️ 請確認 API Key 已設定且內容不為空")
                else:
                    with st.spinner("⚖️ AI 律師正在閱卷中..."):
                        try:
                            model = get_model(api_key)
                            prompt = f"""
                            你是一位專業律師。請分析以下合約。
                            【輸出規則】
                            1. [BLOCK_DATA]分數

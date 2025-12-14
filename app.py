import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import pypdf
import docx
import re # 引入正規表達式，這是處理複雜字串的關鍵工具

# --- 1. 全局設定 ---
st.set_page_config(
    page_title="Pocket Lawyer 數位律師",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS 樣式 (優化進度條與閱讀體驗) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
    
    :root {
        --primary: #2563eb;    
        --success: #10b981;    
        --danger: #ef4444;     
        --bg: #f8fafc;         
        --card: #ffffff;
        --text-dark: #1e293b;
    }

    .stApp { background-color: var(--bg); font-family: 'Noto Sans TC', sans-serif; color: var(--text-dark); }
    #MainMenu, footer, header {visibility: hidden;}
    
    /* --- 進度條優化 --- */
    .progress-container {
        padding: 20px 0 40px 0; margin-bottom: 20px;
    }
    .progress-track {
        display: flex; justify-content: space-between; align-items: center;
        position: relative; max-width: 800px; margin: 0 auto;
    }
    .progress-step {
        text-align: center; font-size: 0.9rem; color: #94a3b8; font-weight: 600; 
        position: relative; z-index: 2; background: var(--bg); padding: 0 15px;
    }
    .progress-step.active { color: var(--primary); }
    .progress-step.completed { color: var(--success); }
    
    .step-icon {
        width: 32px; height: 32px; background: #cbd5e1; border-radius: 50%;
        margin: 0 auto 8px; display: flex; align-items: center; justify-content: center;
        font-weight: bold; color: white; transition: all 0.3s; font-size: 1rem;
    }
    .progress-step.active .step-icon { background: var(--primary); box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.2); }
    .progress-step.completed .step-icon { background: var(--success); }
    
    .progress-line-bg {
        position: absolute; top: 16px; left: 0; width: 100%; height: 3px; 
        background: #e2e8f0; z-index: 1;
    }
    
    /* --- 卡片與內容 --- */
    .css-card {
        background: var(--card); padding: 2.5rem; border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;
        margin-bottom: 20px;
    }
    
    /* 優化 Markdown 閱讀體驗 */
    .markdown-text h3 { color: var(--danger) !important; margin-top: 1.5rem; }
    .markdown-text strong { color: var(--text-dark); font-weight: 700; }
    .markdown-text li { margin-bottom: 0.5rem; }

    /* 儀表板 */
    .stat-box { text-align: center; padding: 10px; }
    .stat-num { font-size: 4rem; font-weight: 800; line-height: 1; margin-bottom: 5px; }
    .stat-label { font-size: 1rem; color: #64748b; font-weight: 500; }

    /* 按鈕優化 */
    .stButton>button {
        border-radius: 8px; font-weight: 600; height: 3.5rem; font-size: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;
        transition: all 0.2s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
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
# 初始化為 0，避免報錯
if 'score_data' not in st.session_state: st.session_state.score_data = {"score": 0, "risk": "未評估", "traps": 0}

# --- 4. 關鍵修復：超級防呆分數提取器 ---
def safe_extract_score(text):
    """ 
    核心功能：處理 AI 回傳的各種奇葩分數格式
    例如: "1/10", "Score: 85", "90分", "極高風險(10)"
    """
    try:
        text_str = str(text).strip()
        
        # 優先處理分數格式 "x/y"
        fraction_match = re.search(r'(\d+)\s*/\s*(\d+)', text_str)
        if fraction_match:
            numerator = int(fraction_match.group(1))
            denominator = int(fraction_match.group(2))
            if denominator > 0:
                # 轉換為百分制
                return int((numerator / denominator) * 100)

        # 如果不是分數，抓取第一個出現的數字
        nums = re.findall(r'\d+', text_str)
        if nums:
            val = int(nums[0])
            # 如果數字很小且原文包含"10"，假設是十分制，乘以 10
            if val <= 10 and "10" in text_str:
                return val * 10
            return min(val, 100) # 確保不超過 100

        return 0 # 沒抓到數字就回傳 0
    except:
        return 0 # 發生任何錯誤都回傳 0，保證不崩潰

def safe_extract_int(text):
    """ 一般數字提取 (用於陷阱數量) """
    try:
        nums = re.findall(r'\d+', str(text))
        return int(nums[0]) if nums else 0
    except: return 0

def render_progress(current_step):
    """ 渲染進度條 (純 HTML/CSS) """
    steps = ["上傳合約", "風險診斷", "深度剖析", "談判策略"]
    
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

# ==========================================
#  頁面 A：輸入區 (Step 1)
# ==========================================
if st.session_state.page == 'input':
    
    # ★★★ 強制在最上方渲染進度條 ★★★
    render_progress(1)

    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="font-size: 2rem; color: #1e293b;">數位合約律師</h1>
        <p style="color: #64748b;">拖放合約，AI 立即為您偵測法律陷阱。</p>
    </div>
    """, unsafe_allow_html=True)

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

        if st.button("🚀 開始分析", type="primary", use_container_width=True):
            st.session_state.contract_content = user_input
            if not user_input.strip() and not api_key:
                st.error("⚠️ 請確認 API Key 與合約內容")
            else:
                progress_bar = st.progress(0)
                try:
                    model = genai.GenerativeModel(get_model(api_key))
                    # ★★★ 優化 Prompt：要求更視覺化的 Markdown 輸出 ★★★
                    prompt = f"""
                    你是一位犀利的王牌律師。請分析以下合約。
                    
                    【輸出規則】
                    1. [BLOCK_DATA]分數(0-100),風險等級,陷阱數[/BLOCK_DATA]
                    2. [BLOCK_REPORT] 請用高度視覺化的 Markdown 格式列出 3 個最致命的風險。
                       格式要求：
                       ### 🔴 風險標題 (請用紅燈 Emoji 開頭)
                       **嚴重程度：極高**
                       **風險詳情：** 這裡寫詳細解釋，請多用條列式和粗體強調關鍵字，讓讀者一眼看出重點。
                       ---
                       (下一個風險...)
                    3. [BLOCK_TIPS] 針對風險提供談判話術，請用條列式列出。
                    
                    合約：{user_input}
                    """
                    response = model.generate_content(prompt)
                    text = response.text
                    progress_bar.progress(100)
                    
                    # 解析
                    if "[BLOCK_DATA]" in text:
                        data = text.split("[BLOCK_DATA]")[1].split("[/BLOCK_DATA]")[0].split(",")
                        # 存原始資料
                        st.session_state.score_data = {
                            "score": data[0], 
                            "risk": data[1].strip(),
                            "traps": data[2]
                        }
                    
                    if "[BLOCK_REPORT]" in text:
                        st.session_state.analysis_result = text.split("[BLOCK_REPORT]")[1].split("[/BLOCK_REPORT]")[0]
                    else: st.session_state.analysis_result = text

                    if "[BLOCK_TIPS]" in text:
                        st.session_state.negotiation_tips = text.split("[BLOCK_TIPS]")[1].split("[/BLOCK_TIPS]")[0]
                    else: st.session_state.negotiation_tips = "請參考報告。"
                    
                    st.session_state.page = 'result'
                    st.session_state.step = 2
                    st.rerun()
                    
                except Exception as e:
                    st.error("分析錯誤，請重試或是檢查 Key")
                    # st.write(e) # 不顯示醜醜的錯誤碼給使用者看

# ==========================================
#  頁面 B：結果流程
# ==========================================
elif st.session_state.page == 'result':
    
    current_step = st.session_state.step
    # ★★★ 強制在最上方渲染進度條 ★★★
    render_progress(current_step)

    # --- Step 2: 儀表板 ---
    if current_step == 2:
        # ★★★ 關鍵修復：使用 safe_extract_score 處理分數 ★★★
        raw_score = st.session_state.score_data['score']
        score = safe_extract_score(raw_score)
        
        traps = safe_extract_int(st.session_state.score_data['traps'])
        risk = st.session_state.score_data['risk']
        
        color = "#ef4444" if score < 60 else "#f59e0b" if score < 80 else "#10b981"
        
        st.markdown(f"""
        <div class="css-card">
            <h3 style="text-align:center; color:#1e293b;">📊 風險診斷報告</h3>
            <div style="display: flex; justify-content: space-around; margin-top: 20px;">
                <div class="stat-box">
                    <div class="stat-num" style="color: {color};">{score}</div>
                    <div class="stat-label">安全評分</div>
                </div>
                <div class="stat-box">
                    <div class="stat-num" style="font-size: 2.5rem; line-height: 4rem;">{risk}</div>
                    <div class="stat-label">風險等級</div>
                </div>
                <div class="stat-box">
                    <div class="stat-num" style="color: #ef4444;">{traps}</div>
                    <div class="stat-label">致命陷阱</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("查看風險細節 ➡️", type="primary", use_container_width=True):
                st.session_state.step = 3
                st.rerun()

    # --- Step 3: 詳細分析 (優化閱讀體驗) ---
    elif current_step == 3:
        st.markdown('<div class="css-card markdown-text">', unsafe_allow_html=True)
        st.markdown("### ⚠️ 深度剖析")
        # 這裡顯示的是優化過、帶有 Emoji 和粗體的 Markdown
        st.markdown(st.session_state.analysis_result)
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.expander("📄 原始合約內容"):
            st.text_area("", value=st.session_state.contract_content, height=200, disabled=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 返回總覽"):
                st.session_state.step = 2
                st.rerun()
        with c2:
            if st.button("獲取談判策略 ➡️", type="primary"):
                st.session_state.step = 4
                st.rerun()

    # --- Step 4: 談判 ---
    elif current_step == 4:
        st.info("這是 AI 為您擬定的談判劇本，請點擊右上角複製。")
        st.code(st.session_state.negotiation_tips, language="markdown")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 查看分析"):
                st.session_state.step = 3
                st.rerun()
        with c2:
            if st.button("🔄 分析下一份合約"):
                st.session_state.page = 'input'
                st.session_state.contract_content = ""
                st.session_state.step = 1
                st.rerun()

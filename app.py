import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import pypdf
import docx
import re # 引入正規表達式，專門用來處理 AI 亂回傳格式的問題

# --- 1. 全局設定 ---
st.set_page_config(
    page_title="Pocket Lawyer 數位律師",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS 樣式 (SaaS 產品級質感) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
    
    :root {
        --primary: #2563eb;    /* 專業藍 */
        --success: #10b981;    /* 成功綠 */
        --danger: #ef4444;     /* 警告紅 */
        --bg: #f8fafc;         /* 淺灰底 */
        --card: #ffffff;
    }

    .stApp { background-color: var(--bg); font-family: 'Noto Sans TC', sans-serif; }
    #MainMenu, footer, header {visibility: hidden;}
    
    /* 進度條容器 */
    .progress-track {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 3rem; padding: 0 20px;
    }
    .progress-step {
        text-align: center; font-size: 0.9rem; color: #94a3b8; font-weight: 600; position: relative; width: 100%;
    }
    .progress-step.active { color: var(--primary); }
    .progress-step.completed { color: var(--success); }
    
    /* 進度條的圓圈 */
    .step-icon {
        width: 30px; height: 30px; background: #e2e8f0; border-radius: 50%;
        margin: 0 auto 10px; display: flex; align-items: center; justify-content: center;
        font-weight: bold; color: white; transition: all 0.3s;
    }
    .progress-step.active .step-icon { background: var(--primary); box-shadow: 0 0 0 5px rgba(37, 99, 235, 0.2); }
    .progress-step.completed .step-icon { background: var(--success); }
    
    /* 連接線 */
    .progress-line {
        position: absolute; top: 15px; left: -50%; width: 100%; height: 3px; background: #e2e8f0; z-index: -1;
    }
    .progress-step:first-child .progress-line { display: none; }
    .progress-step.completed .progress-line { background: var(--success); }

    /* 卡片設計 */
    .css-card {
        background: var(--card); padding: 2.5rem; border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;
    }

    /* 儀表板數字 */
    .stat-box { text-align: center; padding: 15px; }
    .stat-num { font-size: 3.5rem; font-weight: 800; line-height: 1; margin-bottom: 5px; }
    .stat-label { font-size: 0.9rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px; }

    /* 按鈕優化 */
    .stButton>button {
        border-radius: 8px; font-weight: 600; height: 3.5rem; font-size: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: none;
    }
    
    /* 談判便條紙 */
    .negotiation-paper {
        background: #fffbeb; border-left: 4px solid #f59e0b; padding: 20px;
        font-family: 'Courier New', monospace; color: #78350f; line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 狀態管理 ---
if 'page' not in st.session_state: st.session_state.page = 'input'
if 'step' not in st.session_state: st.session_state.step = 1 # 1:上傳, 2:總覽, 3:詳情, 4:談判
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = ""
if 'negotiation_tips' not in st.session_state: st.session_state.negotiation_tips = "" 
if 'contract_content' not in st.session_state: st.session_state.contract_content = ""
if 'score_data' not in st.session_state: st.session_state.score_data = {"score": 0, "risk": "未評估", "traps": 0}

# --- 4. 輔助函數 ---
def safe_extract_number(text):
    """ 強力過濾器：只抓數字，防止 ValueError """
    try:
        # 使用正規表達式抓取字串中所有的數字
        # 例如 "1/10" 會抓到 ["1", "10"]，我們取第一個 "1"
        # "85分" 會抓到 ["85"]
        matches = re.findall(r'\d+', str(text))
        if matches:
            val = int(matches[0])
            # 如果 AI 回傳 1/10，我們假設它是 10 分制，轉換成 100 分制
            if val <= 10 and "10" in str(text): 
                return val * 10 
            return val
        return 0 # 沒抓到數字就回傳 0，避免當機
    except:
        return 0

def render_progress(current_step):
    """ 渲染全域進度條 """
    steps = ["檔案上傳", "風險診斷", "深度剖析", "談判策略"]
    html = '<div class="progress-track">'
    for i, label in enumerate(steps, 1):
        status = "completed" if i < current_step else "active" if i == current_step else ""
        icon = "✓" if i < current_step else str(i)
        html += f"""
        <div class="progress-step {status}">
            <div class="progress-line"></div>
            <div class="step-icon">{icon}</div>
            <div>{label}</div>
        </div>
        """
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

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
    if st.button("🔄 重置所有進度"):
        st.session_state.clear()
        st.rerun()

# ==========================================
#  頁面 A：輸入區 (Step 1)
# ==========================================
if st.session_state.page == 'input':
    
    # ★★★ 關鍵修正：首頁也要顯示進度條 ★★★
    render_progress(1)

    st.markdown("""
    <div style="text-align: center; margin: 30px 0;">
        <h1 style="font-size: 2.5rem; color: #1e293b;">🛡️ Pocket Lawyer 數位律師</h1>
        <p style="color: #64748b; font-size: 1.1rem;">3 秒鐘，為您的合約進行醫療級的風險掃描。</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("📂 拖放檔案至此 (PDF / Word / TXT)", type=["pdf", "docx", "txt"])
        
        if uploaded_file:
            text = read_file(uploaded_file)
            if len(text) > 10:
                st.session_state.contract_content = text
                st.success(f"✅ 已讀取：{uploaded_file.name}")
        
        user_input = st.text_area("或直接貼上條款內容：", value=st.session_state.contract_content, height=200, placeholder="請貼上合約內容...")
        st.markdown('</div>', unsafe_allow_html=True)

        # 這裡改用 primary 藍色按鈕
        if st.button("🚀 開始智能分析", type="primary", use_container_width=True):
            st.session_state.contract_content = user_input
            if not user_input.strip() and not api_key:
                st.error("⚠️ 請確認 API Key 與合約內容是否填寫")
            else:
                progress_bar = st.progress(0)
                try:
                    model = genai.GenerativeModel(get_model(api_key))
                    prompt = f"""
                    你是一位專業律師。請分析以下合約。
                    
                    【嚴格輸出規則】
                    1. [BLOCK_DATA]分數(純數字0-100),風險等級(文字),陷阱數(純數字)[/BLOCK_DATA]
                    2. [BLOCK_REPORT] 請用 Markdown 格式列出最致命的 3 個風險，每個風險都要有標題。
                    3. [BLOCK_TIPS] 針對上述風險，提供一段「可以直接複製」的談判話術。
                    
                    合約：{user_input}
                    """
                    response = model.generate_content(prompt)
                    text = response.text
                    progress_bar.progress(100)
                    
                    # 穩健的解析邏輯
                    if "[BLOCK_DATA]" in text:
                        data = text.split("[BLOCK_DATA]")[1].split("[/BLOCK_DATA]")[0].split(",")
                        
                        # ★★★ 關鍵修正：使用 safe_extract_number 防止 ValueError ★★★
                        st.session_state.score_data = {
                            "score": safe_extract_number(data[0]), 
                            "risk": data[1].strip(),
                            "traps": safe_extract_number(data[2])
                        }
                    
                    if "[BLOCK_REPORT]" in text:
                        st.session_state.analysis_result = text.split("[BLOCK_REPORT]")[1].split("[/BLOCK_REPORT]")[0]
                    else: st.session_state.analysis_result = text

                    if "[BLOCK_TIPS]" in text:
                        st.session_state.negotiation_tips = text.split("[BLOCK_TIPS]")[1].split("[/BLOCK_TIPS]")[0]
                    else: st.session_state.negotiation_tips = "請參考分析報告自行擬定。"
                    
                    # 轉場
                    st.session_state.page = 'result'
                    st.session_state.step = 2
                    st.rerun()
                    
                except Exception as e:
                    st.error("分析過程發生錯誤，請稍後再試。")
                    with st.expander("錯誤代碼"): st.write(e)

# ==========================================
#  頁面 B：結果流程 (Wizard Flow)
# ==========================================
elif st.session_state.page == 'result':
    
    current_step = st.session_state.step
    render_progress(current_step) # 顯示全域進度

    # --- Step 2: 儀表板 ---
    if current_step == 2:
        score = st.session_state.score_data['score']
        risk = st.session_state.score_data['risk']
        traps = st.session_state.score_data['traps']
        
        # 這裡絕對不會再報錯，因為 score 已經被強制轉為 int
        color = "#ef4444" if score < 60 else "#f59e0b" if score < 80 else "#10b981"
        
        st.markdown(f"""
        <div class="css-card">
            <h3 style="text-align:center; margin-bottom:30px;">📊 風險診斷報告</h3>
            <div style="display: flex; justify-content: space-around;">
                <div class="stat-box">
                    <div class="stat-num" style="color: {color};">{score}</div>
                    <div class="stat-label">安全評分</div>
                </div>
                <div class="stat-box">
                    <div class="stat-num">{risk}</div>
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

    # --- Step 3: 詳細分析 ---
    elif current_step == 3:
        st.markdown("### ⚠️ 深度剖析")
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
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
        st.markdown("### 🛡️ 談判行動")
        st.info("這是 AI 為您擬定的談判劇本，請點擊右上角複製。")
        
        # 使用 st.code 讓使用者一鍵複製
        st.code(st.session_state.negotiation_tips, language="markdown")
        
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 查看分析"):
                st.session_state.step = 3
                st.rerun()
        with c2:
            if st.button("🔄 分析下一份合約"):
                st.session_state.page = 'input'
                st.session_state.contract_content = ""
                st.rerun()

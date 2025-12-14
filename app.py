import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import pypdf
import docx

# --- 1. 全局設定 ---
st.set_page_config(
    page_title="Pocket Lawyer 數位律師",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed" # 預設收起，讓畫面更乾淨
)

# --- 2. CSS 極致美化 (去除作業感，增加 SaaS 質感) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
    
    /* 全局變數 */
    :root {
        --primary-color: #2563eb;
        --bg-color: #f1f5f9;
        --card-bg: #ffffff;
        --text-color: #1e293b;
    }

    .stApp { background-color: var(--bg-color); font-family: 'Noto Sans TC', sans-serif; }
    
    /* 隱藏原生元素 */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    /* 進度條樣式 */
    .step-container {
        display: flex; justify-content: space-between; margin-bottom: 2rem;
        background: white; padding: 15px; border-radius: 50px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .step {
        font-weight: bold; color: #94a3b8; padding: 5px 15px; border-radius: 20px; transition: all 0.3s;
    }
    .step.active {
        background-color: var(--primary-color); color: white; box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
    }

    /* 卡片設計 */
    .css-card {
        background-color: var(--card-bg);
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.025);
        border: 1px solid #e2e8f0;
        margin-bottom: 1.5rem;
    }

    /* 風險卡片 */
    .risk-card {
        border-left: 5px solid #ef4444;
        background: #fff; padding: 20px; margin-bottom: 15px; border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* 儀表板數字 */
    .big-number { font-size: 3.5rem; font-weight: 800; line-height: 1; margin-bottom: 0.5rem; }
    
    /* 按鈕優化 */
    .stButton>button {
        border-radius: 10px; height: 3rem; font-weight: 600; border: none;
        transition: transform 0.1s;
    }
    .stButton>button:active { transform: scale(0.98); }
    
    /* 談判框 */
    .negotiation-box {
        background: #eff6ff; border: 1px solid #bfdbfe; color: #1e3a8a;
        padding: 20px; border-radius: 12px; font-size: 1.05rem; line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 狀態管理 (Session State) ---
if 'page' not in st.session_state: st.session_state.page = 'input'
if 'result_step' not in st.session_state: st.session_state.result_step = 1 # 1:總覽, 2:詳情, 3:行動
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = ""
if 'negotiation_tips' not in st.session_state: st.session_state.negotiation_tips = "" 
if 'contract_content' not in st.session_state: st.session_state.contract_content = ""
if 'score_data' not in st.session_state: st.session_state.score_data = {"score": 0, "risk": "未評估", "traps": 0}

# --- 4. Secrets & Model ---
api_key = None
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
except: pass

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

def get_best_model(key):
    try:
        genai.configure(api_key=key)
        models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if any('flash-latest' in m for m in models): return next(m for m in models if 'flash-latest' in m)
        return models[0] if models else "gemini-1.5-flash"
    except: return "gemini-1.5-flash"

# --- 5. 側邊欄 (極簡化) ---
with st.sidebar:
    st.header("⚖️ 設定")
    if not api_key:
        api_key = st.text_input("API Key", type="password")
    
    st.markdown("---")
    if st.button("🔄 重置系統"):
        st.session_state.clear()
        st.rerun()

# ==========================================
#  頁面 A：輸入區 (Landing Page)
# ==========================================
if st.session_state.page == 'input':
    # 標題區
    st.markdown("""
    <div style="text-align: center; margin-bottom: 40px;">
        <h1 style="font-size: 3rem; margin-bottom: 10px;">🛡️ Pocket Lawyer</h1>
        <p style="color: #64748b; font-size: 1.2rem;">3 秒鐘，為您的合約進行醫療級的風險掃描。</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 6, 1])
    with c2:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("📂 拖放檔案上傳 (PDF / Word / TXT)", type=["pdf", "docx", "txt"])
        
        if uploaded_file:
            text = read_file(uploaded_file)
            if len(text) > 20:
                st.session_state.contract_content = text
                st.success(f"已讀取：{uploaded_file.name}")
        
        user_input = st.text_area("或直接貼上條款內容：", value=st.session_state.contract_content, height=200)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("🚀 開始分析", type="primary", use_container_width=True):
            st.session_state.contract_content = user_input
            if not user_input.strip() and not api_key:
                st.error("請確認 Key 與內容")
            else:
                progress = st.progress(0)
                try:
                    model = genai.GenerativeModel(get_best_model(api_key))
                    # Prompt 優化：要求更結構化的 Markdown
                    prompt = f"""
                    你是一位專業律師。請分析以下合約。
                    
                    【輸出指令】
                    1. [BLOCK_DATA]分數,風險等級,陷阱數[/BLOCK_DATA]
                    2. [BLOCK_REPORT] 請用 Markdown 條列式列出 3 個最致命的風險。每個風險請用 **粗體標題** 開頭，然後換行寫解釋。
                    3. [BLOCK_TIPS] 針對上述風險，提供一段「可以直接複製」的談判訊息，語氣要委婉但堅定。
                    
                    合約：{user_input}
                    """
                    response = model.generate_content(prompt)
                    text = response.text
                    
                    # 簡易解析
                    if "[BLOCK_DATA]" in text:
                        data = text.split("[BLOCK_DATA]")[1].split("[/BLOCK_DATA]")[0].split(",")
                        st.session_state.score_data = {"score": data[0], "risk": data[1], "traps": data[2]}
                    
                    if "[BLOCK_REPORT]" in text:
                        st.session_state.analysis_result = text.split("[BLOCK_REPORT]")[1].split("[/BLOCK_REPORT]")[0]
                    else: st.session_state.analysis_result = text

                    if "[BLOCK_TIPS]" in text:
                        st.session_state.negotiation_tips = text.split("[BLOCK_TIPS]")[1].split("[/BLOCK_TIPS]")[0]
                    
                    st.session_state.page = 'result'
                    st.session_state.result_step = 1
                    st.rerun()
                except Exception as e:
                    st.error("分析失敗，請稍後再試")
                    st.write(e)

# ==========================================
#  頁面 B：分步導引結果頁 (Wizard Flow)
# ==========================================
elif st.session_state.page == 'result':
    
    # 上方導航條 (Progress Stepper)
    step = st.session_state.result_step
    st.markdown(f"""
    <div class="step-container">
        <div class="step {'active' if step==1 else ''}">1. 風險總覽</div>
        <div class="step {'active' if step==2 else ''}">2. 深度剖析</div>
        <div class="step {'active' if step==3 else ''}">3. 談判行動</div>
    </div>
    """, unsafe_allow_html=True)

    # --- 步驟 1：儀表板 (Dashboard) ---
    if step == 1:
        score = st.session_state.score_data['score']
        risk = st.session_state.score_data['risk']
        traps = st.session_state.score_data['traps']
        
        color = "#ef4444" if int(score) < 60 else "#f59e0b"
        
        st.markdown(f"""
        <div class="css-card" style="text-align: center;">
            <h2 style="margin-bottom: 30px;">📊 合約健康度診斷</h2>
            <div style="display: flex; justify-content: space-around; flex-wrap: wrap;">
                <div>
                    <div class="big-number" style="color: {color};">{score}</div>
                    <div style="color: #64748b;">安全評分</div>
                </div>
                <div>
                    <div class="big-number">{risk}</div>
                    <div style="color: #64748b;">風險等級</div>
                </div>
                <div>
                    <div class="big-number" style="color: #ef4444;">{traps}</div>
                    <div style="color: #64748b;">致命陷阱</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("查看風險詳情 ➡️", type="primary", use_container_width=True):
                st.session_state.result_step = 2
                st.rerun()

    # --- 步驟 2：詳細分析 (Deep Dive) ---
    elif step == 2:
        st.markdown("### ⚠️ 發現以下關鍵風險")
        
        # 把 AI 的報告包在卡片裡，而不是直接噴字
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.markdown(st.session_state.analysis_result)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 原始條文 (收折起來，不佔空間)
        with st.expander("📄 點擊查看原始合約內容"):
            st.text_area("", value=st.session_state.contract_content, height=300, disabled=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 返回總覽"):
                st.session_state.result_step = 1
                st.rerun()
        with c2:
            if st.button("獲取談判話術 ➡️", type="primary"):
                st.session_state.result_step = 3
                st.rerun()

    # --- 步驟 3：談判行動 (Action) ---
    elif step == 3:
        st.markdown("### 🛡️ 您的談判劇本")
        st.info("直接複製下方內容，傳送給對方 HR 或法務。")
        
        st.code(st.session_state.negotiation_tips, language="text")
        
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 查看風險"):
                st.session_state.result_step = 2
                st.rerun()
        with c2:
            if st.button("🔄 分析下一份合約", type="secondary"):
                st.session_state.page = 'input'
                st.session_state.contract_content = ""
                st.rerun()

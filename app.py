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

# --- 2. CSS 樣式 ---
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
        position: sticky; top: 0; z-index: 999;
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

    /* 按鈕 */
    .stButton>button {
        border-radius: 8px; font-weight: 600; height: 3rem; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 狀態管理 ---
if 'page' not in st.session_state: st.session_state.page = 'input'
if 'step' not in st.session_state: st.session_state.step = 1 
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = ""
if 'negotiation_tips' not in st.session_state: st.session_state.negotiation_tips = "" 
if 'contract_content' not in st.session_state: st.session_state.contract_content = ""
if 'score_data' not in st.session_state: st.session_state.score_data = {"score": 0, "risk": "未評估", "traps": 0}

# --- 4. 輔助函數 ---
def safe_extract_score(text):
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

# --- 5. 提示詞模板 (防止語法錯誤，移到全域) ---
PROMPT_TEMPLATE = """
你是一位專業律師。請分析以下合約。
【輸出規則】
1. [BLOCK_DATA]分數(0-100),風險等級,陷阱數[/BLOCK_DATA]
2. [BLOCK_REPORT] 請用 Markdown 格式列出 3 個致命風險。使用 Emoji 🔴 ⚠️。
3. [BLOCK_TIPS] 提供談判話術。
合約內容：
{}
"""

# --- 6. 抓取 API Key ---
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

# --- 主程式邏輯 ---
try:
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
                            # 使用 format 填入內容，避免 f-string 多行縮排錯誤
                            final_prompt = PROMPT_TEMPLATE.format(user_input)
                            
                            response = model.generate_content(final_prompt)
                            text = response.text
                            
                            if "[BLOCK_DATA]" in text:
                                data = text.split("[BLOCK_DATA]")[1].split("[/BLOCK_DATA]")[0].split(",")
                                st.session_state.score_data = {
                                    "score": data[0], "risk": data[1].strip(), "traps": data[2]
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
                            st.error(f"分析失敗: {e}")

    # === 頁面 2: 結果 ===
    elif st.session_state.page == 'result':
        current_step = st.session_state.step

        # Step 2: 儀表板
        if current_step == 2:
            raw_score = st.session_state.score_data['score']
            score = safe_extract_score(raw_score)
            traps = safe_extract_int(st.session_state.score_data['traps'])
            risk = st.session_state.score_data['risk']
            
            color = "#ef4444" if score < 60 else "#f59e0b" if score < 80 else "#10b981"
            
            st.markdown(f"""
            <div class="css-card">
                <h3 style="text-align:center;">📊 風險診斷報告</h3>
                <div style="display: flex; justify-content: space-around; margin-top: 20px;">
                    <div style="text-align:center;">
                        <div style="font-size: 3.5rem; color: {color}; font-weight:800;">{score}</div>
                        <div>安全評分</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size: 2.5rem; font-weight:800; line-height: 4.5rem;">{risk}</div>
                        <div>風險等級</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size: 3.5rem; color: #ef4444; font-weight:800;">{traps}</div>
                        <div>致命陷阱</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                if st.button("查看風險細節 ➡️", type="primary"):
                    st.session_state.step = 3
                    st.rerun()

        # Step 3: 詳細分析
        elif current_step == 3:
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            st.markdown("### ⚠️ 深度剖析")
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

        # Step 4: 談判
        elif current_step == 4:
            st.info("💡 這是 AI 為您擬定的談判劇本，請點擊右上角複製。")
            st.code(st.session_state.negotiation_tips, language="markdown")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("⬅️ 查看分析"):
                    st.session_state.step = 3
                    st.rerun()
            with c2:
                if st.button("🔄 分析下一份"):
                    st.session_state.page = 'input'
                    st.session_state.contract_content = ""
                    st.session_state.step = 1
                    st.rerun()

except Exception as e:
    st.error("⚠️ 系統發生錯誤，請檢查 Secrets 設定 (Key 必須加雙引號)")
    with st.expander("錯誤詳情"):
        st.write(e)

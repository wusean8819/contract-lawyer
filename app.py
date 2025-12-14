import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import pypdf
import docx

# --- 1. 全局設定 ---
st.set_page_config(
    page_title="Pocket Lawyer 數位律師 Pro",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS 美化 ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&display=swap');
    .stApp { background-color: #f8f9fa; font-family: 'Noto Sans TC', sans-serif; }
    h1, h2, h3 { color: #0f172a; font-weight: 800 !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    .css-card {
        background-color: white; padding: 2rem; border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 1.5rem;
    }
    
    .metric-box {
        background: white; border-radius: 10px; padding: 20px; text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-top: 4px solid #cbd5e1;
    }
    .metric-number { font-size: 3rem; font-weight: 900; line-height: 1; margin-bottom: 0.5rem; }
    .metric-label { color: #64748b; font-size: 0.875rem; text-transform: uppercase; }
    
    .negotiation-box {
        background-color: #f0f9ff; border-left: 5px solid #0ea5e9;
        padding: 15px; margin-bottom: 15px; border-radius: 0 5px 5px 0;
        font-size: 1.1rem; line-height: 1.8;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 狀態管理 ---
if 'page' not in st.session_state: st.session_state.page = 'input'
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = ""
if 'negotiation_tips' not in st.session_state: st.session_state.negotiation_tips = "" 
if 'contract_content' not in st.session_state: st.session_state.contract_content = ""
if 'score_data' not in st.session_state: st.session_state.score_data = {"score": 0, "risk": "未評估", "traps": 0}

# --- 4. 核心：自動抓取 Secrets ---
api_key = None
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
except:
    pass

# --- 5. 檔案讀取函數 (新功能) ---
def read_file(uploaded_file):
    try:
        text = ""
        if uploaded_file.type == "application/pdf":
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_file)
            text = "\n".join([para.text for para in doc.paragraphs])
        elif uploaded_file.type == "text/plain":
            text = uploaded_file.getvalue().decode("utf-8")
        return text
    except Exception as e:
        return f"讀取錯誤: {str(e)}"

# --- 6. 側邊欄 ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2504/2504814.png", width=60)
    st.markdown("## ⚖️ 數位律師 Pro")
    
    if not api_key:
        st.warning("⚠️ 未偵測到雲端 Key")
        api_key = st.text_input("輸入 API Key (開發者模式)", type="password")
        if api_key: st.success("🟢 開發者金鑰已啟用")
    else:
        st.success("🟢 公共金鑰系統已連線")
        st.caption("訪客模式：支援 PDF/Word/Text")

    st.markdown("---")
    st.info("支援上傳合約檔案，AI 自動辨識文字內容。")

# --- 7. 模型選擇邏輯 ---
def get_best_model(key):
    try:
        genai.configure(api_key=key)
        models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if any('flash-latest' in m for m in models): return next(m for m in models if 'flash-latest' in m)
        if any('1.5-flash' in m for m in models): return next(m for m in models if '1.5-flash' in m)
        return models[0]
    except:
        return "gemini-1.5-flash"

# ==========================================
#  頁面 A：輸入區
# ==========================================
if st.session_state.page == 'input':
    col1, col2, col3 = st.columns([1, 8, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🛡️ Pocket Lawyer 數位合約律師</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b;'>上傳 PDF/Word 或貼上文字，3 秒鐘生成風險報告。</p>", unsafe_allow_html=True)

        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        
        # --- 新增：檔案上傳區 ---
        uploaded_file = st.file_uploader("📂 上傳合約檔案 (支援 PDF, Word, TXT)", type=["pdf", "docx", "txt"])
        
        if uploaded_file is not None:
            # 如果有上傳檔案，自動讀取並填入變數
            file_text = read_file(uploaded_file)
            if len(file_text) > 50:
                st.success(f"✅ 已成功讀取 {uploaded_file.name}，共 {len(file_text)} 字。")
                # 將讀取到的文字預設填入文字框，方便使用者檢查
                if st.session_state.contract_content == "":
                    st.session_state.contract_content = file_text
            else:
                st.warning("⚠️ 檔案內容過短或無法讀取文字（請確認 PDF 不是純圖片掃描檔）")

        user_input = st.text_area("📄 合約內容 (可手動修改)", value=st.session_state.contract_content, height=300, placeholder="文字會自動從檔案讀取，您也可以直接在此貼上...")
        st.markdown('</div>', unsafe_allow_html=True)

        c1, c2 = st.columns([1, 3])
        with c1:
            if st.button("🎲 載入測試範本"):
                st.session_state.contract_content = "第12條：乙方若未滿兩年離職，需賠償6個月薪資。\n第13條：甲方有權隨時調整乙方工作內容及地點，乙方不得異議。"
                st.rerun()
        with c2:
            if st.button("🚀 啟動風險分析", type="primary", use_container_width=True):
                if not api_key:
                    st.error("⚠️ 請先設定 Secrets 或輸入 Key")
                elif not user_input.strip():
                    st.error("⚠️ 內容為空，請上傳檔案或貼上文字")
                else:
                    st.session_state.contract_content = user_input
                    
                    progress = st.empty()
                    with progress.container():
                        st.info("🧠 AI 正在閱卷中...")
                        bar = st.progress(0)
                        for i in range(100):
                            time.sleep(0.01)
                            bar.progress(i+1)
                    
                    try:
                        model_name = get_best_model(api_key)
                        model = genai.GenerativeModel(model_name)
                        
                        prompt = f"""
                        你是一位王牌律師。請分析以下合約。
                        
                        【輸出格式要求】
                        請將回應切分為三個區塊：

                        [BLOCK_DATA]
                        分數,風險等級(高/中/低),陷阱數量
                        [/BLOCK_DATA]

                        [BLOCK_REPORT]
                        (這裡請寫詳細的風險分析報告、總結、紅燈條款，使用 Markdown)
                        [/BLOCK_REPORT]

                        [BLOCK_TIPS]
                        ### 針對第 X 條的談判建議：
                        "您好，關於合約中第 X 條提到的...我們希望能調整為...因為..."
                        (請針對最危險的點，寫出 3 段具體的談判逐字稿)
                        [/BLOCK_TIPS]

                        合約內容：
                        {user_input}
                        """
                        
                        safety = {HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE, HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE}
                        response = model.generate_content(prompt, safety_settings=safety)
                        text = response.text
                        
                        if "[BLOCK_DATA]" in text:
                            st.session_state.score_data = {
                                "score": text.split("[BLOCK_DATA]")[1].split(",")[0].strip(),
                                "risk": text.split(",")[1].strip(),
                                "traps": text.split(",")[2].split("[/BLOCK_DATA]")[0].strip()
                            }
                        
                        if "[BLOCK_REPORT]" in text:
                            st.session_state.analysis_result = text.split("[BLOCK_REPORT]")[1].split("[/BLOCK_REPORT]")[0].strip()
                        else:
                            st.session_state.analysis_result = text

                        if "[BLOCK_TIPS]" in text:
                            st.session_state.negotiation_tips = text.split("[BLOCK_TIPS]")[1].split("[/BLOCK_TIPS]")[0].strip()
                        else:
                            st.session_state.negotiation_tips = "AI 未能生成特定話術，請參考總結報告。"

                        st.session_state.page = 'result'
                        st.rerun()
                            
                    except Exception as e:
                        progress.empty()
                        st.error(f"連線錯誤：{e}")

# ==========================================
#  頁面 B：結果區
# ==========================================
elif st.session_state.page == 'result':
    if st.button("⬅️ 分析下一份"):
        st.session_state.page = 'input'
        # 清空上傳的檔案內容，以免混淆
        st.session_state.contract_content = ""
        st.rerun()
        
    s_val = st.session_state.score_data['score']
    r_val = st.session_state.score_data['risk']
    t_val = st.session_state.score_data['traps']
    
    try:
        color = "#ef4444" if int(s_val) < 60 else "#f59e0b" if int(s_val) < 80 else "#10b981"
    except: color = "#64748b"

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-box" style="border-top-color:{color}"><div class="metric-number" style="color:{color}">{s_val}</div><div class="metric-label">安全評分</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-box" style="border-top-color:{color}"><div class="metric-number">{r_val}</div><div class="metric-label">風險等級</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-box" style="border-top-color:#ef4444"><div class="metric-number" style="color:#ef4444">{t_val}</div><div class="metric-label">致命陷阱</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📑 分析報告", "🛡️ 談判話術 (AI 擬定)", "📝 原始條文"])
    
    with tab1:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.markdown(st.session_state.analysis_result)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with tab2:
        st.info("💡 這是 AI 律師為您擬定的談判劇本，您可以直接複製傳給對方。")
        st.markdown(f"""
        <div class="css-card">
            <div class="negotiation-box">
                {st.session_state.negotiation_tips}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tab3:
        st.text_area("原始合約", value=st.session_state.contract_content, height=400, disabled=True)

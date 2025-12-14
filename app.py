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

# --- 2. CSS 樣式 (維持最簡潔與 UX 優化版) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
    :root { --primary: #2563eb; --success: #10b981; --bg: #f8fafc; --card: #ffffff; }
    .stApp { background-color: var(--bg); font-family: 'Noto Sans TC', sans-serif; }
    
    #MainMenu, footer, header {visibility: hidden;}
    
    .css-card { 
        background: var(--card); 
        padding: 2rem; 
        border-radius: 12px; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); 
        border: 1px solid #e2e8f0; 
        margin-bottom: 20px; 
    }
    
    .stButton>button { border-radius: 8px; font-weight: 600; height: 3rem; width: 100%; }
    
    /* Tabs 優化 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; border-radius: 8px 8px 0 0; }
</style>
""", unsafe_allow_html=True)

# --- 3. 狀態管理 ---
if 'page' not in st.session_state: st.session_state.page = 'input'
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = ""
if 'negotiation_tips' not in st.session_state: st.session_state.negotiation_tips = "" 
if 'contract_content' not in st.session_state: st.session_state.contract_content = ""
if 'score_data' not in st.session_state: st.session_state.score_data = {"score": 0, "risk": "未評估", "traps": 0}
if 'current_model_name' not in st.session_state: st.session_state.current_model_name = "Auto"

# --- 4. 輔助函數 ---
def safe_extract_score(text):
    try:
        text_str = str(text).strip()
        fraction_match = re.search(r'(\d+)\s*/\s*(\d+)', text_str)
        if fraction_match:
            num, den = float(fraction_match.group(1)), float(fraction_match.group(2))
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

def generate_with_retry(model, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return model.generate_content(prompt)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Quota exceeded" in error_str:
                wait_time = 60 
                timer_text = st.empty()
                bar = st.progress(0)
                for i in range(wait_time):
                    left = wait_time - i
                    timer_text.warning(f"🔥 觸發流量限制，系統冷卻中... 剩餘 {left} 秒 (第 {attempt+1}/{max_retries} 次重試)")
                    bar.progress((i+1)/wait_time)
                    time.sleep(1)
                timer_text.empty()
                bar.empty()
                continue 
            else:
                raise e
    raise Exception("重試次數過多，請稍後再試。")

# ★★★ 關鍵修復：自動偵測並選用最佳模型 ★★★
def get_best_model(api_key):
    genai.configure(api_key=api_key)
    
    target_model = None
    available_models = []
    
    try:
        # 1. 獲取所有可用模型
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # 2. 定義優先順序 (Flash 快 -> Pro 強 -> 1.0 舊版)
        preferences = [
            "gemini-1.5-flash", # 首選：快速便宜
            "gemini-1.5-pro",   # 次選：強大
            "gemini-1.0-pro",   # 備選
            "gemini-pro"        # 最後手段
        ]
        
        # 3. 匹配模型
        for pref in preferences:
            for model_name in available_models:
                if pref in model_name:
                    target_model = model_name
                    break
            if target_model: break
            
        # 4. 如果都沒找到，使用列表中的第一個，或者強制預設
        if not target_model:
            if available_models:
                target_model = available_models[0]
            else:
                target_model = "gemini-1.5-flash" # 強制預設，雖然可能失敗
                
        st.session_state.current_model_name = target_model # 記錄下來給 UI 顯示
        return genai.GenerativeModel(target_model)
        
    except Exception as e:
        # 如果連 list_models 都失敗 (例如 key 錯誤)，直接回傳預設物件讓後面報錯
        return genai.GenerativeModel("gemini-1.5-flash")

# --- 5. 設定區與 Key ---
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
    if st.button("🔄 重置 / 分析新合約"):
        st.session_state.clear()
        st.rerun()

# --- 主程式邏輯 ---
try:
    # === 頁面 1: 輸入 ===
    if st.session_state.page == 'input':
        st.markdown("<h1 style='text-align: center; color: #1e293b; margin-bottom: 0.5rem;'>Pocket Lawyer 數位律師</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 2rem;'>拖放合約，AI 立即為您偵測法律陷阱。</p>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 6, 1])
        with col2:
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            uploaded_file = st.file_uploader("📂 上傳檔案 (PDF / Word / TXT)", type=["pdf", "docx", "txt"])
            
            if uploaded_file:
                text = read_file(uploaded_file)
                if len(text) > 10:
                    st.session_state.contract_content = text
                    st.success(f"✅ 已讀取：{uploaded_file.name}")
            
            user_input = st.text_area("或直接貼上條款內容：", value=st.session_state.contract_content, height=200)
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("🚀 開始分析", type="primary"):
                st.session_state.contract_content = user_input
                if not user_input.strip() and not api_key:
                    st.error("⚠️ 請確認 API Key 已設定且內容不為空")
                else:
                    with st.spinner("🔍 正在尋找最佳模型並閱卷中..."):
                        try:
                            # ★★★ 呼叫新的自動選模函數 ★★★
                            model = get_best_model(api_key)
                            
                            prompt = f"""
                            你是一位專業律師。請分析以下合約。
                            【輸出規則】
                            1. [BLOCK_DATA]分數(0-100),風險等級,陷阱數[/BLOCK_DATA]
                            2. [BLOCK_REPORT] 請用 Markdown 格式列出 3 個致命風險。使用 Emoji 🔴 ⚠️。
                            3. [BLOCK_TIPS] 提供談判話術。
                            合約內容：
                            {user_input}
                            """
                            response = generate_with_retry(model, prompt)
                            text = response.text
                            
                            # 解析回傳資料
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
                            st.rerun()
                        except Exception as e:
                            st.error(f"分析失敗: {e}")

    # === 頁面 2: 結果儀表板 ===
    elif st.session_state.page == 'result':
        
        # 顯示使用的模型 (放在右上角或不明顯處，增加信任感)
        st.toast(f"🤖 使用模型：{st.session_state.current_model_name}", icon="⚡")

        # 1. 頂部儀表板
        raw_score = st.session_state.score_data['score']
        score = safe_extract_score(raw_score)
        traps = safe_extract_int(st.session_state.score_data['traps'])
        risk = st.session_state.score_data['risk']
        color = "#ef4444" if score < 60 else "#f59e0b" if score < 80 else "#10b981"
        
        st.markdown(f"""
        <div class="css-card">
            <h3 style="text-align:center; margin-bottom: 1.5rem;">📊 風險診斷報告</h3>
            <div style="display: flex; justify-content: space-around; align-items: center;">
                <div style="text-align:center;">
                    <div style="font-size: 3.5rem; color: {color}; font-weight:800; line-height: 1;">{score}</div>
                    <div style="color: #64748b; font-weight: 500;">安全評分</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size: 2rem; font-weight:800; color: #334155; margin-bottom: 5px;">{risk}</div>
                    <div style="background: {color}; color: white; padding: 2px 12px; border-radius: 20px; font-size: 0.8rem;">風險等級</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size: 3.5rem; color: #ef4444; font-weight:800; line-height: 1;">{traps}</div>
                    <div style="color: #64748b; font-weight: 500;">致命陷阱</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 2. 分頁內容區 (Tabs)
        tab1, tab2, tab3 = st.tabs(["⚠️ 風險深度分析", "🗣️ 談判策略劇本", "📄 原始合約內容"])

        with tab1:
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            st.markdown(st.session_state.analysis_result)
            st.markdown('</div>', unsafe_allow_html=True)

        with tab2:
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            st.info("💡 這是 AI 為您擬定的談判劇本，可直接複製使用。")
            st.code(st.session_state.negotiation_tips, language="markdown")
            st.markdown('</div>', unsafe_allow_html=True)

        with tab3:
            st.text_area("合約全文", value=st.session_state.contract_content, height=400, disabled=True)
            
        # 3. 底部按鈕
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            if st.button("🔄 分析下一份合約", type="primary"):
                st.session_state.page = 'input'
                st.session_state.contract_content = ""
                st.session_state.score_data = {"score": 0, "risk": "未評估", "traps": 0}
                st.rerun()

except Exception as e:
    st.error("⚠️ 系統發生預期外的錯誤，請檢查 Secrets 設定。")
    with st.expander("錯誤詳情"): st.write(e)

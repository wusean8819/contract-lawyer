import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time

# --- 1. 全局設定 ---
st.set_page_config(
    page_title="Pro 數位合約律師",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 專業 CSS 優化 (美化分頁與卡片) ---
st.markdown("""
<style>
    .stApp { font-family: "Microsoft JhengHei", sans-serif; }
    
    /* 隱藏預設的選單與 footer，讓畫面更乾淨 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 美化分數卡片 */
    .score-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border-left: 5px solid #4a5568;
        margin-bottom: 20px;
    }
    .score-title { font-size: 18px; color: #555; }
    .score-value { font-size: 42px; font-weight: bold; color: #2c3e50; }
    
    /* 美化 Tabs 分頁 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #fff;
        border-radius: 5px 5px 0 0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #eef2ff;
        border-bottom: 2px solid #4f46e5;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 狀態管理 (Session State) ---
# 這是實現「換頁」的關鍵
if 'page' not in st.session_state:
    st.session_state.page = 'input'  # 預設在輸入頁
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = "" # 儲存分析結果

# --- 4. 側邊欄與自動導航 ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2504/2504814.png", width=70)
    st.title("⚖️ 數位律師事務所")
    st.markdown("---")
    
    api_key = st.text_input("輸入 Google API Key", type="password")
    
    # 自動抓模型邏輯
    target_model_name = "尚未連線"
    if api_key:
        try:
            genai.configure(api_key=api_key)
            available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # 優先順序：flash-latest -> 1.5-flash -> 2.0-flash
            if any('flash-latest' in m for m in available_models):
                target_model_name = next(m for m in available_models if 'flash-latest' in m)
            elif any('1.5-flash' in m for m in available_models):
                target_model_name = next(m for m in available_models if '1.5-flash' in m)
            elif any('2.0-flash' in m for m in available_models):
                target_model_name = next(m for m in available_models if '2.0-flash' in m)
            else:
                target_model_name = available_models[0]
            
            st.success(f"✅ 連線成功：{target_model_name}")
        except:
            st.error("連線失敗，請檢查 Key")
            target_model_name = "gemini-1.5-flash"

    st.markdown("---")
    # 如果已經在結果頁，顯示「分析新合約」按鈕
    if st.session_state.page == 'result':
        if st.button("⬅️ 分析下一份合約", use_container_width=True):
            st.session_state.page = 'input'
            st.session_state.analysis_result = ""
            st.rerun()

# --- 5. 頁面邏輯切換 ---

# === 頁面 A：輸入介面 ===
if st.session_state.page == 'input':
    st.title("🛡️ 24H 數位合約風險分析儀")
    st.markdown("#### 請輸入合約內容，AI 將為您切換至專業分析視圖。")
    
    with st.container():
        contract_content = st.text_area(
            "📄 合約條款貼上區：", 
            height=300, 
            placeholder="請直接貼上整份合約或有疑慮的條款..."
        )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        start_btn = st.button("🚀 啟動深度審查 (進入分析頁)", use_container_width=True, type="primary")

    if start_btn:
        if not api_key:
            st.warning("⚠️ 請先在左側輸入 API Key")
        elif not contract_content.strip():
            st.warning("⚠️ 請貼上合約內容")
        else:
            # 轉場動畫
            with st.spinner("⚖️ 正在切換至分析室...AI 律師閱卷中..."):
                try:
                    # 設定模型
                    model = genai.GenerativeModel(target_model_name)
                    
                    # 提示詞 (要求詳細 Markdown)
                    prompt = f"""
                    你是一位專業律師。請分析以下合約。
                    請務必使用 Markdown 格式，並包含以下章節：
                    
                    # 📊 風險總覽
                    (請在這裡畫一個表格，包含：合約安全分(0-100)、風險燈號(紅/黃/綠)、致命陷阱數量)

                    # ⚖️ 深度風險分析
                    (請列出 3-5 點關鍵風險，每點都要有【風險說明】與【嚴重程度】)
                    
                    # 🛡️ 具體修改建議
                    (針對上述風險，提供白話文的修改建議或談判話術)

                    # 💡 隱藏陷阱與盲點
                    (合約沒寫但應該要注意的事情)

                    ---
                    合約內容：
                    {contract_content}
                    """
                    
                    # 執行分析
                    safety_settings = {
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                    
                    response = model.generate_content(prompt, safety_settings=safety_settings)
                    
                    # 儲存結果並切換頁面
                    st.session_state.analysis_result = response.text
                    st.session_state.page = 'result' # 切換狀態
                    st.rerun() # 強制重整畫面以進入新頁面
                    
                except Exception as e:
                    st.error(f"分析發生錯誤：{e}")

# === 頁面 B：分析報告介面 (全螢幕呈現) ===
elif st.session_state.page == 'result':
    st.title("📊 合約健檢報告書")
    
    # 建立分頁籤 (這是你要的下一頁、下一頁的感覺)
    tab1, tab2, tab3, tab4 = st.tabs(["🚦 總覽與評分", "⚖️ 深度分析", "🛡️ 修改建議", "📝 原始條文"])
    
    # 解析 AI 回傳的 Markdown 內容 (簡單切割)
    full_text = st.session_state.analysis_result
    
    # 為了方便顯示，我們直接顯示完整內容，但你可以教使用者點擊 Tab 查看不同角度
    # 這裡我們用比較聰明的方式：在 Tab 1 顯示重點，Tab 2 顯示全文
    
    with tab1:
        st.markdown("### 🎯 核心風險評估")
        st.info("💡 提示：請點擊上方分頁標籤查看詳細分析與建議。")
        # 這裡顯示 AI 的前段結果 (通常是總覽)
        if "# ⚖️ 深度風險分析" in full_text:
            summary_part = full_text.split("# ⚖️ 深度風險分析")[0]
            st.markdown(summary_part)
        else:
            st.markdown(full_text)

    with tab2:
        st.markdown("### ⚠️ 關鍵條款審查")
        # 嘗試擷取中間段落
        if "# ⚖️ 深度風險分析" in full_text and "# 🛡️ 具體修改建議" in full_text:
            risk_part = full_text.split("# ⚖️ 深度風險分析")[1].split("# 🛡️ 具體修改建議")[0]
            st.markdown(risk_part)
        else:
            st.markdown("請參考總覽頁面。")
            
    with tab3:
        st.markdown("### 🛡️ 律師修改建議")
        if "# 🛡️ 具體修改建議" in full_text:
            suggestion_part = full_text.split("# 🛡️ 具體修改建議")[1]
            st.markdown(suggestion_part)
        else:
            st.markdown("請參考總覽頁面。")

    with tab4:
        st.markdown("### 📄 原始合約內容")
        st.text_area("您輸入的內容", value=contract_content, height=400, disabled=True)
    
    st.divider()
    col_back, col_print = st.columns([1, 4])
    with col_back:
        if st.button("⬅️ 重新分析"):
            st.session_state.page = 'input'
            st.session_state.analysis_result = ""
            st.rerun()

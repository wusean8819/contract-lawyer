import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- 1. 頁面設定 (開啟寬螢幕模式) ---
st.set_page_config(
    page_title="Pro 數位合約律師",
    page_icon="⚖️",
    layout="wide"  # <--- 關鍵！這會讓畫面變寬，看起來像專業後台
)

# --- 2. 注入專業 CSS (美化字體與卡片效果) ---
st.markdown("""
<style>
    /* 全站字體優化 */
    .stApp {
        font-family: "Microsoft JhengHei", "PingFang TC", sans-serif;
    }
    /* 標題樣式 */
    h1 {
        color: #2c3e50;
        font-weight: 700;
    }
    /* 讓分析報告的表格變漂亮 */
    table {
        width: 100%;
        border-collapse: collapse;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
    }
    th {
        background-color: #4a5568;
        color: white;
        padding: 12px;
    }
    td {
        padding: 10px;
        border-bottom: 1px solid #ddd;
    }
    /* 強調關鍵字的螢光筆效果 */
    .highlight {
        background-color: #fff3cd;
        padding: 2px 5px;
        border-radius: 4px;
        font-weight: bold;
        color: #856404;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 側邊欄設定 ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2504/2504814.png", width=80)
    st.title("⚖️ 數位律師事務所")
    st.markdown("---")
    
    st.markdown("### 🔑 身份驗證")
    api_key = st.text_input("輸入 Google API Key", type="password", help="請輸入您的 Gemini API Key")
    
    st.markdown("### ⚙️ 系統狀態")
    st.caption("🟢 核心模型：Gemini 1.5 Flash")
    st.caption("⚡ 連線通道：穩定版 (Stable)")
    st.caption("🛡️ 安全過濾：已解除 (Law Mode)")
    
    st.markdown("---")
    st.info("💡 提示：越完整的合約內容，評分越準確。")

# --- 4. 主畫面 ---
st.title("🛡️ 24H 數位合約風險分析儀")
st.markdown("#### 讓 AI 為您的合約進行「健康檢查」，3 秒鐘抓出隱藏陷阱。")

if not api_key:
    st.warning("⬅️ 請先在左側側邊欄輸入 API Key 才能開始服務。")
else:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash') # 使用最穩定的模型

        # 輸入區塊美化
        with st.container():
            st.markdown("### 📄 案件受理")
            contract_content = st.text_area(
                "請將合約條款貼在下方：", 
                height=250, 
                placeholder="例如：\n第 12 條：若乙方欲終止合約，需賠償甲方 100 萬元懲罰性違約金..."
            )

        # 按鈕區
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            analyze_btn = st.button("🚀 啟動深度風險分析", use_container_width=True, type="primary")

        if analyze_btn and contract_content.strip():
            st.divider()
            
            # --- 5. 顯示分析中的動畫 ---
            with st.status("🔍 律師正在閱卷中...", expanded=True) as status:
                st.write("正在掃描關鍵字...")
                st.write("正在比對法律條文...")
                st.write("正在計算風險分數...")
                
                # --- 6. 專業提示詞 (Prompt Engineering) ---
                # 這裡教 AI 如何畫出漂亮的表格和分數
                prompt = f"""
                你是一位經驗豐富的台灣律師，現在要出一份「合約風險評估報告」。
                請嚴格依照以下 Markdown 格式輸出，不要輸出任何 JSON，直接輸出美化後的文字：

                # 📊 合約健康度診斷書

                | 評分項目 | 分析結果 |
                | :--- | :--- |
                | **🏆 合約安全分** | **[請根據風險給出 0-100 分] 分** (分數越低越危險) |
                | **🚦 風險燈號** | [請選一個：🔴高風險 / 🟡中風險 / 🟢低風險] |
                | **💣 致命陷阱數** | 共發現 **[數字]** 個高風險條款 |

                ---

                ## 🚦 整體風險評估 (Executive Summary)
                [請用一句話總結這份合約是對誰比較有利，例如：這份合約嚴重偏向甲方，充滿了單方免責條款。]

                ---

                ## ⚠️ 紅燈條款 (致命風險 - 建議拒簽或修改)
                > 請找出最危險的 3 個條款，用引言格式強調。
                
                **1. [條款名稱或摘要]**
                * **🔴 為什麼危險：** [解釋]
                * **🛡️ 律師建議：** [具體修改文字]

                **2. [條款名稱或摘要]**
                * **🔴 為什麼危險：** [解釋]
                * **🛡️ 律師建議：** [具體修改文字]

                ---

                ## 💡 隱藏陷阱 (魔鬼藏在細節裡)
                * [列出合約沒寫但應該要有的權益，例如：缺漏的終止權、不明確的驗收標準]

                ---
                
                ## ⚖️ 逐條詳細審查
                [請針對使用者提供的內容進行逐條分析]

                合約內容如下：
                {contract_content}
                """

                # 關閉安全過濾，確保法律用語不被擋
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                # 呼叫 AI (使用流式傳輸)
                result_container = st.empty()
                full_text = ""
                
                try:
                    response = model.generate_content(
                        prompt, 
                        stream=True, 
                        safety_settings=safety_settings
                    )
                    
                    for chunk in response:
                        if chunk.text:
                            full_text += chunk.text
                            result_container.markdown(full_text + "▌")
                    
                    # 分析完成
                    result_container.markdown(full_text)
                    status.update(label="✅ 分析完成！", state="complete", expanded=False)

                except Exception as e:
                    st.error(f"分析中斷：{e}")

        elif analyze_btn:
            st.warning("⚠️ 請先貼上合約內容喔！")

    except Exception as e:
        st.error(f"連線設定錯誤：{e}")

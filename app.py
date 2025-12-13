import streamlit as st
import google.generativeai as genai

st.title("🔧 雲端主機檢測工具")
st.write("這是一個測試工具，用來查看雲端主機到底認識哪些模型。")

# 讓使用者輸入 Key
api_key = st.text_input("請輸入 API Key", type="password")

if st.button("開始檢測"):
    if not api_key:
        st.warning("請先輸入 Key")
    else:
        try:
            genai.configure(api_key=api_key)
            st.info("正在連線詢問 Google...")
            
            # 這是關鍵：列出所有可用模型
            models = genai.list_models()
            
            st.success("✅ 連線成功！這台主機目前支援以下模型名字：")
            found_models = []
            for m in models:
                # 只顯示能生成文字的模型
                if 'generateContent' in m.supported_generation_methods:
                    st.code(f"model = genai.GenerativeModel('{m.name.replace('models/', '')}')")
                    found_models.append(m.name)
            
            if not found_models:
                st.error("連線通了，但清單是空的。這代表 API Key 可能權限不足或專案設定有誤。")
                
        except Exception as e:
            st.error(f"❌ 連線失敗，錯誤原因：\n{e}")

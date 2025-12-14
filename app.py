import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import pypdf
import docx
import re # 用來強制抓取數字的工具

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
if 'negotiation_tips' not

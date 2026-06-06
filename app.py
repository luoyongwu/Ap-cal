
import streamlit as st
from anthropic import Anthropic

MODEL_NAME = "claude-sonnet-4-20250514"
st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide")

# 1. 配置与状态初始化
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "messages" not in st.session_state: st.session_state.messages = []
if "curr_concept" not in st.session_state: st.session_state.curr_concept = "3.1 链式法则"
if "mastery_scores" not in st.session_state: st.session_state.mastery_scores = {}
if "mastery_ready" not in st.session_state: st.session_state.mastery_ready = False
if "last_summary" not in st.session_state: st.session_state.last_summary = ""

# 2. UI: 侧边栏配置页 (点击“》”进入)
with st.sidebar:
    st.title("⚙️ 配置页")
    st.session_state.api_key = st.text_input("🔑 Claude API Key", type="password")
    
    units = ["Unit 1: 极限", "Unit 3: 求导法则"]
    selected_unit = st.selectbox("选择 Unit", units)
    
    concepts = ["3.1 链式法则", "3.2 隐函数求导", "3.4 反函数求导"]
    st.session_state.curr_concept = st.selectbox("选择 Concept", concepts)
    
    if st.button("✅ 确认配置"):
        st.success(f"已锁定: {selected_unit} - {st.session_state.curr_concept}")

# 3. 核心逻辑: 保持您熟悉的测试框和状态处理
st.title("🎓 Luo-cal AP Calculus")

def get_ai_response(prompt):
    if not st.session_state.api_key: return "请先在配置页输入 API Key。"
    client = Anthropic(api_key=st.session_state.api_key)
    # ... (保持您的翻译网关和状态拦截逻辑) ...
    return "导师反馈: [STATUS: GUIDING] (模拟)"

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("输入测试题/回答..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    response = get_ai_response(prompt)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

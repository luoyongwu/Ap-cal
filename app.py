
import streamlit as st
from anthropic import Anthropic

MODEL_NAME = "claude-sonnet-4-6"

st.set_page_config(page_title="Luo-cal 最终稳定版", layout="wide")

# --- 状态初始化 ---
if "messages" not in st.session_state: st.session_state.messages = []
if "ENV_CLAUDE_KEY" not in st.session_state: st.session_state.ENV_CLAUDE_KEY = ""
if "curr_unit" not in st.session_state: st.session_state.curr_unit = "Unit 1: Limits & Continuity"
if "curr_lang" not in st.session_state: st.session_state.curr_lang = "Chinese"

CONTENT_MATRIX = {
    "Unit 1: Limits & Continuity": ["1.1 Limits Intro", "1.2 Asymptotes", "1.3 Continuity", "1.4 Squeeze Theorem", "1.5 Intermediate Value Theorem"],
    "Unit 2: Derivatives": ["2.1 Derivative Definition", "2.2 Power/Product Rules", "2.3 Chain Rule", "2.4 Higher-Order"]
}

# --- 侧边栏 ---
st.sidebar.title("🎓 Luo-cal 教学控制台")
key_input = st.sidebar.text_input("🔑 API Key:", type="password", placeholder="sk-ant-api03-...")
if key_input.strip(): st.session_state.ENV_CLAUDE_KEY = key_input.strip()

if st.session_state.ENV_CLAUDE_KEY:
    st.sidebar.success("🟢 密钥已激活")
else:
    st.sidebar.warning("🔴 请输入 API Key")

selected_unit = st.sidebar.selectbox("📂 选择 Unit:", list(CONTENT_MATRIX.keys()))
concept = st.sidebar.selectbox("🎯 选择 Concept:", CONTENT_MATRIX[selected_unit])
lang = st.sidebar.radio("🌐 语言:", ["Chinese", "English"])

# ✅ 罗老师核心修复：Unit 切换 或 语言切换，统一清空历史，触发新语言/新 Unit 首题自启
if selected_unit != st.session_state.curr_unit or lang != st.session_state.curr_lang:
    st.session_state.curr_unit = selected_unit
    st.session_state.curr_lang = lang
    st.session_state.messages = []
    st.rerun()

st.title(f"{selected_unit} - {concept}")

# --- 核心引擎 ---
def get_ai_response():
    if not st.session_state.ENV_CLAUDE_KEY:
        st.warning("⚠️ 请先在左侧输入 API Key")
        st.stop()
        
    client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
    # ✅ 修正点2：显式强制指令，防止大模型发生语言混淆
    system_msg = f"You are an AP Calculus tutor. Respond entirely in {'Chinese (简体中文)' if st.session_state.curr_lang == 'Chinese' else 'English'}. Rules: Use LaTeX for all math expressions. Use Socratic method: guide the student with hints and questions, never give away the full answer directly. Ask only one question at a time."
    
    with st.spinner("⏳ 正在思考..."):
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1500,
            system=system_msg,
            messages=st.session_state.messages
        )
    return response.content[0].text

# --- 逻辑流 ---
# 1. 首题自动加载
if not st.session_state.messages:
    # ✅ 修正点3：首题 Prompt 动态进行中英文对齐
    first_prompt = f"请针对 {concept} 给出第一道 AP 风格习题。" if st.session_state.curr_lang == "Chinese" else f"Please give me the first AP-style problem for {concept}."
    st.session_state.messages.append({"role": "user", "content": first_prompt})
    res = get_ai_response()
    if res:
        st.session_state.messages.append({"role": "assistant", "content": res})
        st.rerun()

# 2. 渲染历史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 3. 输入处理
placeholder_text = "请输入你的解答或问题..." if st.session_state.curr_lang == "Chinese" else "Enter your answer or question..."
if prompt := st.chat_input(placeholder_text):
    st.session_state.messages.append({"role": "user", "content": prompt})
    res = get_ai_response()
    if res:
        st.session_state.messages.append({"role": "assistant", "content": res})
        st.rerun()

# 4. 下一题按钮
# ✅ 修正点4：按钮标签文本动态切换
btn_label = "▶️ 下一题" if st.session_state.curr_lang == "Chinese" else "▶️ Next Problem"
if st.button(btn_label):
    next_prompt = f"请针对 {concept} 继续出下一道 AP 难度习题。" if st.session_state.curr_lang == "Chinese" else f"Please give me the next AP-level problem for {concept}."
    st.session_state.messages.append({"role": "user", "content": next_prompt})
    res = get_ai_response()
    if res:
        st.session_state.messages.append({"role": "assistant", "content": res})
        st.rerun()

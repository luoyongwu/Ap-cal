
import streamlit as st
from anthropic import Anthropic

MODEL_NAME = "claude-sonnet-4-6"

st.set_page_config(page_title="Luo-cal 最终稳定版", layout="wide")

if "messages" not in st.session_state: st.session_state.messages = []
if "ENV_CLAUDE_KEY" not in st.session_state: st.session_state.ENV_CLAUDE_KEY = ""
if "curr_unit" not in st.session_state: st.session_state.curr_unit = "Unit 1: Limits & Continuity"

CONTENT_MATRIX = {
    "Unit 1: Limits & Continuity": ["1.1 Limits Intro", "1.2 Asymptotes", "1.3 Continuity", "1.4 Squeeze Theorem", "1.5 Intermediate Value Theorem"],
    "Unit 2: Derivatives": ["2.1 Derivative Definition", "2.2 Power/Product Rules", "2.3 Chain Rule", "2.4 Higher-Order"]
}

st.sidebar.title("🎓 Luo-cal 教学控制台")
key_input = st.sidebar.text_input("🔑 API Key:", type="password", placeholder="sk-ant-api03-...")
if key_input.strip():
    st.session_state.ENV_CLAUDE_KEY = key_input.strip()

if st.session_state.ENV_CLAUDE_KEY:
    masked = st.session_state.ENV_CLAUDE_KEY[:8] + "..." + st.session_state.ENV_CLAUDE_KEY[-4:]
    st.sidebar.success(f"🟢 密钥已激活 `{masked}`")
else:
    st.sidebar.warning("🔴 请输入 API Key")

selected_unit = st.sidebar.selectbox("📂 选择 Unit:", list(CONTENT_MATRIX.keys()))
concept = st.sidebar.selectbox("🎯 选择 Concept:", CONTENT_MATRIX[selected_unit])
lang = st.sidebar.radio("🌐 语言:", ["Chinese", "English"])

if selected_unit != st.session_state.curr_unit:
    st.session_state.curr_unit = selected_unit
    st.session_state.messages = []
    st.rerun()

st.title(f"{selected_unit} - {concept}")

def get_ai_response():
    if not st.session_state.ENV_CLAUDE_KEY:
        st.warning("⚠️ 请先在左侧输入 API Key")
        st.stop()
    client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=1500,
        system=f"You are a tutor. Topic: {concept}. Language: {lang}. Rules: Use LaTeX, never give direct answers, use Socratic method.",
        messages=st.session_state.messages
    )
    return response.content[0].text

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("请输入问题..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    res = get_ai_response()
    st.session_state.messages.append({"role": "assistant", "content": res})
    st.rerun()

if st.button("▶️ 下一题 (Next Challenge)"):
    prompt = f"请针对 {concept} 出一道难度契合 AP 考试风格的习题。"
    st.session_state.messages.append({"role": "user", "content": prompt})
    res = get_ai_response()
    st.session_state.messages.append({"role": "assistant", "content": res})
    st.rerun()


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

# 修复：Unit 切换清空历史，语言切换仅触发刷新
if selected_unit != st.session_state.curr_unit:
    st.session_state.curr_unit = selected_unit
    st.session_state.messages = []
    st.rerun()

if lang != st.session_state.curr_lang:
    st.session_state.curr_lang = lang
    st.rerun()

st.title(f"{selected_unit} - {concept}")

# --- 核心引擎 ---
def get_ai_response():
    if not st.session_state.ENV_CLAUDE_KEY:
        st.warning("⚠️ 请先在左侧输入 API Key")
        st.stop()
        
    client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
    system_msg = f"You are an AP tutor. Language: {st.session_state.curr_lang}. Rules: Use LaTeX. Socratic method (guide, don't answer). Ask one question at a time."
    
    with st.spinner("⏳ 正在思考并翻译..."):
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
    first_prompt = f"请针对 {concept} 给出第一道 AP 风格习题。"
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
if prompt := st.chat_input("请输入问题或上传解析..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    res = get_ai_response()
    if res:
        st.session_state.messages.append({"role": "assistant", "content": res})
        st.rerun()

# 4. 按钮处理
if st.button("▶️ 刷新/下一题"):
    prompt = f"请针对 {concept} 继续出下一道 AP 难度习题。"
    st.session_state.messages.append({"role": "user", "content": prompt})
    res = get_ai_response()
    if res:
        st.session_state.messages.append({"role": "assistant", "content": res})
        st.rerun()

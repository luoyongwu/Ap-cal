import streamlit as st
from anthropic import Anthropic

MODEL_NAME = "claude-sonnet-4-6"
st.set_page_config(page_title="Luo-cal 最终稳定版", layout="wide")

if "messages" not in st.session_state: st.session_state.messages = []
if "ENV_CLAUDE_KEY" not in st.session_state: st.session_state.ENV_CLAUDE_KEY = ""

# --- 初始状态对齐 ---
if "curr_lang" not in st.session_state: st.session_state.curr_lang = "Chinese"
if "curr_unit" not in st.session_state: st.session_state.curr_unit = "第一单元: 极限与连续"

BILINGUAL_MATRIX = {
    "Chinese": {
        "Units": {"第一单元: 极限与连续": ["1.1 极限简介", "1.2 渐近线", "1.3 连续性", "1.4 夹逼定理", "1.5 介值定理"],
                  "第二单元: 导数": ["2.1 导数定义", "2.2 幂/乘积法则", "2.3 链式法则", "2.4 高阶导数"]}
    },
    "English": {
        "Units": {"Unit 1: Limits & Continuity": ["1.1 Limits Intro", "1.2 Asymptotes", "1.3 Continuity", "1.4 Squeeze Theorem", "1.5 Intermediate Value Theorem"],
                  "Unit 2: Derivatives": ["2.1 Derivative Definition", "2.2 Power/Product Rules", "2.3 Chain Rule", "2.4 Higher-Order"]}
    }
}

st.sidebar.title("🎓 Luo-cal 教学控制台")
key_input = st.sidebar.text_input("🔑 API Key:", type="password", value=st.session_state.ENV_CLAUDE_KEY, placeholder="sk-ant-api03-...")
if key_input.strip(): st.session_state.ENV_CLAUDE_KEY = key_input.strip()

if st.session_state.ENV_CLAUDE_KEY: st.sidebar.success("🟢 密钥已激活")
else: st.sidebar.warning("🔴 请输入 API Key")

lang = st.sidebar.radio("🌐 语言:", ["Chinese", "English"], index=["Chinese", "English"].index(st.session_state.curr_lang))

if lang != st.session_state.curr_lang:
    old_units = list(BILINGUAL_MATRIX[st.session_state.curr_lang]["Units"].keys())
    new_units = list(BILINGUAL_MATRIX[lang]["Units"].keys())
    try:
        idx = old_units.index(st.session_state.curr_unit)
        st.session_state.curr_unit = new_units[idx]
    except:
        st.session_state.curr_unit = new_units[0]
    st.session_state.curr_lang = lang
    st.session_state.messages = []
    st.rerun()

units_map = BILINGUAL_MATRIX[st.session_state.curr_lang]["Units"]
selected_unit = st.sidebar.selectbox("📂 选择 Unit:", list(units_map.keys()), index=list(units_map.keys()).index(st.session_state.curr_unit))
concept = st.sidebar.selectbox("🎯 选择 Concept:", units_map[selected_unit])

if selected_unit != st.session_state.curr_unit:
    st.session_state.curr_unit = selected_unit
    st.session_state.messages = []
    st.rerun()

st.title(f"{selected_unit} - {concept}")

def get_ai_response():
    if not st.session_state.ENV_CLAUDE_KEY:
        st.warning("⚠️ 请输入 API Key")
        st.stop()
    client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
    system_msg = f"You are an AP tutor. Language: {st.session_state.curr_lang}. Rules: Use LaTeX. Socratic method (guide, don't answer). Ask one question at a time."
    with st.spinner("⏳ 正在思考..."):
        response = client.messages.create(model=MODEL_NAME, max_tokens=1500, system=system_msg, messages=st.session_state.messages)
    return response.content[0].text

if not st.session_state.messages:
    init_prompt = f"请针对 {concept} 给出第一道 AP 风格习题。" if st.session_state.curr_lang == "Chinese" else f"Give me the first AP-style problem for {concept}."
    st.session_state.messages.append({"role": "user", "content": init_prompt})
    res = get_ai_response()
    if res:
        st.session_state.messages.append({"role": "assistant", "content": res})
        st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("请输入问题或上传解析..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    res = get_ai_response()
    if res:
        st.session_state.messages.append({"role": "assistant", "content": res})
        st.rerun()

# --- 核心优化：按钮语义联动 ---
btn_label = "▶️ 刷新/下一题" if st.session_state.curr_lang == "Chinese" else "▶️ Refresh/Next Problem"
if st.button(btn_label):
    next_prompt = f"请针对 {concept} 继续出下一道 AP 难度习题。" if st.session_state.curr_lang == "Chinese" else f"Please give me the next AP-level problem for {concept}."
    st.session_state.messages.append({"role": "user", "content": next_prompt})
    res = get_ai_response()
    if res:
        st.session_state.messages.append({"role": "assistant", "content": res})
        st.rerun()

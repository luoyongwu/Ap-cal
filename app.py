
import streamlit as st
from anthropic import Anthropic

MODEL_NAME = "claude-sonnet-4-6"

st.set_page_config(page_title="Luo-cal 动态翻译版", layout="wide")

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

# --- 核心辅助函数：后台原地翻译网关 ---
def translate_history(target_lang):
    if not st.session_state.messages or not st.session_state.ENV_CLAUDE_KEY:
        return
    
    client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
    translated_messages = []
    
    with st.spinner("🌐 正在为您无缝转换界面语言，请稍候..."):
        for msg in st.session_state.messages:
            # 针对每一条历史记录，命令 Claude 进行精准语言对译，必须保留全部 LaTeX 数学公式
            prompt = f"Translate the following AP Calculus teaching content into {'English' if target_lang == 'English' else 'Simplified Chinese (简体中文)'}. Keep all LaTeX math expressions (like $...$ or $$...$$) exactly as they are. Do not add any explanations outside the translation.\n\nContent to translate:\n{msg['content']}"
            
            response = client.messages.create(
                model=MODEL_NAME,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            translated_text = response.content[0].text.strip()
            translated_messages.append({"role": msg["role"], "content": translated_text})
            
    st.session_state.messages = translated_messages

# --- 状态拦截机 ---
# 场景 A: 如果用户切换了 Unit 概念，说明要换新题，此时“清空历史”
if selected_unit != st.session_state.curr_unit:
    st.session_state.curr_unit = selected_unit
    st.session_state.messages = []
    st.rerun()

# 场景 B: 如果用户只是切换了【语言】，触发“原地无缝历史翻译”，保留内容只变文字
if lang != st.session_state.curr_lang:
    if st.session_state.messages: # 只有存在历史对话时才触发翻译
        translate_history(lang)
    st.session_state.curr_lang = lang
    st.rerun()

st.title(f"{selected_unit} - {concept}")

# --- 核心大模型对话引擎 ---
def get_ai_response():
    if not st.session_state.ENV_CLAUDE_KEY:
        st.warning("⚠️ 请先在左侧输入 API Key")
        st.stop()
        
    client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
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
btn_label = "▶️ 下一题" if st.session_state.curr_lang == "Chinese" else "▶️ Next Problem"
if st.button(btn_label):
    next_prompt = f"请针对 {concept} 继续出下一道 AP 难度习题。" if st.session_state.curr_lang == "Chinese" else f"Please give me the next AP-level problem for {concept}."
    st.session_state.messages.append({"role": "user", "content": next_prompt})
    res = get_ai_response()
    if res:
        st.session_state.messages.append({"role": "assistant", "content": res})
        st.rerun()

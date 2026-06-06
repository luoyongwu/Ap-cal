
import streamlit as st
from anthropic import Anthropic

MODEL_NAME = "claude-sonnet-4-20250514"
st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide")

# 从 Secrets 读取 Key
st.session_state.api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
if not st.session_state.api_key:
    st.error("请在 Streamlit Cloud Secrets 中配置 ANTHROPIC_API_KEY")
    st.stop()

CONCEPT_OPTIONS = {"1.1 极限简介": "1.1", "3.1 链式法则": "3.1", "3.2 隐函数求导": "3.2", "3.4 反函数求导": "3.4"}
CONCEPT_CONSTRAINTS = {
    "1.1": "Ensure student builds intuition numerically/graphically before algebra.",
    "3.1": "HARD RULE: Decompose f(g(x)) into f(u) and g(x) explicitly. If absent, redirect.",
    "3.2": "Focus on implicit differentiation notation. If dy/dx is missing, redirect.",
    "3.4": "Verify inverse function domain constraints. If domain logic is skipped, redirect."
}

for k, v in {
    "messages": [], "curr_concept": "3.1 链式法则",
    "mastery_scores": {}, "mastery_ready": False, "last_summary": "",
}.items():
    if k not in st.session_state: st.session_state[k] = v

def update_mastery(concept_id, response_text):
    scores = st.session_state.mastery_scores
    if concept_id not in scores: scores[concept_id] = 0
    if "[STATUS: CORRECT]" in response_text: scores[concept_id] += 1
    elif "[STATUS: INCORRECT]" in response_text or "[STATUS: PARTIAL]" in response_text: scores[concept_id] = 0
    if scores[concept_id] >= 3: st.session_state.mastery_ready = True

def generate_summary(concept_id):
    client = Anthropic(api_key=st.session_state.api_key)
    digest = "\n".join(f"{m['role'].upper()}: {m['content'][:200]}" for m in st.session_state.messages[-8:])
    prompt = f"Based on this tutoring for {concept_id}:\n{digest}\nGenerate a structured summary in Chinese:\n1. 核心法则: [公式]\n2. 关键步骤: 1. ...\n3. ⚠️ 陷阱提示: [学生错误]"
    return client.messages.create(model=MODEL_NAME, max_tokens=600, messages=[{"role": "user", "content": prompt}]).content[0].text

def get_ai_response(extra_content=None):
    client = Anthropic(api_key=st.session_state.api_key)
    concept_id = CONCEPT_OPTIONS[st.session_state.curr_concept]
    system_msg = f"Strict AP Calculus tutor. {CONCEPT_CONSTRAINTS.get(concept_id, '')} \nRESPONSE FORMAT: Append one tag: [STATUS: CORRECT], [STATUS: PARTIAL], [STATUS: INCORRECT], [STATUS: GUIDING]."
    msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    if extra_content: msgs.append({"role": "user", "content": extra_content})
    with st.spinner("⏳ 导师思考中…"):
        response = client.messages.create(model=MODEL_NAME, max_tokens=1500, system=system_msg, messages=msgs)
        reply = response.content[0].text
        update_mastery(concept_id, reply)
        return reply.replace("[STATUS: CORRECT]", "").replace("[STATUS: PARTIAL]", "").replace("[STATUS: INCORRECT]", "").replace("[STATUS: GUIDING]", "").rstrip()

st.sidebar.title("🎓 Luo-cal 控制台")
st.session_state.curr_concept = st.sidebar.selectbox("选择概念", list(CONCEPT_OPTIONS.keys()))

if not st.session_state.messages:
    opening = get_ai_response(f"请为概念 {st.session_state.curr_concept} 出一道练习题。")
    st.session_state.messages.append({"role": "assistant", "content": opening})
    st.rerun()

if st.button("🔄 刷新概念"): 
    st.session_state.messages = []; st.session_state.last_summary = ""; st.session_state.mastery_ready = False; st.session_state.mastery_scores = {}; st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("输入回答..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    response = get_ai_response()
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

if st.session_state.mastery_ready:
    if st.button("💡 生成深度总结"):
        st.session_state.last_summary = generate_summary(CONCEPT_OPTIONS[st.session_state.curr_concept])
        st.session_state.mastery_ready = False
        st.rerun()

if st.session_state.last_summary:
    with st.expander("🎓 知识点总结", expanded=True): st.markdown(st.session_state.last_summary)


import streamlit as st
from anthropic import Anthropic
import base64

MODEL_NAME = "claude-sonnet-4-20250514"
st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide")

CONCEPT_OPTIONS = {"1.1 极限简介": "1.1", "3.1 链式法则": "3.1", "3.2 隐函数求导": "3.2", "3.4 反函数求导": "3.4"}
CONCEPT_CONSTRAINTS = {
    "1.1": "Ensure student builds intuition numerically/graphically before algebra.",
    "3.1": "HARD RULE: Decompose f(g(x)) into f(u) and g(x) explicitly. If absent, redirect.",
    "3.2": "Focus on implicit differentiation notation. If dy/dx is missing, redirect.",
    "3.4": "Verify inverse function domain constraints. If domain logic is skipped, redirect."
}

for k, v in {
    "messages": [], "api_key": "", "key_confirmed": False,
    "curr_concept": "3.1 链式法则", "mastery_scores": {},
    "mastery_ready": False, "last_summary": "",
}.items():
    if k not in st.session_state: st.session_state[k] = v

# ── 侧边栏配置页 ──────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ 配置页")
    key_input = st.text_input("🔑 Claude API Key", type="password", value=st.session_state.api_key)
    if st.button("✅ 确认 Key"):
        if key_input.startswith("sk-"):
            st.session_state.api_key = key_input
            st.session_state.key_confirmed = True
            st.success("Key 已锁定")
        else: st.error("Key 格式错误")
    st.divider()
    st.session_state.curr_concept = st.selectbox("选择概念", list(CONCEPT_OPTIONS.keys()))
    st.divider()
    if st.session_state.key_confirmed: st.success("🟢 系统已连接")
    else: st.error("🔴 未连接 (请输入 Key)")

# ── 核心函数 ──────────────────────────────────────────────
def update_mastery(concept_id, response_text):
    scores = st.session_state.mastery_scores
    if concept_id not in scores: scores[concept_id] = 0
    if "[STATUS: CORRECT]" in response_text: scores[concept_id] += 1
    elif "[STATUS: INCORRECT]" in response_text or "[STATUS: PARTIAL]" in response_text: scores[concept_id] = 0
    if scores[concept_id] >= 3: st.session_state.mastery_ready = True

def generate_summary(concept_id):
    client = Anthropic(api_key=st.session_state.api_key)
    digest = "\n".join(f"{m['role'].upper()}: {m['content'][:200]}" for m in st.session_state.messages[-8:] if isinstance(m.get("content"), str))
    prompt = f"Based on this tutoring for {concept_id}:\n{digest}\nGenerate structured summary in Chinese:\n1. 核心法则: [公式]\n2. 关键步骤: 1. ...\n3. ⚠️ 陷阱提示: [学生实际犯错点]"
    return client.messages.create(model=MODEL_NAME, max_tokens=600, messages=[{"role": "user", "content": prompt}]).content[0].text

def get_ai_response(extra_content=None):
    client = Anthropic(api_key=st.session_state.api_key)
    concept_id = CONCEPT_OPTIONS[st.session_state.curr_concept]
    system_msg = (f"Strict AP Calculus Socratic tutor. Respond in Chinese. "
                  f"{CONCEPT_CONSTRAINTS.get(concept_id, '')} \nRESPONSE FORMAT: Append one tag: [STATUS: CORRECT], [STATUS: PARTIAL], [STATUS: INCORRECT], [STATUS: GUIDING].")
    msgs = []
    for m in st.session_state.messages:
        if isinstance(m.get("content"), (str, list)): msgs.append({"role": m["role"], "content": m["content"]})
    if extra_content: msgs.append({"role": "user", "content": extra_content})
    with st.spinner("⏳ 导师思考中…"):
        response = client.messages.create(model=MODEL_NAME, max_tokens=1500, system=system_msg, messages=msgs)
        reply = response.content[0].text
        update_mastery(concept_id, reply)
        for tag in ["[STATUS: CORRECT]","[STATUS: PARTIAL]","[STATUS: INCORRECT]","[STATUS: GUIDING]"]: reply = reply.replace(tag, "")
        return reply.rstrip()

# ── 主界面 ────────────────────────────────────────────────
st.title(f"🎓 Luo-cal: {st.session_state.curr_concept}")
if not st.session_state.key_confirmed:
    st.info("请在左侧配置页输入 API Key 并点击确认。")
    st.stop()

if not st.session_state.messages:
    opening = get_ai_response(f"请为概念 {st.session_state.curr_concept} 出一道练习题。")
    st.session_state.messages.append({"role": "assistant", "content": opening})
    st.rerun()

if st.button("🔄 刷新概念"):
    st.session_state.messages = []; st.session_state.last_summary = ""; st.session_state.mastery_ready = False; st.session_state.mastery_scores = {}
    st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if isinstance(m["content"], str): st.markdown(m["content"])
        elif isinstance(m["content"], list):
            for block in m["content"]:
                if block.get("type") == "text": st.markdown(block["text"])
                elif block.get("type") == "image": st.image(base64.b64decode(block["source"]["data"]))

# 图片上传模块（相机+相册）
with st.expander("📷 上传手写题目（拍照或选图）"):
    col1, col2 = st.columns(2)
    with col1: photo = st.camera_input("📸 拍照")
    with col2: uploaded = st.file_uploader("🖼️ 从相册选图", type=["jpg","jpeg","png"], accept_multiple_files=True)
    pending = []
    if photo: pending.append(("image/jpeg", photo.read()))
    if uploaded:
        for f in uploaded: pending.append(("image/png" if f.name.endswith(".png") else "image/jpeg", f.read()))
    if pending:
        st.write(f"已选 {len(pending)} 张图片：")
        cols = st.columns(len(pending))
        for i, (m, d) in enumerate(pending): cols[i].image(d, width=120)
        if st.button("✅ 确认发送图片"):
            content = [{"type": "image", "source": {"type": "base64", "media_type": m, "data": base64.b64encode(d).decode()}} for m, d in pending]
            content.append({"type": "text", "text": "请分析图中的数学题目或手写答案，按苏格拉底方式引导。"})
            st.session_state.messages.append({"role": "user", "content": content})
            response = get_ai_response()
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

if prompt := st.chat_input("输入回答..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    response = get_ai_response()
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

if st.session_state.mastery_ready:
    st.divider(); st.success("✅ 连续3次正确！已解锁知识点总结。")
    if st.button("💡 生成深度总结"):
        st.session_state.last_summary = generate_summary(CONCEPT_OPTIONS[st.session_state.curr_concept])
        st.session_state.mastery_ready = False
        st.rerun()

if st.session_state.last_summary:
    with st.expander("🎓 知识点总结", expanded=True): st.markdown(st.session_state.last_summary)

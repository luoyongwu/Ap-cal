import streamlit as st
from anthropic import Anthropic
import base64

MODEL_NAME = "claude-sonnet-4-6"
st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide")

# ── 1. 状态初始化 ──────────────────────────────────────────
for k, v in {
    "messages": [],
    "api_key": "",
    "curr_lang": "Chinese",
    "curr_unit": "第一单元: 极限与连续",
    "pending_image": None,
    "pending_media_type": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── 2. 核心教学配置 ──────────────────────────────────────────
BILINGUAL_MATRIX = {
    "Chinese": {"Units": {
        "第一单元: 极限与连续": ["1.1 极限简介","1.2 渐近线","1.3 连续性","1.4 夹逼定理","1.5 介值定理"],
        "第二单元: 导数基础": ["2.1 导数定义","2.2 幂/乘积法则","2.3 链式法则","2.4 高阶导数"],
        "第三单元: 复合、隐函数与反函数微分": ["3.1 链式法则进阶","3.2 隐函数求导","3.3 反函数","3.4 反函数导数"],
        "第四单元: 微分的情境应用": ["4.1 相关变化率","4.2 洛必达法则","4.3 均值定理","4.4 极值与拐点","4.5 线性近似"],
    }},
    "English": {"Units": {
        "Unit 1: Limits & Continuity": ["1.1 Limits Intro","1.2 Asymptotes","1.3 Continuity","1.4 Squeeze Theorem","1.5 Intermediate Value Theorem"],
        "Unit 2: Derivatives": ["2.1 Derivative Definition","2.2 Power/Product Rules","2.3 Chain Rule","2.4 Higher-Order Derivatives"],
        "Unit 3: Composite, Implicit & Inverse": ["3.1 Chain Rule Advanced","3.2 Implicit Differentiation","3.3 Inverse Functions","3.4 Derivatives of Inverse"],
        "Unit 4: Contextual Applications": ["4.1 Related Rates","4.2 L'Hopital's Rule","4.3 Mean Value Theorem","4.4 Extrema & Inflection","4.5 Linear Approximation"],
    }},
}

CONCEPT_CONSTRAINTS = {
    "1.1": "Ensure student builds intuition numerically/graphically before algebra.", "1.2": "Identify asymptote type before proceeding.",
    "1.3": "Check ALL THREE: limit exists, f(a) exists, they are equal.", "1.4": "Explicitly identify bounding functions.",
    "1.5": "Verify continuity on [a,b] before IVT.", "2.1": "Use limit definition h->0 at least once.",
    "2.2": "Identify rule (power vs product) before differentiating.", "2.3": "Identify outer/inner function explicitly.",
    "2.4": "Interpret physical meaning of derivative order.", "3.1": "Decompose f(g(x)) into f(u) and g(x) explicitly.",
    "3.2": "Always explicitly write dy/dx.", "3.3": "Use f_inv(f(x)) = x for all derivations.",
    "3.4": "Derive (f_inv)'(a) = 1 / f'(f_inv(a)) step by step.", "4.1": "Write related-rates equation with d/dt BEFORE substituting.",
    "4.2": "Verify 0/0 or inf/inf indeterminate form before applying L'Hopital.", "4.3": "Verify continuity on [a,b] AND differentiability on (a,b) before MVT.",
    "4.4": "Require sign chart analysis and explicit concavity statement.", "4.5": "State L(x) = f(a) + f'(a)(x-a) as premise."
}

# ── 3. 侧边栏 UI ───────────────────────────────────────────
st.sidebar.title("🎓 Luo-cal 教学控制台")
stored_key = st.session_state.api_key
placeholder = ("*" * 8 + stored_key[-4:]) if len(stored_key) > 8 else ("*" * len(stored_key) if stored_key else "请粘贴 Claude API Key")
key_input = st.sidebar.text_input("🔑 API Key:", type="password", value="", placeholder=placeholder)
if key_input.strip(): st.session_state.api_key = key_input.strip()

if st.session_state.api_key: st.sidebar.success("🟢 密钥已锁定")
else: st.sidebar.warning("🔴 请输入 API Key")

lang = st.sidebar.radio("🌐 语言:", ["Chinese", "English"], index=["Chinese", "English"].index(st.session_state.curr_lang))
if lang != st.session_state.curr_lang:
    old_units = list(BILINGUAL_MATRIX[st.session_state.curr_lang]["Units"].keys())
    new_units = list(BILINGUAL_MATRIX[lang]["Units"].keys())
    try: st.session_state.curr_unit = new_units[old_units.index(st.session_state.curr_unit)]
    except: st.session_state.curr_unit = new_units[0]
    st.session_state.curr_lang = lang
    st.session_state.messages = []
    st.rerun()

units_map = BILINGUAL_MATRIX[st.session_state.curr_lang]["Units"]
unit_keys = list(units_map.keys())
if st.session_state.curr_unit not in unit_keys: st.session_state.curr_unit = unit_keys[0]
selected_unit = st.sidebar.selectbox("📂 选择 Unit:", unit_keys, index=unit_keys.index(st.session_state.curr_unit))
if selected_unit != st.session_state.curr_unit:
    st.session_state.curr_unit = selected_unit
    st.session_state.messages = []
    st.rerun()

concept = st.sidebar.selectbox("🎯 选择 Concept:", units_map[selected_unit])
st.title(f"{selected_unit} — {concept}")

# ── 4. 引擎核心 ─────────────────────────────────────────────
def get_ai_response(extra_content=None):
    if not st.session_state.api_key: st.warning("⚠️ 请输入 API Key！"); st.stop()
    client = Anthropic(api_key=st.session_state.api_key)
    concept_id = concept.split()[0]
    constraint = CONCEPT_CONSTRAINTS.get(concept_id, "Guide step-by-step.")
    system_msg = f"You are a strict AP Calculus tutor. Respond in {st.session_state.curr_lang}.\n\nConstraint: {constraint}\n1. LaTeX math. 2. No direct answers. 3. Socratic guide."
    api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    if extra_content: api_messages.append({"role": "user", "content": extra_content})
    with st.spinner("⏳ 导师思考中…"):
        return client.messages.create(model=MODEL_NAME, max_tokens=1500, system=system_msg, messages=api_messages).content[0].text

# ── 5. MADNESS 压力测试旁路 ─────────────────────────────────
with st.sidebar.expander("🧪 MADNESS 压力测试"):
    test_input = st.text_input("输入测试陷阱回答：", placeholder="输入一个错误答案来测试导师反应…", key="madness_input")
    # ✅ 修正：容器内直接调用 st.button 继承侧边栏上下文
    if st.button("⚡ 执行压力测试"):
        if st.session_state.api_key and test_input.strip():
            st.session_state.messages = []
            ctx = (f"我们正在练习《{concept}》。学生回答：{test_input}。严格依据约束评估：" 
                   if st.session_state.curr_lang == "Chinese" 
                   else f"We are practicing '{concept}'. Student answer: {test_input}. Strictly evaluate per teaching constraints:")
            st.session_state.messages.append({"role": "user", "content": ctx, "is_test_probe": True})
            reply = get_ai_response()
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()

# ── 6. 图片逻辑 ─────────────────────────────────────────────
with st.expander("📷 上传作业照片 / 拍照"):
    t1, t2 = st.tabs(["📸 实时拍照", "🖼️ 相册选图"])
    with t1: cam = st.camera_input("拍照")
    with t2: up = st.file_uploader("文件", type=["jpg", "jpeg", "png", "webp"])
    if cam is not None: st.session_state.pending_image = cam.getvalue(); st.session_state.pending_media_type = "image/jpeg"; st.success("✅ 照片已暂存")
    if up is not None: st.session_state.pending_image = up.read(); st.session_state.pending_media_type = up.type; st.success("✅ 图片已暂存")
    if st.session_state.pending_image:
        cap = st.text_input("附加说明", placeholder="检查我的解题过程...")
        if st.button("✅ 确定发送图片"):
            img_b64 = base64.b64encode(st.session_state.pending_image).decode("utf-8")
            blocks = [{"type": "image", "source": {"type": "base64", "media_type": st.session_state.pending_media_type, "data": img_b64}}, 
                      {"type": "text", "text": cap or "请分析我的作业。"} ]
            reply = get_ai_response(blocks)
            st.session_state.messages.append({"role": "user", "content": f"[📷 图片] {cap}"})
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.session_state.pending_image = st.session_state.pending_media_type = None
            st.rerun()

# ── 7. 对话流 ──────────────────────────────────────────────
col_r, col_n = st.columns(2)
if col_r.button("🔄 刷新当前概念"): st.session_state.messages = []; st.rerun()
if col_n.button("▶️ 下一题"):
    st.session_state.messages.append({"role": "user", "content": "请出下一题。"})
    st.session_state.messages.append({"role": "assistant", "content": get_ai_response()})
    st.rerun()

if not st.session_state.messages:
    with st.chat_message("assistant"): st.markdown("⏳ 导师正在为您准备第一题…")
    init_p = "请针对此概念出第一道题并引导我。" if st.session_state.curr_lang == "Chinese" else "Give me the first problem."
    reply = get_ai_response(extra_content=[{"type": "text", "text": init_p}])
    st.session_state.messages.append({"role": "user", "content": init_p})
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
for m in st.session_state.messages:
    if not m.get("is_test_probe"):
        with st.chat_message(m["role"]): st.markdown(m["content"])

# ── 8. 通用发送输入块 ────────────────────────────────────────
c_in, c_btn = st.columns([0.85, 0.15])
with c_in:
    user_input = st.text_input("输入解答或问题…", key="input_text", label_visibility="collapsed")
with c_btn:
    send_btn = st.button("发送")

if send_btn and user_input.strip():
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": get_ai_response()})
    st.rerun()

import streamlit as st
from anthropic import Anthropic

MODEL_NAME = "claude-sonnet-4-6"
st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide")

# ── 初始化 ──────────────────────────────────────────────
if "messages"       not in st.session_state: st.session_state.messages       = []
if "ENV_CLAUDE_KEY" not in st.session_state: st.session_state.ENV_CLAUDE_KEY = ""
if "curr_lang"      not in st.session_state: st.session_state.curr_lang      = "Chinese"
if "curr_unit"      not in st.session_state: st.session_state.curr_unit      = "第一单元: 极限与连续"

# ── 概念矩阵与约束字典 ──────────────────────────────────
BILINGUAL_MATRIX = {
    "Chinese": {
        "Units": {
            "第一单元: 极限与连续": ["1.1 极限简介", "1.2 渐近线", "1.3 连续性", "1.4 夹逼定理", "1.5 介值定理"],
            "第二单元: 导数基础": ["2.1 导数定义", "2.2 幂/乘积法则", "2.3 链式法则", "2.4 高阶导数"],
            "第三单元: 复合、隐函数与反函数微分": ["3.1 链式法则进阶", "3.2 隐函数求导", "3.3 反函数", "3.4 反函数导数"],
            "第四单元: 微分的情境应用": ["4.1 相关变化率", "4.2 洛必达法则", "4.3 均值定理", "4.4 极值与拐点", "4.5 线性近似"]
        }
    },
    "English": {
        "Units": {
            "Unit 1: Limits & Continuity": ["1.1 Limits Intro", "1.2 Asymptotes", "1.3 Continuity", "1.4 Squeeze Theorem", "1.5 Intermediate Value Theorem"],
            "Unit 2: Derivatives": ["2.1 Derivative Definition", "2.2 Power/Product Rules", "2.3 Chain Rule", "2.4 Higher-Order Derivatives"],
            "Unit 3: Composite, Implicit & Inverse": ["3.1 Chain Rule Advanced", "3.2 Implicit Differentiation", "3.3 Inverse Functions", "3.4 Derivatives of Inverse"],
            "Unit 4: Contextual Applications": ["4.1 Related Rates", "4.2 L'Hopital's Rule", "4.3 Mean Value Theorem", "4.4 Extrema & Inflection", "4.5 Linear Approximation"]
        }
    }
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

# ── 界面 UI ─────────────────────────────────────────────
st.sidebar.title("🎓 Luo-cal 教学控制台")
key_input = st.sidebar.text_input("🔑 API Key:", type="password", value=st.session_state.ENV_CLAUDE_KEY)
if key_input.strip():
    st.session_state.ENV_CLAUDE_KEY = key_input.strip()

lang = st.sidebar.radio("🌐 语言:", ["Chinese", "English"], index=["Chinese", "English"].index(st.session_state.curr_lang))
if lang != st.session_state.curr_lang:
    old_units = list(BILINGUAL_MATRIX[st.session_state.curr_lang]["Units"].keys())
    new_units = list(BILINGUAL_MATRIX[lang]["Units"].keys())
    try: idx = old_units.index(st.session_state.curr_unit); st.session_state.curr_unit = new_units[idx]
    except: st.session_state.curr_unit = new_units[0]
    st.session_state.curr_lang = lang
    st.session_state.messages = []
    st.rerun()

units_map = BILINGUAL_MATRIX[st.session_state.curr_lang]["Units"]
selected_unit = st.sidebar.selectbox("📂 选择 Unit:", list(units_map.keys()), index=list(units_map.keys()).index(st.session_state.curr_unit))
if selected_unit != st.session_state.curr_unit:
    st.session_state.curr_unit = selected_unit
    st.session_state.messages = []
    st.rerun()

concept = st.sidebar.selectbox("🎯 选择 Concept:", units_map[selected_unit])
st.title(f"{selected_unit} — {concept}")

# ── 响应引擎（含防御性 Key 检查） ───────────────────────
def get_ai_response():
    if not st.session_state.ENV_CLAUDE_KEY:
        st.warning("⚠️ 请输入 Claude API Key 以激活教学引擎。")
        st.stop()
    client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
    concept_id = concept.split()[0]
    constraint = CONCEPT_CONSTRAINTS.get(concept_id, "Guide student step-by-step.")
    system_msg = f"You are a strict AP Calculus tutor. Respond in {st.session_state.curr_lang}.\n\nConstraint for {concept_id}: {constraint}\n1. Use LaTeX for math. 2. NEVER give direct answers. 3. ONE step at a time."
    return client.messages.create(model=MODEL_NAME, max_tokens=1500, system=system_msg, messages=st.session_state.messages).content[0].text

# ── 对话逻辑与刷新按钮 ──────────────────────────────────
if not st.session_state.messages:
    init_p = "请针对此概念出第一道题并引导我。" if st.session_state.curr_lang == "Chinese" else "Give me the first problem for this concept."
    st.session_state.messages.append({"role": "user", "content": init_p})
    st.session_state.messages.append({"role": "assistant", "content": get_ai_response()})
    st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("Enter response..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append({"role": "assistant", "content": get_ai_response()})
    st.rerun()

# [新增] 刷新下一题按钮
btn_label = "▶️ 下一题" if st.session_state.curr_lang == "Chinese" else "▶️ Next Problem"
next_p = "请继续针对此概念出下一道题。" if st.session_state.curr_lang == "Chinese" else "Give me the next problem for this concept."
if st.button(btn_label):
    st.session_state.messages.append({"role": "user", "content": next_p})
    st.session_state.messages.append({"role": "assistant", "content": get_ai_response()})
    st.rerun()

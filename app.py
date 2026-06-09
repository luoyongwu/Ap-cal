
import streamlit as st
from anthropic import Anthropic
import base64

st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide")

# ══════════════════════════════════════════════════════
# 后端适配器层
# ══════════════════════════════════════════════════════

class AnthropicAdapter:
    MODEL = "claude-sonnet-4-20250514"
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)
    def chat(self, system, messages, max_tokens=1500):
        r = self.client.messages.create(
            model=self.MODEL, system=system,
            messages=messages, max_tokens=max_tokens)
        return r.content[0].text

class DeepSeekAdapter:
    MODEL = "deepseek-chat"
    def __init__(self, api_key):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com")
    def chat(self, system, messages, max_tokens=1500):
        msgs = [{"role": "system", "content": system}] + messages
        r = self.client.chat.completions.create(
            model=self.MODEL, messages=msgs, max_tokens=max_tokens)
        return r.choices[0].message.content

class OllamaAdapter:
    def __init__(self, model="gemma3"):
        self.model = model
        self.url = "http://localhost:11434/api/chat"
    def chat(self, system, messages, max_tokens=1500):
        msgs = [{"role": "system", "content": system}] + messages
        r = __import__("requests").post(
            self.url,
            json={"model": self.model, "messages": msgs, "stream": False})
        return r.json()["message"]["content"]

BACKENDS = {
    "Anthropic (Claude)": "anthropic",
    "DeepSeek":           "deepseek",
    "本地 Ollama (Gemma)": "ollama",
}

def get_adapter():
    b = st.session_state.backend
    k = st.session_state.api_key
    if b == "anthropic":
        return AnthropicAdapter(k)
    elif b == "deepseek":
        return DeepSeekAdapter(k)
    else:
        return OllamaAdapter()

# ══════════════════════════════════════════════════════
# 教学数据
# ══════════════════════════════════════════════════════

UNITS = {
    "Unit 1: 极限与连续": {
        "1.1 极限简介": "1.1", "1.2 极限计算": "1.2",
        "1.3 连续性": "1.3", "1.4 渐近线": "1.4",
        "1.X 综合练习": "1.X"
    },
    "Unit 2: 导数定义": {
        "2.1 导数定义": "2.1", "2.2 可导与连续": "2.2",
        "2.3 导数图像": "2.3", "2.4 高阶导数": "2.4",
        "2.X 综合练习": "2.X"
    },
    "Unit 3: 求导法则": {
        "3.1 链式法则": "3.1", "3.2 隐函数求导": "3.2",
        "3.3 乘积与商法则": "3.3", "3.4 反函数求导": "3.4",
        "3.5 参数方程求导": "3.5",
        "3.X 综合练习": "3.X"
    },
    "Unit 4: 导数应用": {
        "4.1 极值定理": "4.1",
        "4.2 中值定理": "4.2",
        "4.3 相关变化率": "4.3",
        "4.4 导数图像判读": "4.4",
        "4.5 线性近似": "4.5",
        "4.X 综合练习": "4.X"
    },
}

CONCEPT_CONSTRAINTS = {
    # ── Unit 1 ──────────────────────────────────────────
    "1.1": "Ensure student builds intuition numerically/graphically before algebra. "
           "Start with a concrete numerical example before asking about the formal definition.",
    "1.2": "Guide student to apply limit laws step by step. Do not skip steps.",
    "1.3": "Focus on the three-part definition of continuity at a point.",
    "1.4": "Guide student to identify vertical and horizontal asymptotes separately. "
           "Check both sides for vertical asymptotes.",
    "1.X": "Generate a comprehensive problem combining limits, continuity, and asymptotes. "
           "Cover at least two sub-topics from Unit 1.",
    # ── Unit 2 ──────────────────────────────────────────
    "2.1": "HARD RULE: Guide student to derive the derivative using the limit definition "
           "f\'(x)=lim(h→0)[f(x+h)-f(x)]/h. Do not skip the limit process.",
    "2.2": "Ensure student understands differentiability implies continuity but not vice versa. "
           "Use a counterexample if needed.",
    "2.3": "Focus on connecting the sign of f\'(x) to increasing/decreasing behavior of f(x).",
    "2.4": "Guide student to apply differentiation rules repeatedly for higher-order derivatives.",
    "2.X": "Generate a comprehensive problem combining limit definition of derivative, "
           "differentiability, and graphical interpretation.",
    # ── Unit 3 ──────────────────────────────────────────
    "3.1": "HARD RULE: Decompose f(g(x)) into f(u) and g(x) explicitly before differentiating. "
           "If student skips decomposition, redirect immediately.",
    "3.2": "HARD RULE: Ensure dy/dx appears explicitly when differentiating y terms. "
           "If missing, redirect.",
    "3.3": "HARD RULE: For products, require student to identify u and v explicitly before "
           "applying (uv)\'=u\'v+uv\'. For quotients, require student to identify numerator "
           "and denominator before applying the quotient rule.",
    "3.4": "Verify student correctly applies the inverse function derivative formula. "
           "Check that f\'(f⁻¹(x)) is evaluated at the correct point.",
    "3.5": "HARD RULE: Require student to write dx/dt and dy/dt separately before computing "
           "dy/dx=(dy/dt)/(dx/dt). Do not allow direct substitution without showing both derivatives.",
    "3.X": "Generate a comprehensive problem combining chain rule, implicit differentiation, "
           "product/quotient rules, inverse function derivatives, and parametric derivatives.",
    # ── Unit 4 ──────────────────────────────────────────
    "4.1": "HARD RULE: Student MUST explicitly state and verify ALL conditions of the Extreme "
           "Value Theorem (closed interval + continuity) before applying it. "
           "If student jumps to finding critical points without stating conditions, redirect. "
           "CRITICAL POINT RULE: Critical points include ALL points where f\'=0 OR f\' does not "
           "exist (e.g. corners, cusps). If student claims a non-differentiable point is not a "
           "critical point, correct immediately. "
           "ENDPOINT RULE: Always require comparison of ALL candidates: critical points AND "
           "both endpoints. If student compares only critical points, ask: "
           "\'你比较了所有候选点吗？端点的函数值是多少？/ "
           "Did you compare all candidates? What are the function values at the endpoints?\'",
    "4.2": "HARD RULE: Student MUST verify all THREE MVT hypotheses in order: "
           "(1) continuity on [a,b], (2) differentiability on (a,b), before applying the theorem. "
           "If student skips hypothesis verification, redirect immediately. "
           "IVT vs MVT RULE: If student uses MVT to prove existence of a zero (root), "
           "correct immediately: MVT gives f\'(c) = average rate of change, not f(c)=0. "
           "The correct theorem for zero existence is the Intermediate Value Theorem (IVT). "
           "TWO-STEP UNIQUENESS RULE: For \'exactly one root\' problems, require TWO separate "
           "steps: Step 1 = existence via IVT, Step 2 = uniqueness via monotonicity (f\'>0 or f\'<0). "
           "Do not accept a proof that skips either step. "
           "If student states f\'(x)>0 without computing f\'(x) explicitly, ask: "
           "\'请计算 f\'(x) 并说明它为何恒正。/ Please compute f\'(x) and explain why it is always positive.\'",
    "4.3": "HARD RULE: Student MUST follow this exact sequence: "
           "(1) identify and name all variables, (2) write the relationship equation, "
           "(3) differentiate with respect to time t using chain rule, (4) THEN substitute values. "
           "PRE-SUBSTITUTION TRAP: If student substitutes a specific numerical value into a "
           "variable BEFORE differentiating (e.g. writes A=25π then differentiates), "
           "intercept immediately: "
           "\'你在求导前代入了具体数值，这会把变量变成常数，导数为0。"
           "请保留变量形式，对时间t求导后再代入。/ "
           "You substituted a value before differentiating. This turns the variable into a "
           "constant with derivative 0. Keep the variable, differentiate with respect to t first, "
           "then substitute.\' "
           "SIGN RULE: Always require student to interpret the physical meaning of negative "
           "derivatives (e.g. negative dy/dt means the quantity is decreasing).",
    "4.4": "DERIVATIVE GRAPH READING RULE: Guide student to carefully distinguish between "
           "properties of f\'(x) and the corresponding properties of f(x). "
           "HARD RULE 1 — INFLECTION POINT: Where f\'(x) has a local extremum (max or min), "
           "f(x) has an INFLECTION POINT, NOT an extremum. If student confuses these, "
           "redirect immediately: "
           "\'f\'在该点有极值，这意味着f\'在该点改变单调性，即f在该点有拐点，不是极值点。/ "
           "f\' has an extremum here, meaning f\' changes monotonicity, so f has an inflection "
           "point here, not an extremum.\' "
           "HARD RULE 2 — SIGN CHANGE VERIFICATION: f\'(x)=0 is necessary but NOT sufficient "
           "for an inflection point of f(x). Student MUST verify that f\'(x) changes sign "
           "around that zero. If student claims a zero of f\' is automatically an inflection "
           "point without checking sign change, redirect. "
           "CONCAVITY RULE: Where f\'(x) is increasing, f(x) is concave up (f\'\'>0). "
           "Where f\'(x) is decreasing, f(x) is concave down (f\'\'<0). "
           "Require student to state concavity explicitly.",
    "4.5": "HARD RULE: Student MUST write the full linearization formula "
           "L(x) = f(a) + f\'(a)(x-a) explicitly before substituting any values. "
           "DIRECT COMPUTATION TRAP: If student computes f(x_target) directly without using "
           "the linearization formula, redirect immediately: "
           "\'题目要求用线性化近似，必须通过切线方程L(x)计算，不能直接求值。/ "
           "The problem requires linearization. You must use the tangent line equation L(x), "
           "not direct computation.\' "
           "MISSING TERM TRAP: If student writes L(x) = f\'(a)(x-a) omitting f(a), "
           "redirect: \'线性化公式是L(x)=f(a)+f\'(a)(x-a)，你遗漏了f(a)这一项。/ "
           "The linearization formula is L(x)=f(a)+f\'(a)(x-a). You are missing the f(a) term.\' "
           "Require student to identify the base point a (choose a nearby value where f is easy "
           "to compute exactly), then compute f(a) and f\'(a) before substituting.",
    "4.X": "Generate a comprehensive problem combining EVT, MVT, related rates, "
           "derivative graph reading, and linear approximation. "
           "Cover at least three sub-topics from Unit 4.",
}

OPENING_PROMPTS = {
    # ── Unit 1 ──────────────────────────────────────────
    "1.X": "请出一道Unit 1综合题，综合考查极限、连续性和渐近线，包含至少两个子问题。",
    "1.X_en": "Generate a comprehensive Unit 1 problem covering limits, continuity, and asymptotes. Include at least two sub-questions.",
    # ── Unit 2 ──────────────────────────────────────────
    "2.X": "请出一道Unit 2综合题，综合考查导数定义、可导与连续、导数图像，包含至少两个子问题。",
    "2.X_en": "Generate a comprehensive Unit 2 problem covering limit definition of derivative, differentiability, and graphical interpretation. Include at least two sub-questions.",
    # ── Unit 3 ──────────────────────────────────────────
    "3.X": "请出一道Unit 3综合题，综合考查链式法则、隐函数求导、乘积与商法则、反函数求导和参数方程求导，包含至少两个子问题。",
    "3.X_en": "Generate a comprehensive Unit 3 problem covering chain rule, implicit differentiation, product/quotient rules, inverse function derivatives, and parametric derivatives. Include at least two sub-questions.",
    # ── Unit 4 ──────────────────────────────────────────
    "4.4": "请出一道导数图像判读题：给出一段关于f\'(x)图像特征的描述（如极值点、零点、正负区间），要求学生判断f(x)的增减性、凹凸性及拐点位置。不要直接给出答案，先只问第一个引导性问题。",
    "4.4_en": "Generate a derivative graph reading problem: describe key features of f\'(x) (such as local extrema, zeros, sign intervals), and ask the student to determine the monotonicity, concavity, and inflection points of f(x). Do not give the answer. Ask only the first guiding question.",
    "4.5": "请出一道线性近似题，要求学生用线性化公式L(x)=f(a)+f\'(a)(x-a)估算一个函数值（如sqrt(4.1)、sin(0.1)、e^0.1等）。不要直接给出步骤，先只问第一个引导性问题。",
    "4.5_en": "Generate a linearization problem asking the student to estimate a function value (e.g. sqrt(4.1), sin(0.1), e^0.1) using L(x)=f(a)+f\'(a)(x-a). Do not give steps. Ask only the first guiding question.",
    "4.X": "请出一道Unit 4综合题，综合考查极值定理、中值定理、相关变化率、导数图像判读和线性近似，包含至少三个子问题。",
    "4.X_en": "Generate a comprehensive Unit 4 problem covering EVT, MVT, related rates, derivative graph reading, and linear approximation. Include at least three sub-questions.",
}

LANG_LABELS = {
    "Chinese": {
        "title_prefix": "🎓 Luo-cal",
        "config": "⚙️ 配置页",
        "api_key": "🔑 API Key",
        "confirm_key": "✅ 确认 Key",
        "key_ok": "Key 已锁定",
        "key_err": "Key 格式错误（需以 sk- 开头）",
        "select_unit": "选择 Unit",
        "select_concept": "选择 Concept",
        "select_backend": "🔌 选择后端",
        "connected": "🟢 系统已连接",
        "disconnected": "🔴 未连接",
        "connected_color": "#1a7a1a",
        "disconnected_color": "#cc0000",
        "lang_btn": "切换为 English 🌐",
        "show_test": "🔧 显示测试面板",
        "wait": "请在左侧配置页输入 API Key 并点击确认。",
        "refresh": "🔄 刷新当前概念",
        "upload": "📷 上传手写题目（拍照或选图）",
        "camera": "📸 拍照",
        "gallery": "🖼️ 选图",
        "selected": "已选",
        "preview": "张，预览：",
        "send_img": "✅ 确认发送图片",
        "img_prompt": "请分析图中的手写内容，按苏格拉底方式引导。",
        "chat_input": "输入回答...",
        "mastery_msg": "✅ 连续3次正确！已解锁知识点总结。",
        "summary_btn": "💡 生成深度总结",
        "summary_title": "🎓 知识点总结",
        "generating": "生成总结中...",
        "test_panel": "🔧 测试面板",
        "test_input": "测试输入",
        "test_placeholder": "输入测试题目或学生答案...",
        "test_send": "✅ 确认发送测试",
        "test_working": "⏳ 系统正在工作，请稍后……",
        "test_empty": "请先输入内容。",
        "spinner": "⏳ 导师思考中…",
        "opening_default": "请为概念 {concept} 出一道练习题，不要直接给出解题步骤，先只问第一个引导性问题。",
        "lang_instr": "Respond in Chinese.",
        "summary_lang": "in Chinese",
        "secrets_notice": "🔑 已从系统配置自动加载 API Key",
        "ollama_notice": "🖥️ 本地 Ollama 模式，无需 API Key",
    },
    "English": {
        "title_prefix": "🎓 Luo-cal",
        "config": "⚙️ Settings",
        "api_key": "🔑 API Key",
        "confirm_key": "✅ Confirm Key",
        "key_ok": "Key locked",
        "key_err": "Invalid key format (must start with sk-)",
        "select_unit": "Select Unit",
        "select_concept": "Select Concept",
        "select_backend": "🔌 Select Backend",
        "connected": "🟢 Connected",
        "disconnected": "🔴 Disconnected",
        "connected_color": "#1a7a1a",
        "disconnected_color": "#cc0000",
        "lang_btn": "切换为中文 🌐",
        "show_test": "🔧 Show Test Panel",
        "wait": "Please enter your API Key in the sidebar and confirm.",
        "refresh": "🔄 Refresh Concept",
        "upload": "📷 Upload Handwritten Work (Camera or Gallery)",
        "camera": "📸 Take Photo",
        "gallery": "🖼️ Upload Image",
        "selected": "Selected",
        "preview": " image(s), preview:",
        "send_img": "✅ Send Image(s)",
        "img_prompt": "Please analyze the handwritten content and guide using the Socratic method.",
        "chat_input": "Enter your answer...",
        "mastery_msg": "✅ 3 consecutive correct answers! Summary unlocked.",
        "summary_btn": "💡 Generate Summary",
        "summary_title": "🎓 Knowledge Summary",
        "generating": "Generating summary...",
        "test_panel": "🔧 Test Panel",
        "test_input": "Test Input",
        "test_placeholder": "Enter test question or student answer...",
        "test_send": "✅ Send Test Input",
        "test_working": "⏳ System working, please wait……",
        "test_empty": "Please enter content first.",
        "spinner": "⏳ Tutor thinking…",
        "opening_default": "Generate one practice problem for {concept}. Do not give steps. Ask only the first guiding question.",
        "lang_instr": "Respond in English.",
        "summary_lang": "in English",
        "secrets_notice": "🔑 API Key loaded from system configuration",
        "ollama_notice": "🖥️ Local Ollama mode, no API Key needed",
    }
}

# ── 状态初始化 ────────────────────────────────────────────
for k, v in {
    "messages": [], "api_key": "", "key_confirmed": False,
    "backend": "anthropic",
    "curr_unit": "Unit 1: 极限与连续", "curr_concept": "1.1 极限简介",
    "mastery_scores": {}, "mastery_ready": False, "last_summary": "",
    "lang": "Chinese",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── 自动加载 Secrets ──────────────────────────────────────
# FIX: 加载成功后立即 rerun，确保状态在首次渲染后立即生效
if not st.session_state.key_confirmed:
    try:
        secrets_key = st.secrets["ANTHROPIC_API_KEY"]
        if secrets_key and secrets_key.startswith("sk-"):
            st.session_state.api_key = secrets_key
            st.session_state.key_confirmed = True
            st.rerun()
    except (KeyError, FileNotFoundError):
        pass

L = LANG_LABELS[st.session_state.lang]

# ── 侧边栏 ────────────────────────────────────────────────
with st.sidebar:
    st.title(L["config"])

    if st.button(L["lang_btn"], use_container_width=True):
        st.session_state.lang = "English" if st.session_state.lang == "Chinese" else "Chinese"
        st.rerun()

    st.divider()

    # 后端选择
    backend_label = st.selectbox(
        L["select_backend"], list(BACKENDS.keys()),
        index=list(BACKENDS.values()).index(st.session_state.backend))
    new_backend = BACKENDS[backend_label]
    if new_backend != st.session_state.backend:
        st.session_state.backend = new_backend
        st.session_state.key_confirmed = False
        st.session_state.api_key = ""
        st.session_state.messages = []
        if new_backend == "anthropic":
            try:
                secrets_key = st.secrets["ANTHROPIC_API_KEY"]
                if secrets_key and secrets_key.startswith("sk-"):
                    st.session_state.api_key = secrets_key
                    st.session_state.key_confirmed = True
            except (KeyError, FileNotFoundError):
                pass
        st.rerun()

    st.divider()

    # API Key 区域
    # FIX: 去掉 value= 参数，解决手机端退格键失效问题
    if st.session_state.backend == "ollama":
        st.info(L["ollama_notice"])
        st.session_state.key_confirmed = True
    elif st.session_state.key_confirmed:
        st.info(L["secrets_notice"])
    else:
        key_input = st.text_input(L["api_key"], type="password")
        if st.button(L["confirm_key"]):
            if key_input.startswith("sk-"):
                st.session_state.api_key = key_input
                st.session_state.key_confirmed = True
                st.success(L["key_ok"])
                st.rerun()
            else:
                st.error(L["key_err"])

    st.divider()

    # Unit / Concept 两级选择
    selected_unit = st.selectbox(
        L["select_unit"], list(UNITS.keys()),
        index=list(UNITS.keys()).index(st.session_state.curr_unit))
    selected_concept = st.selectbox(
        L["select_concept"], list(UNITS[selected_unit].keys()))
    if (selected_unit != st.session_state.curr_unit or
            selected_concept != st.session_state.curr_concept):
        st.session_state.curr_unit = selected_unit
        st.session_state.curr_concept = selected_concept
        st.session_state.messages = []
        st.session_state.last_summary = ""
        st.session_state.mastery_ready = False
        st.session_state.mastery_scores = {}
        st.rerun()

    st.divider()

    status_color = L["connected_color"] if st.session_state.key_confirmed else L["disconnected_color"]
    status_text  = L["connected"] if st.session_state.key_confirmed else L["disconnected"]
    st.markdown(
        f"<div style='background:{status_color};color:white;padding:12px;"
        f"border-radius:8px;text-align:center;font-size:16px;font-weight:bold;'>"
        f"{status_text}</div>",
        unsafe_allow_html=True
    )

    st.divider()
    show_test = st.checkbox(L["show_test"], value=False)

# ── 核心函数 ──────────────────────────────────────────────
def update_mastery(concept_id, response_text):
    scores = st.session_state.mastery_scores
    if concept_id not in scores:
        scores[concept_id] = 0
    if "[STATUS: CORRECT]" in response_text:
        scores[concept_id] += 1
    elif "[STATUS: INCORRECT]" in response_text or "[STATUS: PARTIAL]" in response_text:
        scores[concept_id] = 0
    if scores[concept_id] >= 3:
        st.session_state.mastery_ready = True

def generate_summary(concept_id):
    adapter = get_adapter()
    digest = "\n".join(
        f"{m['role'].upper()}: {m['content'][:200]}"
        for m in st.session_state.messages[-8:]
        if isinstance(m.get("content"), str)
    )
    L_local = LANG_LABELS[st.session_state.lang]
    prompt = (f"Based on this tutoring session for concept {concept_id}:\n{digest}\n"
              f"Generate a structured summary {L_local['summary_lang']}:\n"
              f"1. 核心法则 / Core Rule: [公式 / formula]\n"
              f"2. 关键步骤 / Key Steps: 1. [步骤] 2. [步骤] ...\n"
              f"3. ⚠️ 陷阱提示 / Pitfall: [本次学生实际犯的错误，一句话]")
    return adapter.chat("You are a helpful summarizer.",
                        [{"role": "user", "content": prompt}],
                        max_tokens=600)

def get_ai_response(extra_content=None):
    adapter = get_adapter()
    concept_id = UNITS[st.session_state.curr_unit][st.session_state.curr_concept]
    L_local = LANG_LABELS[st.session_state.lang]
    system_msg = (
        f"You are a strict AP Calculus Socratic tutor. {L_local['lang_instr']} "
        f"NEVER give the answer directly. Always guide with questions. "
        f"TEACHING CONSTRAINT: {CONCEPT_CONSTRAINTS.get(concept_id, 'Guide step by step.')} "
        f"\nRESPONSE FORMAT RULE: You MUST append exactly one of these tags "
        f"at the very end of every response, on its own line: "
        f"[STATUS: CORRECT], [STATUS: PARTIAL], [STATUS: INCORRECT], or [STATUS: GUIDING]. "
        f"No other text after the tag."
        f"\nSINGLE-PROBLEM RULE: Only work on ONE problem at a time. "
        f"If the student submits multiple problems (from chat, exercises, or external sources): "
        f"1. Acknowledge you see multiple problems. "
        f"2. List them briefly by number. "
        f"3. Ask: '你想先从哪道题开始？/ Which problem would you like to start with?' "
        f"4. Wait for the student's choice before proceeding. "
        f"Do NOT attempt to answer or guide any problem until the student selects exactly one. "
        f"If the student insists on multiple, politely redirect: one problem at a time is the rule."
    )
    msgs = [{"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
            if isinstance(m.get("content"), (str, list))]
    if extra_content:
        msgs.append({"role": "user", "content": extra_content})
    with st.spinner(L_local["spinner"]):
        reply = adapter.chat(system_msg, msgs)
        update_mastery(concept_id, reply)
        for tag in ["[STATUS: CORRECT]", "[STATUS: PARTIAL]",
                    "[STATUS: INCORRECT]", "[STATUS: GUIDING]"]:
            reply = reply.replace(tag, "")
        return reply.rstrip()

# ── 主界面 ────────────────────────────────────────────────
L = LANG_LABELS[st.session_state.lang]
st.title(f"{L['title_prefix']}: {st.session_state.curr_concept}")

if not st.session_state.key_confirmed:
    st.info(f"👈 {L['wait']}")
    st.stop()

# 测试面板
if show_test:
    st.subheader(L["test_panel"])
    test_input = st.text_area(L["test_input"], height=100,
                               placeholder=L["test_placeholder"])
    if st.button(L["test_send"]):
        if test_input.strip():
            st.session_state.messages.append({"role": "user", "content": test_input})
            with st.status(L["test_working"], expanded=True):
                response = get_ai_response()
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
        else:
            st.warning(L["test_empty"])
    st.divider()

# 初始出题
if not st.session_state.messages:
    concept_id = UNITS[st.session_state.curr_unit][st.session_state.curr_concept]
    key_en = concept_id + "_en"
    if st.session_state.lang == "Chinese":
        opening = OPENING_PROMPTS.get(
            concept_id,
            L["opening_default"].format(concept=st.session_state.curr_concept))
    else:
        opening = OPENING_PROMPTS.get(
            key_en,
            L["opening_default"].format(concept=st.session_state.curr_concept))
    first = get_ai_response(opening)
    st.session_state.messages.append({"role": "assistant", "content": first})
    st.rerun()

# 刷新按钮
if st.button(L["refresh"]):
    st.session_state.messages = []
    st.session_state.last_summary = ""
    st.session_state.mastery_ready = False
    st.session_state.mastery_scores = {}
    st.rerun()

# 消息渲染
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if isinstance(m["content"], str):
            st.markdown(m["content"])
        elif isinstance(m["content"], list):
            for b in m["content"]:
                if b.get("type") == "image":
                    st.image(base64.b64decode(b["source"]["data"]))
                else:
                    st.markdown(b.get("text", ""))

# 图片输入
with st.expander(L["upload"]):
    col1, col2 = st.columns(2)
    photo = col1.camera_input(L["camera"])
    uploaded = col2.file_uploader(L["gallery"], type=["jpg", "jpeg", "png"],
                                   accept_multiple_files=True)
    pending = [("image/jpeg", photo.read())] if photo else []
    for f in uploaded:
        mime = "image/png" if f.name.endswith(".png") else "image/jpeg"
        pending.append((mime, f.read()))
    if pending:
        st.write(f"{L['selected']} {len(pending)} {L['preview']}")
        cols = st.columns(len(pending))
        for i, (mime, data) in enumerate(pending):
            cols[i].image(data, width=120)
        if st.button(L["send_img"]):
            content = [{"type": "image", "source": {
                "type": "base64", "media_type": mime,
                "data": base64.b64encode(data).decode()
            }} for mime, data in pending]
            content.append({"type": "text", "text": L["img_prompt"]})
            st.session_state.messages.append({"role": "user", "content": content})
            response = get_ai_response()
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

# 文字输入
if prompt := st.chat_input(L["chat_input"]):
    st.session_state.messages.append({"role": "user", "content": prompt})
    response = get_ai_response()
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

# Mastery 总结
if st.session_state.mastery_ready:
    st.divider()
    st.success(L["mastery_msg"])
    if st.button(L["summary_btn"]):
        concept_id = UNITS[st.session_state.curr_unit][st.session_state.curr_concept]
        with st.spinner(L["generating"]):
            st.session_state.last_summary = generate_summary(concept_id)
        st.session_state.mastery_ready = False
        st.rerun()

if st.session_state.last_summary:
    with st.expander(L["summary_title"], expanded=True):
        st.markdown(st.session_state.last_summary)

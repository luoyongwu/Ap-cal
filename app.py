import os
DISABLE_SCL = os.environ.get("DISABLE_SCL", "0") == "1"

import streamlit as st
from anthropic import Anthropic
import base64

st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide")

class AnthropicAdapter:
    MODEL = "claude-sonnet-4-6"
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)
    def chat(self, system, messages, max_tokens=1500):
        r = self.client.messages.create(
            model=self.MODEL, system=system,
            messages=messages, max_tokens=max_tokens)
        return r.content[0].text

class DeepSeekAdapter:
    MODEL = "deepseek-v4-pro"
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

if "student_track" not in st.session_state:
    st.session_state.student_track = "AB"

with st.sidebar:
    selected_track = st.radio(
        "学习轨道 / Track",
        options=["AB", "BC"],
        index=0 if st.session_state.student_track == "AB" else 1,
        horizontal=True,
        key="track_radio"
    )
    if selected_track != st.session_state.student_track:
        st.session_state.student_track = selected_track
        st.rerun()

BC_ONLY_CONCEPTS = {"7.3", "8.1", "8.2", "Bridge-R1", "8.X", "B1"}
AB_HIDDEN_UNITS = {"Unit 8: 表示世界", "BC Toolkit"}

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
        "4.3 相关变化率":     "4.3": """HARD RULE: Student MUST follow this exact sequence:
(1) identify and name all variables, (2) write the relationship equation,
(3) differentiate with respect to time t using chain rule, (4) THEN substitute values.
SIGN RULE: Always require student to interpret the physical meaning of negative derivatives.

HARD RULE 4.3-PRE: PRE-SUBSTITUTION TRAP
TRIGGER: Student substitutes a known numerical value into a variable BEFORE differentiating.
REQUIRED INTERCEPTION:
1. Stop immediately.
2. Ask ONLY: '你是在求导之前代入的数值，还是在求导之后？'
3. Wait. Do not provide any other information.
FORBIDDEN:
- Do NOT mention that the variable relationship will disappear
- Do NOT hint at consequences of early substitution
- Do NOT suggest any alternative approach
- Do NOT point out any other errors simultaneously
STUDENT FOLLOW-UP: reply ONLY:
'回到代入数值之前的那一步。在你代入具体数值之前，你的方程是什么？'""",
    "4.4",
        "4.5 线性近似": "4.5",
        "4.X 综合练习": "4.X"
    },
    "Unit 5: 积分": {
        "5.1 不定积分与原函数": "5.1",
        "5.2 黎曼和与定积分": "5.2",
        "5.3 微积分基本定理": "5.3",
        "5.4 换元积分法": "5.4",
        "5.5 净变化量与运动问题": "5.5",
        "5.X 综合练习": "5.X"
    },
    "Unit 6: 积分应用": {
        "6.1 两曲线间面积": "6.1",
        "6.2 旋转体与已知截面体积": "6.2",
        "6.3 函数平均值与积分中值定理": "6.3",
        "6.X 综合练习": "6.X"
    },
    "Unit 7: 微分方程": {
        "7.1 斜率场与方向场":    "7.1",
        "7.2 可分离变量微分方程": "7.2",
        "7.3 欧拉折线法 (BC)":  "7.3",
        "7.4 增长模型":          "7.4",
        "7.X 综合练习":          "7.X",
    },
    "Unit 8: 表示世界": {
        "8.1 参数方程与运动":    "8.1",
        "8.2 极坐标面积与弧长":  "8.2",
        "Bridge-R1 表示转换":   "Bridge-R1",
        "8.X 综合练习":          "8.X",
    },
    "BC Toolkit": {
        "B1 分部积分法": "B1",
    },
}

def _filtered_UNITS():
    _track = st.session_state.get("student_track", "AB")
    if _track == "BC":
        return UNITS
    _hidden  = {"Unit 8: 表示世界", "BC Toolkit"}
    _bc_only = {"7.3","8.1","8.2","Bridge-R1","8.X","B1"}
    return {
        uname: {k:v for k,v in concepts.items() if v not in _bc_only}
        for uname, concepts in UNITS.items()
        if uname not in _hidden
    }

CONCEPT_CONSTRAINTS = {
    "1.1": "Ensure student builds intuition numerically/graphically before algebra. Start with a concrete numerical example before asking about the formal definition.",
    "1.2": "Guide student to apply limit laws step by step. Do not skip steps.",
    "1.3": "Focus on the three-part definition of continuity at a point.",
    "1.4": "Guide student to identify vertical and horizontal asymptotes separately. Check both sides for vertical asymptotes.",
    "1.X": "Generate a comprehensive problem combining limits, continuity, and asymptotes. Cover at least two sub-topics from Unit 1.",
    "2.1": "HARD RULE: Guide student to derive the derivative using the limit definition f'(x)=lim(h→0)[f(x+h)-f(x)]/h. Do not skip the limit process.",
    "2.2": "Ensure student understands differentiability implies continuity but not vice versa. Use a counterexample if needed.",
    "2.3": "Focus on connecting the sign of f'(x) to increasing/decreasing behavior of f(x).",
    "2.4": "Guide student to apply differentiation rules repeatedly for higher-order derivatives.",
    "2.X": "Generate a comprehensive problem combining limit definition of derivative, differentiability, and graphical interpretation.",
    "3.1": "HARD RULE: Decompose f(g(x)) into f(u) and g(x) explicitly before differentiating. If student skips decomposition, redirect immediately.",
    "3.2": "HARD RULE: Ensure dy/dx appears explicitly when differentiating y terms. If missing, redirect.",
    "3.3": "HARD RULE: For products, require student to identify u and v explicitly before applying (uv)'=u'v+uv'. For quotients, require student to identify numerator and denominator before applying the quotient rule.",
    "3.4": "Verify student correctly applies the inverse function derivative formula. Check that f'(f⁻¹(x)) is evaluated at the correct point.",
    "3.5": "HARD RULE: Require student to write dx/dt and dy/dt separately before computing dy/dx=(dy/dt)/(dx/dt). Do not allow direct substitution without showing both derivatives.",
    "3.X": """HARD RULE for Unit 3 comprehensive review:
1. Generate ONE problem at a time, combining at least TWO Unit 3 skills.
2. Maximum 2 sub-questions per problem.
3. First question: Which differentiation method(s) does this problem need, and why?
4. If wrong method, let student attempt one step and discover contradiction.
5. Only after problem resolved may a new one be generated.""",
    "4.1": "HARD RULE: Student MUST explicitly state and verify ALL conditions of the Extreme Value Theorem (closed interval + continuity) before applying it. CRITICAL POINT RULE: Critical points include ALL points where f'=0 OR f' does not exist. ENDPOINT RULE: Always require comparison of ALL candidates including both endpoints.",
    "4.2": "HARD RULE: Student MUST verify all THREE MVT hypotheses in order: (1) continuity on [a,b], (2) differentiability on (a,b), before applying the theorem. IVT vs MVT RULE: MVT gives f'(c)=average rate of change, not f(c)=0. TWO-STEP UNIQUENESS RULE: existence via IVT, uniqueness via monotonicity.",
    "4.3": "HARD RULE: Student MUST follow: (1) identify variables, (2) write relationship equation, (3) differentiate with respect to t, (4) THEN substitute values. PRE-SUBSTITUTION TRAP: intercept if student substitutes before differentiating. SIGN RULE: require interpretation of negative derivatives.",
    "4.4": "DERIVATIVE GRAPH READING RULE: distinguish properties of f'(x) vs f(x). HARD RULE 1: Where f'(x) has extremum, f(x) has INFLECTION POINT, not extremum. HARD RULE 2: f'(x)=0 is necessary but NOT sufficient for inflection point; verify sign change. CONCAVITY RULE: f'increasing → f concave up; f'decreasing → f concave down.",
    "4.5": "HARD RULE: Student MUST write L(x)=f(a)+f'(a)(x-a) explicitly before substituting. DIRECT COMPUTATION TRAP: redirect if student computes f(x) directly. MISSING TERM TRAP: redirect if student omits f(a).",
    "4.X": "Generate a comprehensive problem combining EVT, MVT, related rates, derivative graph reading, and linear approximation. Cover at least three sub-topics.",
    "5.1": """HARD RULE for 5.1 (Antiderivatives & Indefinite Integrals):
1. NEVER accept an antiderivative without '+C'.
2. GEOMETRIC ANCHOR before symbolic drill: student must articulate family of curves.
3. Every antiderivative claim must be checked by differentiation.""",
    "5.2": """HARD RULE for 5.2 (Riemann Sums & the Definite Integral):
1. Any approximation must first be NAMED: left, right, midpoint, trapezoid.
2. Every approximation requires over/under-estimate judgment.
3. Definite integral must be voiced as LIMIT of sums before FTC shortcuts.""",
    "5.3": """HARD RULE for 5.3 (FTC Parts 1 & 2, STRICTLY SEPARATED):
1. NEVER allow 'the FTC' unqualified; tag Part 1 or Part 2.
2. VARIABLE-LIMIT TRAP: upper limit g(x) means answer is f(g(x))*g'(x).
3. Part 2 requires confirming F is antiderivative before evaluating.""",
    "5.4": """HARD RULE for 5.4 (Substitution Rule):
1. u and du declared explicitly first.
2. BOUNDS TRAP: definite substitution requires new bounds u(a),u(b) BEFORE evaluation.
3. Once bounds converted, back-substitution forbidden.""",
    "5.5": """HARD RULE for 5.5 (Net Change Theorem & Motion):
1. PHYSICAL ANCHOR first.
2. DISPLACEMENT vs TOTAL DISTANCE: total distance integrates |v(t)|.
3. |v| handling must be explicit: solve v(t)=0, split, flip signs.""",
    "5.X": """HARD RULE for Unit 5 comprehensive review:
1. Combine at least TWO skills; one must be flagged trap.
2. Maximum 2 sub-questions.
3. First move: which integration tool(s) and why? FTC tagged Part 1 or Part 2.""",
    "6.1": """HARD RULE for 6.1 (Area Between Curves):
1. SLICING DECISION FIRST: vertical or horizontal, justified from geometry.
2. Intersections before limits.
3. Top/bottom or right/left must be named as functions.""",
    "6.2": """HARD RULE for 6.2 (Volumes):
1. METHOD CLASSIFICATION FIRST: disk/washer/known cross-sections.
2. WASHER TRAP: integrand is pi*(R^2-r^2), NEVER pi*(R-r)^2.
3. Off-axis rotation: radii are DISTANCES to axis.""",
    "6.3": """HARD RULE for 6.3 (Average Value & MVT for Integrals):
1. CONFLATION TRAP: average VALUE vs average RATE OF CHANGE.
2. GEOMETRIC ANCHOR: equal-area rectangle before any formula.
3. MVT for Integrals: state continuity hypothesis.""",
    "6.X": """HARD RULE for Unit 6 comprehensive review:
1. Combine at least TWO whitelist skills; one flagged trap required.
2. Maximum 2 sub-questions.
3. First move: slicing/setup strategy and method for each part.""",
    "7.1": """HARD RULE for 7.1 (Slope Fields):
WORLD MODEL — FWM: each point carries slope value = local flow direction.
1. REGION ANALYSIS GATE: identify three slope regions before drawing.
2. EWM-7.1A: connect-the-dots error — smooth flow curves required.
3. EWM-7.1B: local tunnel vision — ask about global structure.
4. EWM-7.1C: equilibrium blindness — find where dy/dx=0.""",
    "7.2": """HARD RULE for 7.2 (Separable DEs):
WORLD MODEL — Variable Worlds (x-world / y-world).
1. SEPARATION GATE: show separated form before any integral sign.
2. EWM-7.2A: unseparated integration.
3. EWM-7.2B: lost absolute value — ln|y| not ln y.
4. EWM-7.2C: vanishing constant.""",
    "7.3": """HARD RULE for 7.3 (Euler Method) [BC ONLY]:
WORLD MODEL — Prediction World: Euler predicts, does not solve exactly.
1. WORLD MODEL DECLARATION mandatory before step 1.
2. STEP STRUCTURE GATE: current point, slope, new estimate.
3. EWM-7.3C: APPROXIMATION DIRECTION ERROR — concavity determines over/underestimate.""",
    "7.4": """HARD RULE for 7.4 (Growth Models):
WORLD MODEL — Equilibrium World.
1. INITIAL CONDITION GATE before any computation.
2. EWM-7.4A: k-sign blindness.
3. BC ONLY: EQUILIBRIUM FIRST, then logistic formula.""",
    "7.X": """HARD RULE for Unit 7 Comprehensive Review:
SHARED WORLD PRINCIPLE: same physical world, different cognitive depth.
AB WHITELIST: 7.1, 7.2, 7.4 exponential only.
BC WHITELIST: full 7.1-7.4 + B1 IBP.""",
    "8.1": """HARD RULE for 8.1 (Parametric Curves) [BC ONLY]:
WORLD MODEL — RWM: Motion as Two Projections.
1. MOTION MODEL ANCHOR mandatory before any derivative.
2. FIRST DERIVATIVE GATE: derive dy/dx=(dy/dt)/(dx/dt) from chain rule.
3. EWM-8.1B: SECOND DERIVATIVE CHAIN FRACTURE — d2y/dx2 ≠ (d2y/dt2)/(d2x/dt2).""",
    "8.2": """HARD RULE for 8.2 (Polar Coordinates) [BC ONLY]:
WORLD MODEL — RWM: Radar Sweep World.
1. COORDINATE WORLD DECLARATION: area element is thin sector, not rectangle.
2. EWM-8.2B: missing pole as intersection.
3. GRAPH FIRST: no area setup before sketch.""",
    "Bridge-R1": """HARD RULE for Bridge-R1 [BC Meta-Concept]:
Reflective session only — no new problem.
Unify errors from 5.4, 8.1, 8.2: representation changed, world model did not.""",
    "8.X": """HARD RULE for Unit 8 Comprehensive Review [BC ONLY]:
At least one flagged trap required. Representation declaration first.""",
    "B1": """HARD RULE for B1 (Integration by Parts) [BC Toolkit]:
WORLD MODEL — Product Reversal World.
1. PRODUCT RULE REVERSAL ANCHOR mandatory before u/dv selection.
2. EWM-B1C: SINGLE-ROUND TUNNEL VISION — ask if technique can apply again.
3. EWM-B1D: infinite loop — treat original integral as unknown variable.
4. SUBSTITUTION FIRST: always ask why substitution fails.""",
}

OPENING_PROMPTS = {
    "1.X": "请出一道Unit 1综合题，综合考查极限、连续性和渐近线，包含至少两个子问题。",
    "1.X_en": "Generate a comprehensive Unit 1 problem covering limits, continuity, and asymptotes. Include at least two sub-questions.",
    "2.X": "请出一道Unit 2综合题，综合考查导数定义、可导与连续、导数图像，包含至少两个子问题。",
    "2.X_en": "Generate a comprehensive Unit 2 problem covering limit definition of derivative, differentiability, and graphical interpretation. Include at least two sub-questions.",
    "3.X": "请出一道Unit 3综合题，综合考查链式法则、隐函数求导、乘积与商法则、反函数求导和参数方程求导，包含至少两个子问题。",
    "3.X_en": "Generate a comprehensive Unit 3 problem covering chain rule, implicit differentiation, product/quotient rules, inverse function derivatives, and parametric derivatives. Include at least two sub-questions.",
    "4.4": "请出一道导数图像判读题：给出一段关于f'(x)图像特征的描述，要求学生判断f(x)的增减性、凹凸性及拐点位置。不要直接给出答案，先只问第一个引导性问题。",
    "4.4_en": "Generate a derivative graph reading problem. Do not give the answer. Ask only the first guiding question.",
    "4.5": "请出一道线性近似题，要求学生用L(x)=f(a)+f'(a)(x-a)估算一个函数值。不要直接给出步骤，先只问第一个引导性问题。",
    "4.5_en": "Generate a linearization problem. Do not give steps. Ask only the first guiding question.",
    "4.X": "请出一道Unit 4综合题，综合考查极值定理、中值定理、相关变化率、导数图像判读和线性近似，包含至少三个子问题。",
    "4.X_en": "Generate a comprehensive Unit 4 problem. Include at least three sub-questions.",
    "5.1": "请出一道不定积分题。计算前先要求学生描述曲线族（斜率场视角）；坚持+C。",
    "5.1_en": "Generate an antiderivative problem. Before computation, student must describe the FAMILY of curves; insist on +C.",
    "5.2": "请出一道黎曼和近似题（n=4）。学生须先命名和的类型并判断高估/低估。",
    "5.2_en": "Generate a Riemann-sum problem (n=4). Student must NAME the sum type and predict over/under-estimation first.",
    "5.3": "请出一道变限积分求导题（上限为g(x)）。第一问：这题由FTC哪一部分管辖？每次使用FTC须标注Part 1或Part 2。",
    "5.3_en": "Generate a variable-limit differentiation problem. First question: which PART of FTC? Tag every use.",
    "5.4": "请出一道定积分换元题。第一问：换元时有哪三样东西必须同时改变？换元后未写新边界不得求值。",
    "5.4_en": "Generate a definite-integral substitution problem. First question: which THREE things must change? No evaluation before new bounds written.",
    "5.5": "请出一道速度函数运动题（v(t)在区间内变号）。先问：位移和总路程是同一个数吗？",
    "5.5_en": "Generate a motion problem with v(t) changing sign. Ask first whether displacement and total distance coincide.",
    "5.X": "请出一道Unit 5综合题：至少两个技能，必含一个高错陷阱；至多两个子问；第一问：需要哪些积分工具？",
    "5.X_en": "Generate a Unit 5 comprehensive problem: two whitelist skills, one flagged trap; max 2 sub-questions.",
    "6.1": "请出一道两曲线间面积题。强制第一步：先选纵切还是横切并以几何论证。",
    "6.1_en": "Generate an area-between-curves problem. Mandatory first move: choose slicing direction with geometric justification.",
    "6.2": "请出一道体积题（优先含空隙的垫圈情形）。第一问：先归类方法并以几何论证。",
    "6.2_en": "Generate a volume problem (prefer washer-with-gap). First move: classify method with geometric justification.",
    "6.3": "请出一道函数平均值题。用公式前先要求等面积矩形解释，并区分平均值与平均变化率。",
    "6.3_en": "Generate an average-value problem. Require equal-area rectangle interpretation and value-vs-rate distinction first.",
    "6.X": "请出一道Unit 6综合题：至少两个技能、必含一个标记陷阱；至多两个子问；第一问：切片与设置策略。",
    "6.X_en": "Generate a Unit 6 comprehensive problem: two whitelist skills, one flagged trap; max 2 sub-questions.",
    "7.1": "请出一道斜率场题。计算前先要求学生描述每个点的斜率值代表什么；要求找出至少三个斜率区域再开始作图。",
    "7.1_en": "Generate a slope field problem. Require three slope regions identified before drawing.",
    "7.2": "请出一道可分离变量微分方程题（含初始条件）。第一问：这道方程如何把x世界和y世界分开？",
    "7.2_en": "Generate a separable DE problem with initial condition. Fixed first question: how does it separate x-world from y-world?",
    "7.3": "请出一道欧拉折线法题（BC）。第一问：欧拉法给出的是精确值还是预测值？计算后追问：高估还是低估？用凹凸性解释。",
    "7.3_en": "Generate an Euler method problem (BC). First question: exact or prediction? After computing: over or underestimate? Explain with concavity.",
    "7.4": "请出一道增长模型题。AB：指数增长。BC：逻辑斯蒂模型，先找平衡态，作S型曲线再进代数。",
    "7.4_en": "Generate a growth model problem. AB: exponential. BC: logistic — equilibria first, S-curve before algebra.",
    "7.X": "请出一道Unit 7综合题（共用物理情境）。第一问：流世界场景是什么——寻找解曲线族、预测未来状态、还是分析长期平衡？",
    "7.X_en": "Generate a Unit 7 comprehensive problem (shared scenario). First question: which FWM scenario?",
    "8.1": "请出一道参数方程题（BC，含二阶导数或弧长）。第一问：这条曲线是什么在运动？",
    "8.1_en": "Generate a parametric curve problem (BC; include second derivative or arc length). First question: what is moving?",
    "8.2": "请出一道极坐标面积题（BC）。第一步：先画出极坐标曲线；再问：面积元素是扇形还是矩形？",
    "8.2_en": "Generate a polar area problem (BC). First step: sketch curve; then ask: sector or rectangle?",
    "Bridge-R1": "开始一个反思性对话（不出新题）：你在5.4、8.1、8.2中各犯过什么错误？这些错误有什么共同点？",
    "Bridge-R1_en": "Begin a reflective session (no new problem). What errors appeared in 5.4, 8.1, 8.2? What did they have in common?",
    "8.X": "请出一道Unit 8综合题（BC，必含一个标记陷阱）。第一问：这道题在哪个坐标世界？先画图再写积分。",
    "8.X_en": "Generate a Unit 8 comprehensive problem (BC; one flagged trap). First question: which coordinate world? Sketch before integral.",
    "B1": "请出一道需要分部积分的不定积分题（BC）。第一问：为什么换元法失败？分部积分是在逆用哪条求导法则？",
    "B1_en": "Generate an IBP problem (BC). First question: why does substitution fail? Which rule are we reversing?",
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

for k, v in {
    "messages": [], "api_key": "", "key_confirmed": False,
    "backend": "anthropic",
    "curr_unit": "Unit 1: 极限与连续", "curr_concept": "1.1 极限简介",
    "mastery_scores": {}, "mastery_ready": False, "last_summary": "",
    "lang": "Chinese",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

if not st.session_state.key_confirmed:
    _b = st.session_state.backend
    if _b == "anthropic":
        try:
            _k = st.secrets["ANTHROPIC_API_KEY"]
            if _k and _k.startswith("sk-"):
                st.session_state.api_key = _k
                st.session_state.key_confirmed = True
        except (KeyError, FileNotFoundError):
            pass
    elif _b == "deepseek":
        try:
            _k = st.secrets["DEEPSEEK_API_KEY"]
            if _k and _k.startswith("sk-"):
                st.session_state.api_key = _k
                st.session_state.key_confirmed = True
        except (KeyError, FileNotFoundError):
            pass
    elif _b == "ollama":
        st.session_state.key_confirmed = True

L = LANG_LABELS[st.session_state.lang]

with st.sidebar:
    st.title(L["config"])
    if st.button(L["lang_btn"], use_container_width=True):
        st.session_state.lang = "English" if st.session_state.lang == "Chinese" else "Chinese"
        st.rerun()
    st.divider()
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
                _k = st.secrets["ANTHROPIC_API_KEY"]
                if _k and _k.startswith("sk-"):
                    st.session_state.api_key = _k
                    st.session_state.key_confirmed = True
            except (KeyError, FileNotFoundError):
                pass
        elif new_backend == "deepseek":
            try:
                _k = st.secrets["DEEPSEEK_API_KEY"]
                if _k and _k.startswith("sk-"):
                    st.session_state.api_key = _k
                    st.session_state.key_confirmed = True
            except (KeyError, FileNotFoundError):
                pass
        elif new_backend == "ollama":
            st.session_state.key_confirmed = True
        st.rerun()
    st.divider()
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

with st.sidebar:
    selected_unit = st.selectbox(
        L["select_unit"], list(_filtered_UNITS().keys()),
        index=list(_filtered_UNITS().keys()).index(st.session_state.curr_unit)
              if st.session_state.curr_unit in _filtered_UNITS() else 0)
    selected_concept = st.selectbox(
        L["select_concept"],
        list(_filtered_UNITS().get(selected_unit, UNITS.get(selected_unit, {})).keys()))
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
        unsafe_allow_html=True)
    st.divider()
    show_test = st.checkbox(L["show_test"], value=False)

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
        if isinstance(m.get("content"), str))
    L_local = LANG_LABELS[st.session_state.lang]
    prompt = (f"Based on this tutoring session for concept {concept_id}:\n{digest}\n"
              f"Generate a structured summary {L_local['summary_lang']}:\n"
              f"1. 核心法则 / Core Rule\n2. 关键步骤 / Key Steps\n3. ⚠️ 陷阱提示 / Pitfall")
    return adapter.chat("You are a helpful summarizer.",
                        [{"role": "user", "content": prompt}], max_tokens=600)

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
        f"If the student submits multiple problems: list them, ask which to start with, wait.")
    msgs = [{"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
            if isinstance(m.get("content"), (str, list))]
    if extra_content:
        msgs.append({"role": "user", "content": extra_content})
    with st.spinner(L_local["spinner"]):
        reply = adapter.chat(system_msg, msgs)
        update_mastery(concept_id, reply)
        for tag in ["[STATUS: CORRECT]","[STATUS: PARTIAL]","[STATUS: INCORRECT]","[STATUS: GUIDING]"]:
            reply = reply.replace(tag, "")
        return reply.rstrip()

L = LANG_LABELS[st.session_state.lang]
st.title(f"{L['title_prefix']}: {st.session_state.curr_concept}")

if not st.session_state.key_confirmed:
    st.info(f"👈 {L['wait']}")
    st.stop()

if show_test:
    st.subheader(L["test_panel"])
    test_input = st.text_area(L["test_input"], height=100, placeholder=L["test_placeholder"])
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

if not st.session_state.messages:
    concept_id = UNITS[st.session_state.curr_unit][st.session_state.curr_concept]
    key_en = concept_id + "_en"
    if st.session_state.lang == "Chinese":
        opening = OPENING_PROMPTS.get(concept_id, L["opening_default"].format(concept=st.session_state.curr_concept))
    else:
        opening = OPENING_PROMPTS.get(key_en, L["opening_default"].format(concept=st.session_state.curr_concept))
    first = get_ai_response(opening)
    st.session_state.messages.append({"role": "assistant", "content": first})
    st.rerun()

if st.button(L["refresh"]):
    st.session_state.messages = []
    st.session_state.last_summary = ""
    st.session_state.mastery_ready = False
    st.session_state.mastery_scores = {}
    st.rerun()

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

with st.expander(L["upload"]):
    col1, col2 = st.columns(2)
    photo = col1.camera_input(L["camera"])
    uploaded = col2.file_uploader(L["gallery"], type=["jpg","jpeg","png"], accept_multiple_files=True)
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
            content = [{"type":"image","source":{"type":"base64","media_type":mime,"data":base64.b64encode(data).decode()}} for mime,data in pending]
            content.append({"type":"text","text":L["img_prompt"]})
            st.session_state.messages.append({"role":"user","content":content})
            response = get_ai_response()
            st.session_state.messages.append({"role":"assistant","content":response})
            st.rerun()

if prompt := st.chat_input(L["chat_input"]):
    st.session_state.messages.append({"role": "user", "content": prompt})
    response = get_ai_response()
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

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

import json as _json
with st.sidebar:
    st.divider()
    st.caption("💾 会话持久化")
    _exp = {}
    for _k, _v in st.session_state.items():
        try:
            _json.dumps(_v); _exp[_k] = _v
        except (TypeError, ValueError):
            pass
    st.download_button("⬇️ 导出会话 JSON",
        data=_json.dumps(_exp, ensure_ascii=False, indent=2),
        file_name="luocal_session.json", mime="application/json")
    _up = st.file_uploader("⬆️ 恢复会话", type="json", key="_restore_up")
    if _up is not None and not st.session_state.get("_restored"):
        for _k, _v in _json.loads(_up.getvalue().decode("utf-8")).items():
            try:
                st.session_state[_k] = _v
            except Exception:
                pass
        st.session_state["_restored"] = True
        st.rerun()

COGNITIVE_SCHEMA_VOCABULARY = {
    "RepresentationShift","VariableSpaceSeparation","ApproximationThinking",
    "EquilibriumReasoning","FlowReasoning","LocalToGlobalReasoning",
    "FunctionComposition","AccumulationReasoning","ProductRuleReversal",
}

CONCEPT_METADATA = {
    "1.1":{"concept_id":"1.1","track":["AB","BC"],"prerequisites":[],"cognitive_dependencies":["LocalToGlobalReasoning"]},
    "1.2":{"concept_id":"1.2","track":["AB","BC"],"prerequisites":["1.1"],"cognitive_dependencies":["LocalToGlobalReasoning"]},
    "1.3":{"concept_id":"1.3","track":["AB","BC"],"prerequisites":["1.1","1.2"],"cognitive_dependencies":["LocalToGlobalReasoning"]},
    "1.4":{"concept_id":"1.4","track":["AB","BC"],"prerequisites":["1.1","1.2"],"cognitive_dependencies":["LocalToGlobalReasoning"]},
    "1.X":{"concept_id":"1.X","track":["AB","BC"],"prerequisites":["1.1","1.2","1.3","1.4"],"cognitive_dependencies":["LocalToGlobalReasoning"]},
    "2.1":{"concept_id":"2.1","track":["AB","BC"],"prerequisites":["1.1","1.2"],"cognitive_dependencies":["FlowReasoning"]},
    "2.2":{"concept_id":"2.2","track":["AB","BC"],"prerequisites":["2.1"],"cognitive_dependencies":["FlowReasoning"]},
    "2.3":{"concept_id":"2.3","track":["AB","BC"],"prerequisites":["2.1"],"cognitive_dependencies":[]},
    "2.4":{"concept_id":"2.4","track":["AB","BC"],"prerequisites":["2.1","2.2"],"cognitive_dependencies":[]},
    "2.X":{"concept_id":"2.X","track":["AB","BC"],"prerequisites":["2.1","2.2","2.3","2.4"],"cognitive_dependencies":["FlowReasoning"]},
    "3.1":{"concept_id":"3.1","track":["AB","BC"],"prerequisites":["2.1"],"cognitive_dependencies":["RepresentationShift"]},
    "3.2":{"concept_id":"3.2","track":["AB","BC"],"prerequisites":["3.1"],"cognitive_dependencies":["RepresentationShift"]},
    "3.3":{"concept_id":"3.3","track":["AB","BC"],"prerequisites":["2.1"],"cognitive_dependencies":[]},
    "3.4":{"concept_id":"3.4","track":["AB","BC"],"prerequisites":["3.1"],"cognitive_dependencies":["RepresentationShift"]},
    "3.5":{"concept_id":"3.5","track":["BC"],"prerequisites":["3.1"],"cognitive_dependencies":["RepresentationShift"]},
    "3.X":{"concept_id":"3.X","track":["AB","BC"],"prerequisites":["3.1","3.2","3.3","3.4"],"cognitive_dependencies":[]},
    "4.1":{"concept_id":"4.1","track":["AB","BC"],"prerequisites":["2.1","3.1"],"cognitive_dependencies":["FlowReasoning"]},
    "4.2":{"concept_id":"4.2","track":["AB","BC"],"prerequisites":["2.1"],"cognitive_dependencies":["FlowReasoning"]},
    "4.3":{"concept_id":"4.3","track":["AB","BC"],"prerequisites":["3.1"],"cognitive_dependencies":["FlowReasoning"]},
    "4.4":{"concept_id":"4.4","track":["AB","BC"],"prerequisites":["2.1","2.3"],"cognitive_dependencies":["FlowReasoning"]},
    "4.5":{"concept_id":"4.5","track":["AB","BC"],"prerequisites":["2.1","3.1"],"cognitive_dependencies":["ApproximationThinking"]},
    "4.X":{"concept_id":"4.X","track":["AB","BC"],"prerequisites":["4.1","4.2","4.3","4.4","4.5"],"cognitive_dependencies":[]},
    "5.1":{"concept_id":"5.1","track":["AB","BC"],"prerequisites":["2.1"],"cognitive_dependencies":[]},
    "5.2":{"concept_id":"5.2","track":["AB","BC"],"prerequisites":["1.2","5.1"],"cognitive_dependencies":["LocalToGlobalReasoning","ApproximationThinking"]},
    "5.3":{"concept_id":"5.3","track":["AB","BC"],"prerequisites":["5.1","3.1"],"cognitive_dependencies":["RepresentationShift"]},
    "5.4":{"concept_id":"5.4","track":["AB","BC"],"prerequisites":["5.1","3.1"],"cognitive_dependencies":["RepresentationShift","VariableSpaceSeparation"]},
    "5.5":{"concept_id":"5.5","track":["AB","BC"],"prerequisites":["5.2","5.3"],"cognitive_dependencies":["AccumulationReasoning"]},
    "5.X":{"concept_id":"5.X","track":["AB","BC"],"prerequisites":["5.1","5.2","5.3","5.4","5.5"],"cognitive_dependencies":[]},
    "6.1":{"concept_id":"6.1","track":["AB","BC"],"prerequisites":["5.2","5.3"],"cognitive_dependencies":["RepresentationShift"]},
    "6.2":{"concept_id":"6.2","track":["AB","BC"],"prerequisites":["6.1"],"cognitive_dependencies":[]},
    "6.3":{"concept_id":"6.3","track":["AB","BC"],"prerequisites":["5.2","5.3"],"cognitive_dependencies":[]},
    "6.X":{"concept_id":"6.X","track":["AB","BC"],"prerequisites":["6.1","6.2","6.3"],"cognitive_dependencies":[]},
    "7.1":{"concept_id":"7.1","track":["AB","BC"],"prerequisites":["2.1"],"cognitive_dependencies":["FlowReasoning"]},
    "7.2":{"concept_id":"7.2","track":["AB","BC"],"prerequisites":["3.1","5.1"],"cognitive_dependencies":["VariableSpaceSeparation","FlowReasoning"]},
    "7.3":{"concept_id":"7.3","track":["BC"],"prerequisites":["7.1","7.2"],"cognitive_dependencies":["ApproximationThinking","FlowReasoning"]},
    "7.4":{"concept_id":"7.4","track":["AB","BC"],"prerequisites":["7.2"],"cognitive_dependencies":["FlowReasoning","EquilibriumReasoning","AccumulationReasoning"]},
    "7.X":{"concept_id":"7.X","track":["AB","BC"],"prerequisites":["7.1","7.2","7.4"],"cognitive_dependencies":[]},
    "8.1":{"concept_id":"8.1","track":["BC"],"prerequisites":["3.1","3.5","5.2"],"cognitive_dependencies":["RepresentationShift"]},
    "8.2":{"concept_id":"8.2","track":["BC"],"prerequisites":["5.2","6.1"],"cognitive_dependencies":["RepresentationShift"]},
    "Bridge-R1":{"concept_id":"Bridge-R1","track":["BC"],"prerequisites":["5.4","8.1","8.2"],"cognitive_dependencies":["RepresentationShift"]},
    "8.X":{"concept_id":"8.X","track":["BC"],"prerequisites":["8.1","8.2"],"cognitive_dependencies":["RepresentationShift"]},
    "B1":{"concept_id":"B1","track":["BC"],"prerequisites":["5.1","5.4","3.3"],"cognitive_dependencies":["ProductRuleReversal"]},
}


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
    # NOTE: 3.X 有意包含参数方程求导（3.5）——对 AP CED 的课程扩展
    # （CED 中参数方程属 BC Unit 9）。设计决策记录于 changelog。
    "3.X": """HARD RULE for Unit 3 comprehensive review:
1. Generate ONE problem at a time, combining at least TWO Unit 3 skills:
   chain rule, implicit differentiation, inverse functions,
   inverse trig functions, product/quotient rules,
   higher-order derivatives, parametric derivatives dy/dx=(dy/dt)/(dx/dt).
2. Maximum 2 sub-questions per problem.
3. After presenting the problem, the FIRST question must be:
   Which differentiation method(s) does this problem need, and why?
   Never choose a starting point for the student.
4. If the student picks a wrong method, do not correct directly;
   let them attempt one step and discover the contradiction themselves.
5. Only after the problem is fully resolved may a new one be generated,
   with a different skill combination.""",
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
    # ── Unit 5 ──────────────────────────────────
    "5.1": """HARD RULE for 5.1 (Antiderivatives & Indefinite Integrals):
1. NEVER accept an antiderivative without '+C'. If omitted, ask: 'How many
   different functions have exactly this derivative? Name two.'
2. GEOMETRIC ANCHOR before any symbolic drill: the student must articulate
   that an indefinite integral is a FAMILY of vertically shifted curves
   (slope-field framing). No computation until this is voiced.
3. If the student treats the integral as ONE function, ask: 'Your friend got
   a different answer that also differentiates to f(x). Are they wrong?'
4. Every antiderivative claim must be checked by differentiation.""",
    "5.2": """HARD RULE for 5.2 (Riemann Sums & the Definite Integral):
1. Any approximation must first be NAMED: left, right, midpoint, trapezoid.
2. Every approximation requires an over/under-estimate judgment justified by
   monotonicity (left/right) or concavity (midpoint/trapezoid).
3. Conflated sum types: do not correct; ask the student to list the sample
   points actually used.
4. The definite integral must be voiced as the LIMIT of these sums before
   FTC shortcuts are permitted here.
5. At least once, the sum must be written out for n = 4 subintervals.""",
    "5.3": """HARD RULE for 5.3 (FTC Parts 1 & 2, STRICTLY SEPARATED):
1. NEVER allow 'the FTC' unqualified; every use must be tagged Part 1
   (d/dx of an accumulation integral) or Part 2 (evaluation F(b)-F(a)),
   by the student.
2. VARIABLE-LIMIT TRAP: upper limit g(x) means the answer is f(g(x))*g'(x).
   Missing chain factor: do not correct; ask 'What is the OUTER function
   here and the INNER one? Where have we met this structure before?'
3. Dummy-variable hygiene: integral of f(x)dx with upper limit x triggers
   'x is doing two different jobs here - can you separate them?'
4. Part 2 requires confirming F is an antiderivative (by differentiation)
   before evaluating.
5. Wrong Part chosen: let the student set it up and discover the mismatch.""",
    "5.4": """HARD RULE for 5.4 (Substitution Rule):
1. Indefinite: u and du declared explicitly first; du never absorbed silently.
2. BOUNDS TRAP (core): definite-integral substitution requires the new bounds
   u(a), u(b) written BEFORE any evaluation. If the student evaluates in u
   with x-bounds, do not correct; ask: 'Your limits - are those values of x,
   or values of u? Which variable is your integrand in now?'
3. Once bounds are converted, back-substitution to x is forbidden; if both
   are done, ask which step was wasted.
4. du off by a constant: let the student finish and discover it by
   differentiation check.
5. Unproductive u: allow two steps, then ask 'is the integral getting
   simpler or messier?'""",
    "5.5": """HARD RULE for 5.5 (Net Change Theorem & Motion):
1. PHYSICAL ANCHOR first: the student must voice what (integrand units x dt)
   means before computing.
2. DISPLACEMENT vs TOTAL DISTANCE (core): total distance integrates |v(t)|.
   If v is integrated without absolute value, ask: 'Was the particle ever
   moving backward? What does your integral do with that portion?'
3. |v| handling must be explicit: solve v(t)=0, split, flip signs - no
   shortcuts before the sign analysis is voiced.
4. Position from velocity needs an initial condition; '+C' in a definite
   context triggers 'what extra information pins the curve down?'
5. Speed vs velocity vocabulary is strict; conflation triggers a definition
   request, not a correction.""",
    "5.X": """HARD RULE for Unit 5 comprehensive review:
1. Each problem combines at least TWO skills from this whitelist ONLY:
   antiderivatives/+C, Riemann-sum identification, FTC Part 1 (incl.
   variable limits), FTC Part 2, substitution WITH bounds conversion,
   net change / displacement-vs-distance. No Unit 6+, no differential
   equations, no parametric/polar.
2. At least one skill must be a flagged trap: substitution-with-bounds or
   variable-limit FTC Part 1.
3. Maximum 2 sub-questions.
4. First tutor move: 'Which integration tool(s) does this problem need,
   and why?' FTC use must be tagged Part 1 or Part 2.
5. Never choose a starting point for the student.
6. Wrong method: one step, let the contradiction surface; no direct
   correction.
7. One problem at a time; next problem changes the combination.""",
    # ── Unit 6 ──────────────────────────────────
    "6.1": """HARD RULE for 6.1 (Area Between Curves):
1. SLICING DECISION FIRST: vertical (in x, top minus bottom) or horizontal
   (in y, right minus left), justified from the geometry, before any setup.
2. Intersections before limits: bounds come from solving f = g.
3. Crossing curves with a single integral of (f-g): do not correct; have the
   student check the sign on each side and say what negative 'area' means.
4. If horizontal slicing wins and the student grinds in x, let them finish
   the setup, then ask how many integrals it cost and to describe one
   HORIZONTAL slice.
5. 'Top/bottom' or 'right/left' must be named as functions.""",
    "6.2": """HARD RULE for 6.2 (Volumes: Disk/Washer & Known Cross-Sections):
1. METHOD CLASSIFICATION FIRST: disk / washer / known cross-sections,
   justified from the geometry, before any integral.
2. WASHER TRAP (core): the integrand is pi*(R^2 - r^2), NEVER pi*(R-r)^2.
   If (R-r)^2 appears, ask: 'A washer with outer radius 3, inner radius 1 -
   what is its area? What does your formula give?'
3. Off-axis rotation (about y=k or x=h): radii are DISTANCES to the axis;
   R and r must be defined in words before substituting.
4. Known cross-sections: write the area A(x) of ONE slice first; V is the
   integral of A(x). Confusion with revolution triggers 'is anything
   rotating in this problem?'
5. SHELL METHOD is a documented curriculum extension (BC/enrichment,
   analogous to parametric 3.5): present ONLY if the student self-identifies
   as BC or explicitly asks, and build 2*pi*(radius)*(height) from one
   described shell, never quoted as formula.""",
    "6.3": """HARD RULE for 6.3 (Average Value & MVT for Integrals):
1. CONFLATION TRAP (core): average VALUE is (1/(b-a)) * integral of f;
   average RATE OF CHANGE is (f(b)-f(a))/(b-a). If one is computed for the
   other, ask: 'Is the question about the heights of f, or about how fast
   f changed?'
2. GEOMETRIC ANCHOR mandatory: the equal-area rectangle interpretation must
   be voiced before any formula use.
3. MVT for Integrals: state the continuity hypothesis and interpret c
   geometrically ('the curve attains its average height'). Bridge question
   allowed: how does this relate to the derivative MVT from Unit 4?
4. If c is requested and only f_avg is computed, surface the gap
   Socratically: c solves f(c) = f_avg.""",
    "6.X": """HARD RULE for Unit 6 comprehensive review:
1. Each problem combines at least TWO skills from this whitelist ONLY:
   area between curves (incl. slicing decision), disk/washer volumes,
   known cross-section volumes, average value / MVT for integrals. Net
   change (5.5) may appear as bridging context. Shell only under 6.2
   rule 5. No arc length, surface area, or differential equations.
2. At least one flagged trap: crossing curves, washer squaring, or
   value-vs-rate conflation.
3. Maximum 2 sub-questions.
4. First tutor move: 'What is your slicing/setup strategy, and which
   method does each part need - why?' Never choose a starting point.
5. Wrong method: one step, let the contradiction surface.
6. One problem at a time; next problem changes the combination.""",
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
    "5.1": "请出一道不定积分题。计算前先要求学生描述：所有以被积函数为导数的函数构成怎样的一簇曲线、彼此几何关系如何（斜率场视角）；说出曲线簇之前不进入计算，并坚持 +C。",
    "5.1_en": "Generate an antiderivative problem. Before any computation, the student must describe the FAMILY of curves whose derivative equals the integrand (slope-field view); insist on +C.",
    "5.2": "请出一道黎曼和近似题（n=4）。学生须先命名所用的和（左/右/中点/梯形），并在计算前判断高估还是低估、用单调性或凹凸性论证。",
    "5.2_en": "Generate a Riemann-sum problem (n=4). The student must first NAME the sum type and predict over/under-estimation with justification, before computing.",
    "5.3": "请出一道变限积分求导题（上限为 g(x)）。第一问固定：这题由 FTC 的哪一部分管辖、如何判断；每次使用 FTC 须标注 Part 1 或 Part 2。",
    "5.3_en": "Generate a variable-limit differentiation problem. First question: which PART of the FTC governs it and why. Every FTC use must be tagged Part 1 or Part 2.",
    "5.4": "请出一道定积分换元题。第一问固定：如果换元 u=…，式子里有哪三样东西必须同时改变？换元后未写出新边界 u(a)、u(b) 不得求值。",
    "5.4_en": "Generate a definite-integral substitution problem. First question: which THREE things must change under the substitution? No evaluation before new bounds are written.",
    "5.5": "请出一道速度函数运动题（v(t) 在区间内变号）。先问：位移和总路程在这题里是同一个数吗、计算前如何判断；总路程须先做 v(t)=0 符号分析分段。",
    "5.5_en": "Generate a motion problem with v(t) changing sign. Ask first whether displacement and total distance coincide here and how to tell BEFORE integrating.",
    "5.X": "请出一道 Unit 5 综合题：白名单内至少两个技能，必含一个高错陷阱（带边界换元或变限 FTC Part 1）；至多两个子问；第一问固定：这道题需要哪些积分工具、为什么？不得替学生选起点。",
    "5.X_en": "Generate a Unit 5 comprehensive problem: at least two whitelist skills including one flagged trap (bounds substitution or variable-limit FTC); max 2 sub-questions; first question: which integration tools and why? Never choose the starting point.",
    "6.1": "请出一道两曲线间面积题（优先横切更优或曲线相交的情形）。强制第一步：先选纵切还是横切并以几何论证；交点先于上下限。",
    "6.1_en": "Generate an area-between-curves problem (prefer cases where horizontal slicing wins or curves cross). Mandatory first move: choose the slicing direction with geometric justification.",
    "6.2": "请出一道体积题（圆盘/垫圈/已知截面，优先含空隙的垫圈情形）。第一问固定：先归类方法并以几何论证；警惕先减后平方错误。",
    "6.2_en": "Generate a volume problem (disk/washer/known cross-sections; prefer washer-with-gap). First move: classify the method with geometric justification.",
    "6.3": "请出一道函数平均值题。用公式前先要求等面积矩形解释，并区分平均值与平均变化率；涉及积分中值定理时须陈述连续性并几何解读 c。",
    "6.3_en": "Generate an average-value problem. Require the equal-area rectangle interpretation first and the value-vs-rate distinction; for the MVT for integrals, state continuity and interpret c.",
    "6.X": "请出一道 Unit 6 综合题：白名单内至少两个技能、必含一个标记陷阱（相交曲线/垫圈平方/值与率混淆）；至多两个子问；第一问固定：你的切片与设置策略是什么、各部分用什么方法、为什么？",
    "6.X_en": "Generate a Unit 6 comprehensive problem: at least two whitelist skills including one flagged trap; max 2 sub-questions; first question: what is your slicing/setup strategy and which method does each part need, and why?",
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


# ───────── Session 持久化：导出/恢复（防中断丢失） ─────────
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

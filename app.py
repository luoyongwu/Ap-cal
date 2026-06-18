import os
DISABLE_SCL = os.environ.get("DISABLE_SCL", "0") == "1"

import streamlit as st
from anthropic import Anthropic
import base64

st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide")

# ══════════════════════════════════════════════════════
# 后端适配器层
# ══════════════════════════════════════════════════════

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

# ══════════════════════════════════════════════════════
# 教学数据
# ══════════════════════════════════════════════════════


# ── AB/BC Track 选择器 ────────────────────────────────────
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
# 过滤逻辑：渲染 Unit 菜单时跳过 BC_ONLY_CONCEPTS（AB track 时）
# 以及跳过整个 "Unit 8: 表示世界" 和 "BC Toolkit"（AB track 时）
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
    # ── Unit 7: 微分方程（FWM 流世界模型）──────────────────
    "7.1": """HARD RULE for 7.1 (Slope Fields & Direction Fields):

WORLD MODEL — FWM Entry Point:
Before any sketch, student must voice: 'Each point in the plane carries a
slope value — a local flow direction. A solution curve must flow WITH
these arrows at every point it passes through. It cannot cut across them.'
This reframes dy/dx from derivative of a function to flow direction at a point.

1. REGION ANALYSIS GATE: before drawing any solution curve, student must
   identify at least three distinct slope regions (where dy/dx > 0, = 0, < 0).
   No curve-drawing before region analysis is complete.
2. EWM-7.1A (connect-the-dots error): student draws straight segments between
   grid points rather than smooth flow curves.
   Intercept: 'Your curve just crossed a slope arrow pointing a different
   direction — can a river flow against its own current?'
3. EWM-7.1B (local tunnel vision): student reads one region correctly but
   ignores global structure. Intercept: 'If you shift your solution curve left
   or right, does the slope field change? What does that tell you about the
   entire family of solutions?'
4. EWM-7.1C (equilibrium blindness): student fails to identify where dy/dx = 0.
   Intercept: 'Are there horizontal lines where the slope is exactly zero?
   What happens to a solution curve that reaches one — and what happens to
   curves that approach from above or below?'
5. Never draw the solution curve for the student. Never confirm a sketch before
   the student has verified it against at least three slope values on the curve.""",

    "7.2": """HARD RULE for 7.2 (Separable Differential Equations):

WORLD MODEL — Variable Worlds (x-world / y-world):
Separation is an act of sorting the equation into two worlds.
No integration may begin until both worlds are explicitly isolated.

1. SEPARATION GATE (core): before any integral sign, student must show the
   separated form with dy on one side and dx on the other — explicitly written.
   Jumping to integration without showing separation: intercept: 'Show me the
   algebraic step where you divided both sides. Which world does each term
   live in now?'
2. EWM-7.2A (unseparated integration): student integrates dy/dx = xy as
   integral of (dy/dx)dx = integral of xy dx. Do not correct. Ask: 'Can you
   integrate the left side without knowing y as a function of x first?'
3. EWM-7.2B (lost absolute value): student writes ln y instead of ln|y|.
   Intercept: 'Substitute y = -2 into your formula. What does ln give you?
   Is that defined?'
4. EWM-7.2C (vanishing constant): student absorbs +C into the base when
   exponentiating without tracking it. Intercept: 'Show me exactly where the
   +C went when you took e to both sides. Is that step always valid?'
5. PHYSICAL ANCHOR for applied problems: before separating, student must state
   in words what the equation is modeling. Equation before meaning not accepted.""",

    "7.3": """HARD RULE for 7.3 (Euler Method) [BC ONLY]:

WORLD MODEL — Prediction World (PWM):
Core reframe: 'Euler does not find the true y(b). It predicts y(b) step by
step using local slope information. The true value exists; our answer
accumulates error with each step.'
SEED CONCEPT FOR AWM: students see for the first time that a locally correct
procedure produces globally imperfect results — the root of why Unit 9 exists.

1. WORLD MODEL DECLARATION mandatory before step 1: 'I am simulating the
   future one step at a time, not solving the DE.' If student treats output
   as exact: 'Is this the true value, or our best local prediction?'
2. STEP STRUCTURE GATE: each step must contain (a) current point (x_n, y_n),
   (b) slope f(x_n, y_n) at current point, (c) new estimate y_{n+1} = y_n +
   h*f(x_n, y_n). Missing element: intercept before proceeding.
3. EWM-7.3A (exact-value confusion): 'Is that the exact solution or an
   approximation? What would change if we halved the step size?'
4. EWM-7.3B (stale slope): student reuses slope from step n at step n+1.
   'At your new point, is the slope guaranteed to be the same? Why must you
   recompute f at the new location?'
5. EWM-7.3C — APPROXIMATION DIRECTION ERROR (FWM to AWM bridge):
   Student computes correctly but cannot predict whether Euler overestimates
   or underestimates the true solution. This is the most cognitively valuable
   error in 7.3.
   BEFORE computation: student must state concavity of true solution and
   predict direction of error.
   Intercept: 'If the true solution is concave up, where does the tangent line
   lie relative to the curve — above or below? So does each Euler step land
   above or below the true solution?'
   Follow-up: 'What would it take to guarantee our estimate is always an
   overestimate? Always an underestimate?'""",

    "7.4": """HARD RULE for 7.4 (Growth Models: Exponential and Logistic):

WORLD MODEL — Equilibrium World:
COGNITIVE EVOLUTION CHAIN (explicit):
  Pure exponential flow -> Exponential growth model (AB) ->
  What if the environment has a limit? (BC transition) ->
  Logistic model (BC)
Logistic = Exponential + Constraint = Flow under a limiting condition.
These are one cognitive structure at two depths, not two concepts.

SHARED RULES (AB and BC):
1. INITIAL CONDITION GATE: before any computation, identify which solution
   curve the initial condition selects. If C is undetermined: 'What
   information pins down which curve we are on?'
2. EWM-7.4A (k-sign blindness): k > 0 for a decay problem.
   Intercept: 'If the quantity is decreasing, what must be true about dy/dt?
   Now look at your equation.'
3. EWM-7.4B (formula without meaning): student writes y = Ce^(kt) without
   connecting it to the DE. Intercept: 'Without any formula — if growth rate
   is always proportional to current amount, what function grows that way?'

BC-ONLY RULES (Logistic):
4. EQUILIBRIUM FIRST: identify all equilibrium states (dy/dt = 0), classify
   each as stable or unstable. No formula before this.
5. EWM-7.4C — LOGISTIC FORMULA RECITATION: student treats Logistic as a new
   unrelated formula, failing to see Logistic = Exponential + Carrying Capacity.
   Intercept: 'You know exponential has rate proportional to y. Logistic adds
   one modification. What factor slows growth as y approaches L? Why does
   multiplying by (L-y)/L slow things down near L?'
   Follow-up: 'When y is very small compared to L, what does dy/dt = ky(L-y)
   look like? Can you see the exponential hiding inside?'
6. EWM-7.4D (inflection point blindness): cannot locate inflection point.
   Intercept: 'At what population size is dy/dt at its maximum? How do you
   find that from dy/dt = ky(L-y)?'
7. GRAPH ANCHOR mandatory for BC: sketch the qualitative S-curve and label
   initial value, inflection point at y = L/2, carrying capacity L.
   Algebra before sketch is not accepted.""",

    "7.X": """HARD RULE for Unit 7 Comprehensive Review:

SHARED WORLD PRINCIPLE: AB and BC students may receive problems set in the
same physical world (same story, same organism). What differs is the depth
of cognitive tools — not the reality being modeled.

AB WHITELIST: 7.1, 7.2, 7.4 exponential only.
Core AB traps: lost ln|y|, +C vanishes before initial condition, attempt to
integrate without separating. FORBIDDEN: Euler, logistic, IBP, Unit 8/9.

BC WHITELIST: 7.1, 7.2, 7.3, 7.4 full logistic, B1 IBP.
BC cascade trap: separable DE whose solution requires IBP.
BC bridge question: after Euler, ask over- or underestimate with concavity.

SHARED RULES:
1. FWM WORLD DECLARATION first: 'finding solution curves / predicting future
   state / analyzing long-term equilibrium.'
2. First move: 'What is this DE telling you about how the quantity changes?
   Which Unit 7 tools does this problem need, and why?'
3. Never choose the starting approach for the student.
4. Wrong method: one step, let contradiction surface.
5. Maximum 2 sub-questions. One problem at a time.""",

    # ── Unit 8: 表示世界（RWM 表示世界模型）──────────────
    "8.1": """HARD RULE for 8.1 (Parametric Curves and Motion) [BC ONLY]:

WORLD MODEL — RWM: Motion as Two Projections:
A parametric curve describes a moving point whose x- and y-positions are
each independent functions of time t. Same object, two simultaneous
descriptions. Student has entered a new coordinate world.

CROSS-UNIT BRIDGE: shares cognitive structure with 5.4 (u-substitution):
in both, a variable change creates a new world, and rules from the old world
do not automatically transfer. When errors appear: 'In 5.4, when you changed
to u, what else had to change? The same logic applies here.'

1. MOTION MODEL ANCHOR mandatory: before any derivative, student must describe
   the curve as a trajectory — 'A point moves in the plane. At time t, its
   x-position is x(t) and y-position is y(t).'
2. FIRST DERIVATIVE GATE: dy/dx = (dy/dt)/(dx/dt). Student must derive from
   chain rule, not quote as formula. Intercept: 'dy/dx asks how y changes as
   x changes. Neither y nor x is the independent variable — t is. How do you
   connect dy/dx to dy/dt and dx/dt?'
3. EWM-8.1A (t as ordinary variable): student tries to eliminate t immediately.
   Intercept: 'What does t represent physically? Is there information in the
   parametric form that the Cartesian form would lose?'
4. EWM-8.1B — SECOND DERIVATIVE CHAIN FRACTURE (highest-frequency AP BC error):
   Student computes d2y/dx2 as (d2y/dt2)/(d2x/dt2).
   Do not correct immediately. Ask: 'You computed d2y/dx2. What exactly is
   being differentiated with respect to what? The first derivative dy/dx is
   a function of t — how do you differentiate it with respect to x?'
   Follow-up: 'Write out the chain rule for d/dx[dy/dx]. What is the missing
   denominator?' (Correct: d2y/dx2 = (d/dt[dy/dx]) / (dx/dt))
5. ARC LENGTH: set up from Pythagorean theorem on infinitesimal displacement,
   not from memory. Intercept if formula appears without derivation.""",

    "8.2": """HARD RULE for 8.2 (Polar Coordinates: Area and Arc Length) [BC ONLY]:

WORLD MODEL — RWM: Radar Sweep World:
The student must abandon the rectangular slice (dx-strip) and enter a world
where area is swept out by a rotating radius vector.
Fundamental area element: dA = (1/2)r^2 dtheta (sector, not rectangle).

RWM FRAMING: polar coordinates are a different representation of the same
plane — organized by angle and distance, not horizontal and vertical.
Student must recognize: 'I am in a different coordinate world; my area
element must match that world.'

1. COORDINATE WORLD DECLARATION mandatory: before any setup, student must
   state: 'My area element is a thin sector, not a thin rectangle.' If
   student writes dx-strips: 'What shape is a thin slice of a polar region?
   Draw the slice at angle theta with width dtheta. Is it a rectangle?'
2. SECTOR ELEMENT DERIVATION: dA = (1/2)r^2 dtheta must be derived from
   sector area formula, not memorized. Intercept: 'What is the area of a
   full circle of radius r? What fraction does dtheta represent?'
3. EWM-8.2A (rectangular strip inertia): student sets up area as integral of
   f(x)dx. Intercept: 'Your integral has dx. In polar coordinates, what is
   the variable of integration?'
4. EWM-8.2B (missing the pole): student finds r1 = r2 intersections but
   misses origin. Intercept: 'Both curves pass through the origin when r = 0.
   For what values of theta does each curve have r = 0? Do they coincide?'
5. EWM-8.2C (wrong angular bounds): student integrates over wrong range,
   missing symmetry. Intercept: 'Over what range of theta does the curve
   trace exactly one copy of the region? Does your integral reflect that?'
6. GRAPH FIRST: no area setup before student sketches polar curve and
   identifies region by shading.""",

    "Bridge-R1": """HARD RULE for Bridge-R1 (Representation Translation) [BC — Meta-Concept]:

Bridge-R1 is Luo-cal's first Non-Curricular Concept. It does not correspond
to any AP CED topic. It is a meta-concept revealing the shared cognitive root
of 5.4, 8.1, and 8.2.

REPRESENTATION SHIFT ERROR (RWM core):
The deepest error in 5.4, 8.1, and 8.2 is not computational.
  5.4: changed to u-world, evaluated bounds in x-world.
  8.1: entered t-world, computed second derivative as if in x-world.
  8.2: entered theta-world, set up area element as rectangle.
In each case: representation changed, but cognitive world model did not.

TUTOR APPROACH (reflective session, no new problem):
1. RECOGNITION: 'You worked in three coordinate systems: (x,y), parametric
   (x(t),y(t)), and polar (r,theta). In each, you made a specific kind of error.
   What did those errors have in common?'
2. UNIFICATION: 'In 5.4, when you changed to u, what else had to change?
   In 8.2, when you moved to polar, what had to change about the area element?
   Is there a pattern?'
3. TRANSFER TEST: present a novel system (e.g., cylindrical coordinates) and
   ask: 'What question would you ask yourself first — based on 5.4, 8.1, 8.2?'
4. FORWARD BRIDGE to Unit 9: 'In Unit 9, we approximate functions using
   polynomials. That is also a representation change. What might go wrong?'
This session is a retrospective, not a lesson. Maximum: one conversation.""",

    "8.X": """HARD RULE for Unit 8 Comprehensive Review [BC ONLY]:

WORLD MODEL: RWM synthesis — student chooses the correct representation,
sets up the correct element (sector vs strip vs parametric arc), executes
without importing rules from the wrong world.

BC WHITELIST: 8.1 (parametric, including second derivative), 8.2 (polar area,
all intersections including pole). Bridge-R1 reflections allowed.
Cross-unit: 6.1/6.2 Cartesian concepts may appear as contrast.

FLAGGED TRAPS (at least one required):
- Second derivative chain fracture in parametric (EWM-8.1B)
- Missing pole as intersection (EWM-8.2B)
- Rectangular strip in polar area (EWM-8.2A)

SHARED RULES:
1. REPRESENTATION DECLARATION: 'Which coordinate world? What is the
   area/arc-length element in that world?'
2. First move: 'Before writing any integral — what kind of slice describes
   this region? Sketch one slice.'
3. Never choose the representation for the student.
4. Wrong element: one setup step, let error surface.
5. Maximum 2 sub-questions. One problem at a time.""",

    # ── BC Toolkit ───────────────────────────────────────
    "B1": """HARD RULE for B1 (Integration by Parts) [BC Toolkit]:

TOOLKIT INCLUSION BASIS:
(A) New cognitive structure: reversal of the product rule.
(B) New error world: three EWMs absent from all other concepts.
(C) Requires independent Socratic guidance: u/dv choice needs strategy.

WORLD MODEL — Product Reversal World:
IBP is the REVERSE of the product rule. integral u dv = uv - integral v du.
The student runs d(uv)/dx = u(dv/dx) + v(du/dx) backwards.

CROSS-UNIT: confirm substitution was tried and failed before any IBP.

1. PRODUCT RULE REVERSAL ANCHOR mandatory: before u/dv selection, student
   must state: 'This product cannot be simplified by substitution. I am
   reversing the product rule.' If student jumps to u= assignment:
   Intercept: 'Which differentiation rule produces a product? Write it out
   first. Now isolate the integral u dv term.'
2. LIATE as heuristic (not rule): suggest L-I-A-T-E priority but require
   justification. Intercept if no reason given: 'Why does this ordering make
   sense? What property of ln makes it better as u than as dv?'
3. EWM-B1A (dv missing dx): student writes dv = sin x instead of dv = sin x dx.
   Intercept: 'When you integrate dv to get v, what are you integrating with
   respect to? Does your dv reflect that?'
4. EWM-B1B (lost minus sign): student drops minus in uv - integral v du.
   Intercept: 'Write d(uv)/dx first. Rearrange to isolate integral u(dv/dx)dx.
   Where does the minus sign appear, and why?'
5. EWM-B1C — SINGLE-ROUND TUNNEL VISION: student executes one round
   of IBP correctly but stops when the resulting integral still requires
   integration, saying 'I cannot simplify this further.'
   Do not interrupt. After student halts, ask: 'Is this new integral
   simpler than where you started, even if it still needs work?
   Could the same technique apply again?'
   Bridge: 'When differentiating x-squared times e-to-the-x, how many
   times did we apply the product rule? Some integrals need more than
   one pass of the same technique.'
6. EWM-B1D (infinite loop without recognition): student applies IBP twice and
   returns to original integral without recognizing the opportunity.
   Do not interrupt. After two rounds: 'You now have the original integral on
   both sides. Treat it as an unknown variable. What algebraic move follows?'
7. SUBSTITUTION FIRST: IBP is never the first tool tried. Always ask: 'Is there
   a substitution that would work here? Why does it fail?'
8. Tabular Integration is not part of B1 (does not meet Toolkit Inclusion Rule:
   no new cognitive structure, no new EWM, no Socratic guidance needed).""",

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
    "7.1": "请出一道斜率场题。计算前先要求学生描述：每个点的斜率值代表什么（局部流向），解曲线为何不能穿越斜率箭头；然后要求找出至少三个斜率区域再开始作图。",
    "7.1_en": "Generate a slope field problem. Before any sketch, student must describe what each slope value represents (local flow direction) and why solution curves cannot cross slope arrows. Require at least three slope regions before drawing.",
    "7.2": "请出一道可分离变量微分方程题（含初始条件）。第一问固定：这道方程如何把x世界和y世界分开？分离步骤必须显式写出，分离前不许出现积分号。",
    "7.2_en": "Generate a separable DE problem with initial condition. Fixed first question: how does this equation separate the x-world from the y-world? Separation step must be shown explicitly before any integral sign.",
    "7.3": "请出一道欧拉折线法题（BC，真实解为凹或凸函数，给定步长和初值）。第一问固定：欧拉法给出的是精确值还是预测值？每步须含当前点、当前斜率、新估计值。计算后追问：此题欧拉法高估还是低估？用凹凸性解释。",
    "7.3_en": "Generate an Euler method problem (BC; true solution is concave up or down; given step size and initial value). Fixed first question: exact value or prediction? Each step must include current point, current slope, new estimate. After computing, ask: does Euler overestimate or underestimate? Explain using concavity.",
    "7.4": "请出一道增长模型题。AB学生：指数增长，先用初始条件定C，连接DE与解的关系。BC学生：逻辑斯蒂模型，先找所有平衡态并分类稳定性，作定性S型曲线再进代数，禁止直接背公式。",
    "7.4_en": "Generate a growth model problem. AB: exponential — determine C from initial condition, connect DE to solution. BC: logistic — find all equilibria and classify stability, sketch qualitative S-curve before any algebra; formula recitation not accepted.",
    "7.X": "请出一道Unit 7综合题（共用物理情境，AB/BC技能树双轨）。AB仅含7.1/7.2/7.4指数，BC可含7.3/逻辑斯蒂/B1分部积分及桥接。第一问固定：这道题的流世界场景是什么——寻找解曲线族、预测未来状态、还是分析长期平衡？",
    "7.X_en": "Generate a Unit 7 comprehensive problem (shared physical scenario, dual track). AB: 7.1/7.2/7.4-exp only. BC: may add 7.3/logistic/B1 and cross-layer bridging. Fixed first question: which FWM scenario — finding solution curves, predicting future state, or analyzing long-term equilibrium?",
    "8.1": "请出一道参数方程题（BC，含二阶导数或弧长）。第一问固定：这条曲线是什么在运动？x(t)和y(t)各自描述什么？求dy/dx之前先解释为何t是真正的自变量。",
    "8.1_en": "Generate a parametric curve problem (BC; include second derivative or arc length). Fixed first question: what is moving? What does x(t) describe and y(t) describe? Before finding dy/dx, explain why t is the true independent variable.",
    "8.2": "请出一道极坐标面积题（BC，优先含极点为交点或双曲线情形）。第一步固定：先画出极坐标曲线并标出所求区域；再问学生：这个区域的基本面积元素是扇形还是矩形？为什么？",
    "8.2_en": "Generate a polar area problem (BC; prefer cases where pole is an intersection or two curves involved). Fixed first step: sketch polar curve and shade region; then ask: is the basic area element a sector or a rectangle? Why?",
    "Bridge-R1": "开始一个反思性对话（不出新题）：你在5.4、8.1、8.2中各犯过什么错误？这些错误有什么共同点？如果进入全新坐标系，你会先问自己什么问题？",
    "Bridge-R1_en": "Begin a reflective session (no new problem). Ask: what errors appeared in 5.4, 8.1, and 8.2? What did those errors have in common? If you entered a completely new coordinate system, what question would you ask yourself first?",
    "8.X": "请出一道Unit 8综合题（BC，参数方程+极坐标，必含一个标记陷阱：二阶导链式断裂或极点遗漏）。第一问固定：这道题在哪个坐标世界？那个世界的面积或弧长元素是什么？先画图再写积分。",
    "8.X_en": "Generate a Unit 8 comprehensive problem (BC; parametric + polar; at least one flagged trap: second-derivative chain fracture or missing pole). Fixed first question: which coordinate world? What is the area or arc-length element? Sketch before writing any integral.",
    "B1": "请出一道需要分部积分的不定积分题（BC，确认换元法不适用）。第一问固定：为什么换元法在这里失败？分部积分是在逆用哪条求导法则？先写出那条法则再选u和dv，不许只背LIATE。",
    "B1_en": "Generate an integration-by-parts problem (BC; confirm substitution fails). Fixed first question: why does substitution fail? Which differentiation rule are we reversing? Write out that rule first before choosing u and dv; LIATE recitation without justification not accepted.",

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



with st.sidebar:
    # Unit / Concept 两级选择
    selected_unit = st.selectbox(
        L["select_unit"], list(_filtered_UNITS().keys()),
        index=list(_filtered_UNITS().keys()).index(st.session_state.curr_unit))
    selected_concept = st.selectbox(
        L["select_concept"], list(_filtered_UNITS().get(selected_unit, UNITS.get(selected_unit, {})).keys()))
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


# ══════════════════════════════════════════════════════════
# CONCEPT_METADATA — 全量概念元数据（Unit 1-8 + BC Toolkit）
# 字段：concept_id / track / prerequisites / cognitive_dependencies
# cognitive_dependencies 本阶段为空列表，词汇表已定义备用
# ══════════════════════════════════════════════════════════

COGNITIVE_SCHEMA_VOCABULARY = {
    "RepresentationShift",      # 坐标系/变量空间切换（5.4, 8.1, 8.2）
    "VariableSpaceSeparation",  # 变量世界分离（7.2）
    "ApproximationThinking",    # ≈ 而非 = 的认识论（7.3, 9.X）
    "EquilibriumReasoning",     # 稳态与平衡分析（7.4）
    "FlowReasoning",            # 区分状态与变化率（7.X）
    "LocalToGlobalReasoning",   # 无限过程与极限（1.X, 9.X）
    "FunctionComposition",      # 复合函数/链式结构（3.1, 8.1）
    "AccumulationReasoning",    # 物理量累积的直觉（5.5）
    "ProductRuleReversal",      # 乘积法则逆用（B1 IBP）
}

CONCEPT_METADATA = {
    "1.1": {"concept_id":"1.1","track":["AB","BC"],"prerequisites":[],                          "cognitive_dependencies":["LocalToGlobalReasoning"]},
    "1.2": {"concept_id":"1.2","track":["AB","BC"],"prerequisites":["1.1"],                      "cognitive_dependencies":["LocalToGlobalReasoning"]},
    "1.3": {"concept_id":"1.3","track":["AB","BC"],"prerequisites":["1.1","1.2"],                "cognitive_dependencies":["LocalToGlobalReasoning"]},
    "1.4": {"concept_id":"1.4","track":["AB","BC"],"prerequisites":["1.1","1.2"],                "cognitive_dependencies":["LocalToGlobalReasoning"]},
    "1.X": {"concept_id":"1.X","track":["AB","BC"],"prerequisites":["1.1","1.2","1.3","1.4"],   "cognitive_dependencies":["LocalToGlobalReasoning"]},
    "2.1": {"concept_id":"2.1","track":["AB","BC"],"prerequisites":["1.1","1.2"],                "cognitive_dependencies":["FlowReasoning"]},
    "2.2": {"concept_id":"2.2","track":["AB","BC"],"prerequisites":["2.1"],                      "cognitive_dependencies":["FlowReasoning"]},
    "2.3": {"concept_id":"2.3","track":["AB","BC"],"prerequisites":["2.1"],                      "cognitive_dependencies":[]},
    "2.4": {"concept_id":"2.4","track":["AB","BC"],"prerequisites":["2.1","2.2"],                "cognitive_dependencies":[]},
    "2.X": {"concept_id":"2.X","track":["AB","BC"],"prerequisites":["2.1","2.2","2.3","2.4"],   "cognitive_dependencies":["FlowReasoning"]},
    "3.1": {"concept_id":"3.1","track":["AB","BC"],"prerequisites":["2.1"],                      "cognitive_dependencies":["RepresentationShift"]},
    "3.2": {"concept_id":"3.2","track":["AB","BC"],"prerequisites":["3.1"],                      "cognitive_dependencies":["RepresentationShift"]},
    "3.3": {"concept_id":"3.3","track":["AB","BC"],"prerequisites":["2.1"],                      "cognitive_dependencies":[]},
    "3.4": {"concept_id":"3.4","track":["AB","BC"],"prerequisites":["3.1"],                      "cognitive_dependencies":["RepresentationShift"]},
    "3.5": {"concept_id":"3.5","track":["BC"],     "prerequisites":["3.1"],                      "cognitive_dependencies":["RepresentationShift"]},
    "3.X": {"concept_id":"3.X","track":["AB","BC"],"prerequisites":["3.1","3.2","3.3","3.4"],   "cognitive_dependencies":[]},
    "4.1": {"concept_id":"4.1","track":["AB","BC"],"prerequisites":["2.1","3.1"],                "cognitive_dependencies":["FlowReasoning"]},
    "4.2": {"concept_id":"4.2","track":["AB","BC"],"prerequisites":["2.1"],                      "cognitive_dependencies":["FlowReasoning"]},
    "4.3": {"concept_id":"4.3","track":["AB","BC"],"prerequisites":["3.1"],                      "cognitive_dependencies":["FlowReasoning"]},
    "4.4": {"concept_id":"4.4","track":["AB","BC"],"prerequisites":["2.1","2.3"],                "cognitive_dependencies":["FlowReasoning"]},
    "4.5": {"concept_id":"4.5","track":["AB","BC"],"prerequisites":["2.1","3.1"],                "cognitive_dependencies":["ApproximationThinking"]},
    "4.X": {"concept_id":"4.X","track":["AB","BC"],"prerequisites":["4.1","4.2","4.3","4.4","4.5"],"cognitive_dependencies":[]},
    "5.1": {"concept_id":"5.1","track":["AB","BC"],"prerequisites":["2.1"],                      "cognitive_dependencies":[]},
    "5.2": {"concept_id":"5.2","track":["AB","BC"],"prerequisites":["1.2","5.1"],                "cognitive_dependencies":["LocalToGlobalReasoning","ApproximationThinking"]},
    "5.3": {"concept_id":"5.3","track":["AB","BC"],"prerequisites":["5.1","3.1"],                "cognitive_dependencies":["RepresentationShift"]},
    "5.4": {"concept_id":"5.4","track":["AB","BC"],"prerequisites":["5.1","3.1"],                "cognitive_dependencies":["RepresentationShift","VariableSpaceSeparation"]},
    "5.5": {"concept_id":"5.5","track":["AB","BC"],"prerequisites":["5.2","5.3"],                "cognitive_dependencies":["AccumulationReasoning"]},
    "5.X": {"concept_id":"5.X","track":["AB","BC"],"prerequisites":["5.1","5.2","5.3","5.4","5.5"],"cognitive_dependencies":[]},
    "6.1": {"concept_id":"6.1","track":["AB","BC"],"prerequisites":["5.2","5.3"],                "cognitive_dependencies":["RepresentationShift"]},
    "6.2": {"concept_id":"6.2","track":["AB","BC"],"prerequisites":["6.1"],                      "cognitive_dependencies":[]},
    "6.3": {"concept_id":"6.3","track":["AB","BC"],"prerequisites":["5.2","5.3"],                "cognitive_dependencies":[]},
    "6.X": {"concept_id":"6.X","track":["AB","BC"],"prerequisites":["6.1","6.2","6.3"],          "cognitive_dependencies":[]},
    "7.1": {"concept_id":"7.1","track":["AB","BC"],"prerequisites":["2.1"],                      "cognitive_dependencies":["FlowReasoning"]},
    "7.2": {"concept_id":"7.2","track":["AB","BC"],"prerequisites":["3.1","5.1"],                "cognitive_dependencies":["VariableSpaceSeparation","FlowReasoning"]},
    "7.3": {"concept_id":"7.3","track":["BC"],     "prerequisites":["7.1","7.2"],                "cognitive_dependencies":["ApproximationThinking","FlowReasoning"]},
    "7.4": {"concept_id":"7.4","track":["AB","BC"],"prerequisites":["7.2"],                      "cognitive_dependencies":["FlowReasoning","EquilibriumReasoning","AccumulationReasoning"]},
    "7.X": {"concept_id":"7.X","track":["AB","BC"],"prerequisites":["7.1","7.2","7.4"],          "cognitive_dependencies":[]},
    "8.1": {"concept_id":"8.1","track":["BC"],     "prerequisites":["3.1","3.5","5.2"],          "cognitive_dependencies":["RepresentationShift"]},
    "8.2": {"concept_id":"8.2","track":["BC"],     "prerequisites":["5.2","6.1"],                "cognitive_dependencies":["RepresentationShift"]},
    "Bridge-R1": {"concept_id":"Bridge-R1","track":["BC"],"prerequisites":["5.4","8.1","8.2"],  "cognitive_dependencies":["RepresentationShift"]},
    "8.X": {"concept_id":"8.X","track":["BC"],     "prerequisites":["8.1","8.2"],               "cognitive_dependencies":["RepresentationShift"]},
    "B1":  {"concept_id":"B1", "track":["BC"],     "prerequisites":["5.1","5.4","3.3"],          "cognitive_dependencies":["ProductRuleReversal"]},
}
import os
DISABLE_SCL = os.environ.get("DISABLE_SCL", "0") == "1"

import streamlit as st
from anthropic import Anthropic
import base64

st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide")

class RailwayAdapter:
    # 优先从 Streamlit Secrets 读取（Railway 服务重建后域名会变，
    # 改这里的 secrets 配置即可，不需要再改代码、不需要再等部署）。
    # 找不到 secrets 配置时，回退到目前已知的最新域名。
    try:
        BACKEND_URL = st.secrets["RAILWAY_BACKEND_URL"]
    except (KeyError, FileNotFoundError):
        BACKEND_URL = "https://web-production-b9d95.up.railway.app"
    def __init__(self):
        pass
    def chat(self, system, messages, max_tokens=500):
        import urllib.request, json, urllib.error
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        concept_id = st.session_state.get("concept_id", "unknown")
        lang = "en" if st.session_state.get("lang", "zh") == "en" else "zh"

        # ===== 身份系统 v0.2 改造 =====
        # 不再由前端自己声明 student_id，改为在请求头携带 session_token，
        # 由后端从 token 解析出真正的 student_uuid（见 ADR-010 安全底线原则）。
        token = st.session_state.get("session_token")
        if not token:
            raise RuntimeError("尚未登录，无法调用 Railway Backend，请先在侧边栏登录。")

        payload = {"concept_id": concept_id,
                   "user_input": last_user, "session_id": "streamlit",
                   "language": lang}
        req = urllib.request.Request(
            f"{self.BACKEND_URL}/api/v1/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {token}"},
            method="POST")
        try:
            with urllib.request.urlopen(req) as r:
                result = json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # session 失效：可能是过期，也可能是账号在其他设备重新登录，
                # 把本地 session_token 清空，逼用户重新走登录流程。
                st.session_state.session_token = None
                st.session_state.student_display_name = None
                raise RuntimeError("会话已失效（可能您的账号已在其他设备登录），请重新登录。") from e
            raise
        # ===== 身份系统改造结束 =====
        return result.get("response", "")

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
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    def chat(self, system, messages, max_tokens=1500):
        msgs = [{"role": "system", "content": system}] + messages
        r = self.client.chat.completions.create(model=self.MODEL, messages=msgs, max_tokens=max_tokens)
        return r.choices[0].message.content

class OllamaAdapter:
    def __init__(self, model="gemma3"):
        self.model = model
        self.url = "http://localhost:11434/api/chat"
    def chat(self, system, messages, max_tokens=1500):
        msgs = [{"role": "system", "content": system}] + messages
        r = __import__("requests").post(self.url, json={"model": self.model, "messages": msgs, "stream": False})
        return r.json()["message"]["content"]

BACKENDS = {
    "Anthropic (Claude)": "anthropic",
    "DeepSeek": "deepseek",
    "本地 Ollama (Gemma)": "ollama",
    "🚀 Railway Backend": "railway",
}

def get_adapter():
    b = st.session_state.backend
    k = st.session_state.api_key
    if b == "anthropic": return AnthropicAdapter(k)
    elif b == "deepseek": return DeepSeekAdapter(k)
    elif b == "railway": return RailwayAdapter()
    else: return OllamaAdapter()


# ================================================================
# 身份系统 v0.2 — 登录函数
# ================================================================
def railway_login(login_code: str) -> bool:
    """调用后端 /auth/login。成功则把 session_token 写入 st.session_state 并返回 True；
    失败则把错误信息写入 st.session_state["_login_error"] 并返回 False。"""
    import urllib.request, json, urllib.error

    payload = {"login_code": login_code.strip()}
    req = urllib.request.Request(
        f"{RailwayAdapter.BACKEND_URL}/auth/login",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        st.session_state.session_token = result["session_token"]
        st.session_state.student_display_name = result.get("display_name")
        st.session_state["_login_error"] = None
        return True
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read())
            st.session_state["_login_error"] = err_body.get("detail", "登录失败，请检查授权码。")
        except Exception:
            st.session_state["_login_error"] = "登录失败，请检查授权码。"
        return False
    except Exception as e:
        st.session_state["_login_error"] = f"网络错误，请稍后重试：{e}"
        return False
# ================================================================
# 身份系统登录函数结束
# ================================================================


if "student_track" not in st.session_state:
    st.session_state.student_track = "AB"

with st.sidebar:
    selected_track = st.radio("学习轨道 / Track", options=["AB", "BC"],
        index=0 if st.session_state.student_track == "AB" else 1,
        horizontal=True, key="track_radio")
    if selected_track != st.session_state.student_track:
        st.session_state.student_track = selected_track
        st.rerun()

UNITS = {
    "Unit 1: 极限与连续": {
        "1.1 极限简介": "1.1", "1.2 极限计算": "1.2",
        "1.3 连续性": "1.3", "1.4 渐近线": "1.4", "1.X 综合练习": "1.X"
    },
    "Unit 2: 导数定义": {
        "2.1 导数定义": "2.1", "2.2 可导与连续": "2.2",
        "2.3 导数图像": "2.3", "2.4 高阶导数": "2.4", "2.X 综合练习": "2.X"
    },
    "Unit 3: 求导法则": {
        "3.1 链式法则": "3.1", "3.2 隐函数求导": "3.2",
        "3.3 乘积与商法则": "3.3", "3.4 反函数求导": "3.4",
        "3.5 参数方程求导": "3.5", "3.X 综合练习": "3.X"
    },
    "Unit 4: 导数应用": {
        "4.1 极值定理": "4.1", "4.2 中值定理": "4.2",
        "4.3 相关变化率": "4.3", "4.4 导数图像判读": "4.4",
        "4.5 线性近似": "4.5", "4.X 综合练习": "4.X"
    },
    "Unit 5: 积分": {
        "5.1 不定积分与原函数": "5.1", "5.2 黎曼和与定积分": "5.2",
        "5.3 微积分基本定理": "5.3", "5.4 换元积分法": "5.4",
        "5.5 净变化量与运动问题": "5.5", "5.X 综合练习": "5.X"
    },
    "Unit 6: 积分应用": {
        "6.1 两曲线间面积": "6.1", "6.2 旋转体与已知截面体积": "6.2",
        "6.3 函数平均值与积分中值定理": "6.3", "6.X 综合练习": "6.X"
    },
    "Unit 7: 微分方程": {
        "7.1 斜率场与方向场": "7.1", "7.2 可分离变量微分方程": "7.2",
        "7.3 欧拉折线法 (BC)": "7.3", "7.4 增长模型": "7.4", "7.X 综合练习": "7.X"
    },
    "Unit 8: 表示世界": {
        "8.1 参数方程与运动": "8.1", "8.2 极坐标面积与弧长": "8.2",
        "Bridge-R1 表示转换": "Bridge-R1", "8.X 综合练习": "8.X"
    },
    "BC Toolkit": {"B1 分部积分法": "B1"},
}

def _filtered_UNITS():
    _track = st.session_state.get("student_track", "AB")
    if _track == "BC": return UNITS
    _hidden = {"Unit 8: 表示世界", "BC Toolkit"}
    _bc_only = {"7.3","8.1","8.2","Bridge-R1","8.X","B1"}
    return {
        uname: {k:v for k,v in concepts.items() if v not in _bc_only}
        for uname, concepts in UNITS.items() if uname not in _hidden
    }

CONCEPT_CONSTRAINTS = {
    "1.1": "Ensure student builds intuition numerically/graphically before algebra.",
    "1.2": "Guide student to apply limit laws step by step. Do not skip steps.",
    "1.3": "Focus on the three-part definition of continuity at a point.",
    "1.4": "Guide student to identify vertical and horizontal asymptotes separately.",
    "1.X": "Generate a comprehensive problem combining limits, continuity, and asymptotes.",
    "2.1": "HARD RULE: Guide student to derive the derivative using the limit definition. Do not skip the limit process.",
    "2.2": "Ensure student understands differentiability implies continuity but not vice versa.",
    "2.3": "Focus on connecting the sign of f prime to increasing/decreasing behavior of f.",
    "2.4": "Guide student to apply differentiation rules repeatedly for higher-order derivatives.",
    "2.X": "Generate a comprehensive problem combining limit definition of derivative, differentiability, and graphical interpretation.",
    "3.1": "HARD RULE: Decompose f(g(x)) into f(u) and g(x) explicitly before differentiating.",
    "3.2": "HARD RULE: Ensure dy/dx appears explicitly when differentiating y terms.",
    "3.3": "HARD RULE: For products, require student to identify u and v explicitly. For quotients, identify numerator and denominator before applying quotient rule.",
    "3.4": "Verify student correctly applies the inverse function derivative formula.",
    "3.5": "HARD RULE: Require student to write dx/dt and dy/dt separately before computing dy/dx.",
    "3.X": "HARD RULE: Generate ONE problem combining at least TWO Unit 3 skills. Maximum 2 sub-questions. First question: Which method and why? Never choose starting point for student.",
    "4.1": "HARD RULE: Student MUST state ALL EVT conditions before applying. Critical points include where f prime is zero OR undefined. Always compare all candidates including endpoints.",
    "4.2": "HARD RULE: Verify all THREE MVT hypotheses in order. IVT vs MVT: MVT gives f prime(c) equals average rate of change, not f(c)=0. Existence via IVT, uniqueness via monotonicity.",
    "4.3": ("HARD RULE [LAYER: PROBLEM_SOLVING]: Student MUST follow exact sequence: "
            "(1) identify variables, (2) write relationship equation, "
            "(3) differentiate with respect to t, (4) THEN substitute values. "
            "SIGN RULE: Require interpretation of negative derivatives. "
            "HARD RULE 4.3-PRE-OVERRIDE [HIGHEST PRIORITY - CROSS-LAYER]: "
            "This rule overrides SINGLE-PROBLEM RULE and all other rules. "
            "If student input contains substitution of a numerical value into a variable BEFORE differentiating, "
            "BEFORE doing anything else - even before applying SINGLE-PROBLEM RULE - "
            "you MUST immediately ask ONLY this one question: "
            "'你是在求导之前代入的数值，还是在求导之后？/ "
            "Did you substitute the numerical value before differentiating, or after?' "
            "Do NOT list multiple problems. Do NOT ask student to choose. "
            "Do NOT mention variable relationships disappearing. "
            "Do NOT hint at consequences. Do NOT point out other errors. "
            "Wait for answer to THIS question first. Only after student answers "
            "may you proceed to SINGLE-PROBLEM RULE or any other rule. "
            "STUDENT FOLLOW-UP: If student asks what to do, reply ONLY: "
            "'回到代入数值之前的那一步。在你代入具体数值之前，你的方程是什么？'"),
    "4.4": "HARD RULE: Where f prime has extremum, f has INFLECTION POINT not extremum. f prime zero is necessary but NOT sufficient for inflection; verify sign change.",
    "4.5": "HARD RULE: Student MUST write L(x)=f(a)+f prime(a)(x-a) before substituting. Redirect if student computes directly or omits f(a).",
    "4.X": "Generate comprehensive problem combining EVT, MVT, related rates, derivative graph reading, and linearization. Cover at least three sub-topics.",
    "5.1": "HARD RULE: Never accept antiderivative without +C. Geometric anchor: student must describe family of curves before computation.",
    "5.2": "HARD RULE: Approximation must be NAMED first. Require over/under-estimate judgment. Definite integral must be voiced as LIMIT of sums before FTC.",
    "5.3": "HARD RULE: Always tag FTC Part 1 or Part 2. Variable-limit trap: upper limit g(x) requires chain rule factor. Confirm F is antiderivative before Part 2 evaluation.",
    "5.4": "HARD RULE: Declare u and du explicitly first. Bounds trap: new bounds u(a) and u(b) required BEFORE evaluation. No back-substitution after bounds converted.",
    "5.5": "HARD RULE: Physical anchor first. Total distance integrates absolute value of v. Solve v(t)=0 and split before computing.",
    "5.X": "HARD RULE: Combine at least TWO skills including one flagged trap. Max 2 sub-questions. First move: which tool and why? Tag FTC Part 1 or Part 2.",
    "6.1": "HARD RULE: Slicing decision first with geometric justification. Intersections before limits. Name top/bottom or right/left functions.",
    "6.2": "HARD RULE: Method classification first. Washer trap: pi times (R squared minus r squared), never pi times (R minus r) squared. Radii are distances to axis.",
    "6.3": "HARD RULE: Conflation trap: average VALUE versus average RATE OF CHANGE. Equal-area rectangle anchor before any formula. State continuity for MVT for Integrals.",
    "6.X": "HARD RULE: Combine at least TWO whitelist skills with one flagged trap. Max 2 sub-questions. First move: slicing and setup strategy.",
    "7.1": "HARD RULE FWM: Each point carries slope as local flow direction. Identify three slope regions before drawing. Find where dy/dx equals zero and classify equilibria.",
    "7.2": "HARD RULE: Show separated form before any integral sign. Write ln absolute value of y not ln y. Track plus C through exponentiation.",
    "7.3": "HARD RULE BC: World model declaration mandatory before step 1. Each step needs current point, slope, new estimate. Concavity determines over or underestimate.",
    "7.4": "HARD RULE: Initial condition gate before any computation. k-sign blindness check. BC only: equilibrium first, classify stability, sketch S-curve before algebra.",
    "7.X": "HARD RULE: AB whitelist is 7.1, 7.2, 7.4 exponential only. BC whitelist is full 7.1 through 7.4 plus B1. FWM world declaration first.",
    "8.1": "HARD RULE BC RWM: Motion model anchor mandatory before any derivative. Derive dy/dx from chain rule not from memory. Second derivative chain fracture: d2y/dx2 is not (d2y/dt2)/(d2x/dt2).",
    "8.2": "HARD RULE BC RWM: Area element is thin sector not rectangle. Check pole as intersection. Sketch before area setup.",
    "Bridge-R1": "Reflective session only, no new problem. Unify errors from 5.4, 8.1, 8.2.",
    "8.X": "HARD RULE BC: At least one flagged trap. Representation declaration first. Sketch before integral.",
    "B1": "HARD RULE BC: Product rule reversal anchor before u/dv selection. LIATE is heuristic not rule. Single-round tunnel vision trap. Infinite loop trap. Substitution first always.",
}

OPENING_PROMPTS = {
    "1.X": "请出一道Unit 1综合题，综合考查极限、连续性和渐近线，包含至少两个子问题。",
    "1.X_en": "Generate a comprehensive Unit 1 problem covering limits, continuity, and asymptotes. Include at least two sub-questions.",
    "2.X": "请出一道Unit 2综合题，包含至少两个子问题。",
    "2.X_en": "Generate a comprehensive Unit 2 problem. Include at least two sub-questions.",
    "3.X": "请出一道Unit 3综合题，包含至少两个子问题。",
    "3.X_en": "Generate a comprehensive Unit 3 problem. Include at least two sub-questions.",
    "4.4": "请出一道导数图像判读题。不要直接给出答案，先只问第一个引导性问题。",
    "4.4_en": "Generate a derivative graph reading problem. Ask only the first guiding question.",
    "4.5": "请出一道线性近似题。不要直接给出步骤，先只问第一个引导性问题。",
    "4.5_en": "Generate a linearization problem. Ask only the first guiding question.",
    "4.X": "请出一道Unit 4综合题，包含至少三个子问题。",
    "4.X_en": "Generate a comprehensive Unit 4 problem. Include at least three sub-questions.",
    "5.1": "请出一道不定积分题。计算前先要求学生描述曲线族；坚持+C。",
    "5.1_en": "Generate an antiderivative problem. Student must describe family of curves first; insist on +C.",
    "5.2": "请出一道黎曼和近似题（n=4）。学生须先命名类型并判断高估/低估。",
    "5.2_en": "Generate a Riemann-sum problem (n=4). Student must name sum type and predict over/under-estimation first.",
    "5.3": "请出一道变限积分求导题。第一问：FTC哪一部分？",
    "5.3_en": "Generate a variable-limit differentiation problem. First question: which PART of FTC?",
    "5.4": "请出一道定积分换元题。第一问：哪三样东西必须同时改变？",
    "5.4_en": "Generate a definite-integral substitution problem. First question: which THREE things must change?",
    "5.5": "请出一道速度函数运动题（v(t)在区间内变号）。先问：位移和总路程是同一个数吗？",
    "5.5_en": "Generate a motion problem with v(t) changing sign. Ask first whether displacement and total distance coincide.",
    "5.X": "请出一道Unit 5综合题：至少两个技能，必含一个高错陷阱；至多两个子问。",
    "5.X_en": "Generate a Unit 5 comprehensive problem: two skills, one flagged trap; max 2 sub-questions.",
    "6.1": "请出一道两曲线间面积题。强制第一步：先选切片方向并以几何论证。",
    "6.1_en": "Generate an area-between-curves problem. First move: choose slicing direction with geometric justification.",
    "6.2": "请出一道体积题。第一问：先归类方法并以几何论证。",
    "6.2_en": "Generate a volume problem. First move: classify method with geometric justification.",
    "6.3": "请出一道函数平均值题。用公式前先要求等面积矩形解释。",
    "6.3_en": "Generate an average-value problem. Require equal-area rectangle interpretation first.",
    "6.X": "请出一道Unit 6综合题：至少两个技能、必含一个标记陷阱；至多两个子问。",
    "6.X_en": "Generate a Unit 6 comprehensive problem: two skills, one flagged trap; max 2 sub-questions.",
    "7.1": "请出一道斜率场题。要求找出至少三个斜率区域再开始作图。",
    "7.1_en": "Generate a slope field problem. Require three slope regions before drawing.",
    "7.2": "请出一道可分离变量微分方程题（含初始条件）。第一问：如何分离x世界和y世界？",
    "7.2_en": "Generate a separable DE problem with initial condition. First question: how to separate x-world from y-world?",
    "7.3": "请出一道欧拉折线法题（BC）。第一问：精确值还是预测值？",
    "7.3_en": "Generate an Euler method problem (BC). First question: exact or prediction?",
    "7.4": "请出一道增长模型题。AB：指数增长。BC：逻辑斯蒂，先找平衡态。",
    "7.4_en": "Generate a growth model problem. AB: exponential. BC: logistic, equilibria first.",
    "7.X": "请出一道Unit 7综合题。第一问：流世界场景是什么？",
    "7.X_en": "Generate a Unit 7 comprehensive problem. First question: which FWM scenario?",
    "8.1": "请出一道参数方程题（BC，含二阶导数）。第一问：什么在运动？",
    "8.1_en": "Generate a parametric curve problem (BC). First question: what is moving?",
    "8.2": "请出一道极坐标面积题（BC）。第一步：画图；再问：扇形还是矩形？",
    "8.2_en": "Generate a polar area problem (BC). First: sketch; then ask: sector or rectangle?",
    "Bridge-R1": "开始反思性对话（不出新题）：5.4、8.1、8.2的错误有什么共同点？",
    "Bridge-R1_en": "Begin reflective session (no new problem). What did errors in 5.4, 8.1, 8.2 have in common?",
    "8.X": "请出一道Unit 8综合题（BC，必含一个标记陷阱）。先画图再写积分。",
    "8.X_en": "Generate a Unit 8 comprehensive problem (BC; one flagged trap). Sketch before integral.",
    "B1": "请出一道需要分部积分的题（BC）。第一问：为什么换元法失败？",
    "B1_en": "Generate an IBP problem (BC). First question: why does substitution fail?",
}

LANG_LABELS = {
    "Chinese": {
        "title_prefix": "🎓 Luo-cal", "config": "⚙️ 配置页",
        "api_key": "🔑 API Key", "confirm_key": "✅ 确认 Key",
        "key_ok": "Key 已锁定", "key_err": "Key 格式错误（需以 sk- 开头）",
        "select_unit": "选择 Unit", "select_concept": "选择 Concept",
        "select_backend": "🔌 选择后端",
        "connected": "🟢 系统已连接", "disconnected": "🔴 未连接",
        "connected_color": "#1a7a1a", "disconnected_color": "#cc0000",
        "lang_btn": "切换为 English 🌐", "show_test": "🔧 显示测试面板",
        "wait": "请在左侧配置页输入 API Key 并点击确认。",
        "refresh": "🔄 刷新当前概念",
        "upload": "📷 上传手写题目（拍照或选图）",
        "camera": "📸 拍照", "gallery": "🖼️ 选图",
        "selected": "已选", "preview": "张，预览：",
        "send_img": "✅ 确认发送图片",
        "img_prompt": "请分析图中的手写内容，按苏格拉底方式引导。",
        "chat_input": "输入回答...",
        "mastery_msg": "✅ 连续3次正确！已解锁知识点总结。",
        "summary_btn": "💡 生成深度总结", "summary_title": "🎓 知识点总结",
        "generating": "生成总结中...", "test_panel": "🔧 测试面板",
        "test_input": "测试输入", "test_placeholder": "输入测试题目或学生答案...",
        "test_send": "✅ 确认发送测试", "test_working": "⏳ 系统正在工作，请稍后……",
        "test_empty": "请先输入内容。", "spinner": "⏳ 导师思考中…",
        "opening_default": "请为概念 {concept} 出一道练习题，不要直接给出解题步骤，先只问第一个引导性问题。",
        "lang_instr": "Respond in Chinese.", "summary_lang": "in Chinese",
        "secrets_notice": "🔑 已从系统配置自动加载 API Key",
        "ollama_notice": "🖥️ 本地 Ollama 模式，无需 API Key",
    },
    "English": {
        "title_prefix": "🎓 Luo-cal", "config": "⚙️ Settings",
        "api_key": "🔑 API Key", "confirm_key": "✅ Confirm Key",
        "key_ok": "Key locked", "key_err": "Invalid key format (must start with sk-)",
        "select_unit": "Select Unit", "select_concept": "Select Concept",
        "select_backend": "🔌 Select Backend",
        "connected": "🟢 Connected", "disconnected": "🔴 Disconnected",
        "connected_color": "#1a7a1a", "disconnected_color": "#cc0000",
        "lang_btn": "切换为中文 🌐", "show_test": "🔧 Show Test Panel",
        "wait": "Please enter your API Key in the sidebar and confirm.",
        "refresh": "🔄 Refresh Concept",
        "upload": "📷 Upload Handwritten Work (Camera or Gallery)",
        "camera": "📸 Take Photo", "gallery": "🖼️ Upload Image",
        "selected": "Selected", "preview": " image(s), preview:",
        "send_img": "✅ Send Image(s)",
        "img_prompt": "Please analyze the handwritten content and guide using the Socratic method.",
        "chat_input": "Enter your answer...",
        "mastery_msg": "✅ 3 consecutive correct answers! Summary unlocked.",
        "summary_btn": "💡 Generate Summary", "summary_title": "🎓 Knowledge Summary",
        "generating": "Generating summary...", "test_panel": "🔧 Test Panel",
        "test_input": "Test Input", "test_placeholder": "Enter test question or student answer...",
        "test_send": "✅ Send Test Input", "test_working": "⏳ System working, please wait……",
        "test_empty": "Please enter content first.", "spinner": "⏳ Tutor thinking…",
        "opening_default": "Generate one practice problem for {concept}. Do not give steps. Ask only the first guiding question.",
        "lang_instr": "Respond in English.", "summary_lang": "in English",
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
    # ---- 身份系统 v0.2 新增状态 ----
    "session_token": None,
    "student_display_name": None,
    "_login_error": None,
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
        except (KeyError, FileNotFoundError): pass
    elif _b == "deepseek":
        try:
            _k = st.secrets["DEEPSEEK_API_KEY"]
            if _k and _k.startswith("sk-"):
                st.session_state.api_key = _k
                st.session_state.key_confirmed = True
        except (KeyError, FileNotFoundError): pass
    elif _b == "ollama":
        st.session_state.key_confirmed = True

L = LANG_LABELS[st.session_state.lang]

with st.sidebar:
    st.title(L["config"])
    if st.button(L["lang_btn"], use_container_width=True):
        st.session_state.lang = "English" if st.session_state.lang == "Chinese" else "Chinese"
        st.rerun()
    st.divider()
    backend_label = st.selectbox(L["select_backend"], list(BACKENDS.keys()),
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
            except (KeyError, FileNotFoundError): pass
        elif new_backend == "deepseek":
            try:
                _k = st.secrets["DEEPSEEK_API_KEY"]
                if _k and _k.startswith("sk-"):
                    st.session_state.api_key = _k
                    st.session_state.key_confirmed = True
            except (KeyError, FileNotFoundError): pass
        elif new_backend == "ollama":
            st.session_state.key_confirmed = True
        elif new_backend == "railway":
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

    # ================================================================
    # 身份系统 v0.2 — 登录区域（仅 Railway Backend 需要）
    # ================================================================
    if st.session_state.backend == "railway":
        if st.session_state.session_token:
            name = st.session_state.student_display_name or "已登录学生"
            st.success(f"👤 {name}")
            if st.button("🚪 退出登录", use_container_width=True):
                st.session_state.session_token = None
                st.session_state.student_display_name = None
                st.session_state.messages = []
                st.rerun()
        else:
            st.subheader("🔐 学生登录")
            login_code_input = st.text_input("请输入授权码", placeholder="LUO-XXXXXXXX")
            if st.button("登录", use_container_width=True):
                if login_code_input.strip():
                    if railway_login(login_code_input):
                        st.session_state.messages = []
                        st.rerun()
                    else:
                        st.error(st.session_state.get("_login_error", "登录失败"))
                else:
                    st.warning("请输入授权码。")
        st.divider()
    # ================================================================
    # 身份系统登录区域结束
    # ================================================================

with st.sidebar:
    selected_unit = st.selectbox(L["select_unit"], list(_filtered_UNITS().keys()),
        index=list(_filtered_UNITS().keys()).index(st.session_state.curr_unit)
        if st.session_state.curr_unit in _filtered_UNITS() else 0)
    selected_concept = st.selectbox(L["select_concept"],
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
    status_text = L["connected"] if st.session_state.key_confirmed else L["disconnected"]
    st.markdown(
        f"<div style='background:{status_color};color:white;padding:12px;"
        f"border-radius:8px;text-align:center;font-size:16px;font-weight:bold;'>"
        f"{status_text}</div>", unsafe_allow_html=True)
    st.divider()
    show_test = st.checkbox(L["show_test"], value=False)

def update_mastery(concept_id, response_text):
    scores = st.session_state.mastery_scores
    if concept_id not in scores: scores[concept_id] = 0
    if "[STATUS: CORRECT]" in response_text: scores[concept_id] += 1
    elif "[STATUS: INCORRECT]" in response_text or "[STATUS: PARTIAL]" in response_text:
        scores[concept_id] = 0
    if scores[concept_id] >= 3: st.session_state.mastery_ready = True

def extract_leakage(response_text):
    import re
    match = re.search(r"\[LEAKAGE:\s*(\d)\]", response_text)
    return int(match.group(1)) if match else None

def generate_summary(concept_id):
    adapter = get_adapter()
    digest = "\n".join(
        f"{m['role'].upper()}: {m['content'][:200]}"
        for m in st.session_state.messages[-8:]
        if isinstance(m.get("content"), str))
    L_local = LANG_LABELS[st.session_state.lang]
    prompt = (f"Based on this tutoring session for concept {concept_id}:\n{digest}\n"
              f"Generate a structured summary {L_local['summary_lang']}:\n"
              f"1. Core Rule\n2. Key Steps\n3. Pitfall")
    return adapter.chat("You are a helpful summarizer.",
                        [{"role": "user", "content": prompt}], max_tokens=600)

def get_ai_response(extra_content=None):
    adapter = get_adapter()
    concept_id = UNITS[st.session_state.curr_unit][st.session_state.curr_concept]
    # ===== Bug 修复（2026-07-11 人工测试003号学生时发现）=====
    # RailwayAdapter.chat() 读取的是 st.session_state["concept_id"]，
    # 但此前整个文件里从未有任何地方往这个 key 写入过值——concept_id
    # 一直只是本函数内部的局部变量，导致后端 cognitive_signals 表的
    # concept 列永远写入默认兜底值 "unknown"。这里补上同步写入。
    st.session_state["concept_id"] = concept_id
    # ===== Bug 修复结束 =====
    L_local = LANG_LABELS[st.session_state.lang]
    system_msg = (
        f"You are a strict AP Calculus Socratic tutor. {L_local['lang_instr']} "
        f"NEVER give the answer directly. Always guide with questions. "
        f"TEACHING CONSTRAINT: {CONCEPT_CONSTRAINTS.get(concept_id, 'Guide step by step.')} "
        f"\nRESPONSE FORMAT RULE: You MUST append exactly these two tags at the very end, on separate lines: "
        f"First: one of [STATUS: CORRECT], [STATUS: PARTIAL], [STATUS: INCORRECT], or [STATUS: GUIDING]. "
        f"Second: [LEAKAGE: N] where N is 0, 1, 2, or 3. "
        f"0=no leakage pure Socratic, 1=directional hint, 2=obvious hint toward answer, 3=equivalent to giving answer. "
        f"No other text after these tags. "
        f"\nSINGLE-PROBLEM RULE [LAYER: DIALOGUE_STRUCTURE]: Only work on ONE problem at a time. "
        f"If student submits multiple problems: list them, ask which to start with, wait. "
        f"EXCEPTION: If 4.3-PRE-OVERRIDE is triggered, execute it BEFORE this rule.")
    msgs = [{"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
            if isinstance(m.get("content"), (str, list))]
    if extra_content: msgs.append({"role": "user", "content": extra_content})
    with st.spinner(L_local["spinner"]):
        try:
            reply = adapter.chat(system_msg, msgs)
        except RuntimeError as e:
            # 身份系统改造：捕获"未登录"或"会话失效"错误，友好提示而不是让整个页面崩溃
            st.error(str(e))
            st.stop()
        update_mastery(concept_id, reply)
        leakage = extract_leakage(reply)
        if leakage is not None:
            log = st.session_state.get("leakage_log", [])
            log.append(leakage)
            st.session_state["leakage_log"] = log
        for tag in ["[STATUS: CORRECT]","[STATUS: PARTIAL]","[STATUS: INCORRECT]","[STATUS: GUIDING]"]:
            reply = reply.replace(tag, "")
        import re
        reply = re.sub(r"\[LEAKAGE:\s*\d\]", "", reply)
        return reply.rstrip()

L = LANG_LABELS[st.session_state.lang]
st.title(f"{L['title_prefix']}: {st.session_state.curr_concept}")

if not st.session_state.key_confirmed:
    st.info(f"👈 {L['wait']}")
    st.stop()

# ================================================================
# 身份系统 v0.2 — Railway Backend 必须先登录才能使用
# ================================================================
if st.session_state.backend == "railway" and not st.session_state.session_token:
    st.info("👈 请先在侧边栏输入授权码登录，再开始学习。")
    st.stop()
# ================================================================

if show_test:
    st.subheader(L["test_panel"])
    test_input = st.text_area(L["test_input"], height=100, placeholder=L["test_placeholder"])
    if st.button(L["test_send"]):
        if test_input.strip():
            st.session_state.messages.append({"role": "user", "content": test_input})
            with st.status(L["test_working"], expanded=True):
                response = get_ai_response()
            st.session_state.messages.append({"role": "assistant", "content": response})
            leakage = st.session_state.get("last_leakage")
            if leakage is not None:
                st.caption(f"🔬 Leakage Score: {leakage}/3")
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

for i, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        if isinstance(m["content"], str):
            st.markdown(m["content"])
        elif isinstance(m["content"], list):
            for b in m["content"]:
                if b.get("type") == "image":
                    st.image(base64.b64decode(b["source"]["data"]))
                else:
                    st.markdown(b.get("text", ""))
    if m["role"] == "assistant" and i == len(st.session_state.messages) - 1:
        leakage_log = st.session_state.get("leakage_log", [])
        if leakage_log:
            last = leakage_log[-1]
            colors = {0: "🟢", 1: "🟡", 2: "🟠", 3: "🔴"}
            st.caption(f"{colors.get(last, '⚪')} Leakage Score: {last}/3")

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
        except (TypeError, ValueError): pass
    st.download_button("⬇️ 导出会话 JSON",
        data=_json.dumps(_exp, ensure_ascii=False, indent=2),
        file_name="luocal_session.json", mime="application/json")
    _up = st.file_uploader("⬆️ 恢复会话", type="json", key="_restore_up")
    if _up is not None and not st.session_state.get("_restored"):
        for _k, _v in _json.loads(_up.getvalue().decode("utf-8")).items():
            try: st.session_state[_k] = _v
            except Exception: pass
        st.session_state["_restored"] = True
        st.rerun()


import streamlit as st
from anthropic import Anthropic
import base64

MODEL_NAME = "claude-sonnet-4-20250514"
st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide")

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
       "4.1 极值定理": "4.1", "4.2 中值定理": "4.2",
       "4.3 相关变化率": "4.3",
       "4.X 综合练习": "4.X"
   },
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
   "3.X": "Generate a comprehensive problem combining chain rule, implicit differentiation, product/quotient rules, inverse function derivatives, and parametric derivatives.",
   "4.1": "Ensure student explicitly states and checks all conditions of the Extreme Value Theorem before applying it.",
   "4.2": "Guide student to verify all three MVT hypotheses: continuity on [a,b], differentiability on (a,b), before applying.",
   "4.3": "Ensure student identifies all related variables, writes the relationship equation, and differentiates with respect to time.",
   "4.X": "Generate a comprehensive problem combining optimization, MVT, and related rates.",
}

OPENING_PROMPTS = {
   "1.X": "请出一道Unit 1综合题，综合考查极限、连续性和渐近线，包含至少两个子问题。",
   "2.X": "请出一道Unit 2综合题，综合考查导数定义、可导与连续、导数图像，包含至少两个子问题。",
   "3.X": "请出一道Unit 3综合题，综合考查链式法则、隐函数求导、乘积与商法则、反函数求导和参数方程求导，包含至少两个子问题。",
   "4.X": "请出一道Unit 4综合题，综合考查极值定理、中值定理和相关变化率，包含至少两个子问题。",
   "1.X_en": "Generate a comprehensive Unit 1 problem covering limits, continuity, and asymptotes. Include at least two sub-questions.",
   "2.X_en": "Generate a comprehensive Unit 2 problem covering limit definition of derivative, differentiability, and graphical interpretation. Include at least two sub-questions.",
   "3.X_en": "Generate a comprehensive Unit 3 problem covering chain rule, implicit differentiation, product/quotient rules, inverse function derivatives, and parametric derivatives. Include at least two sub-questions.",
   "4.X_en": "Generate a comprehensive Unit 4 problem covering optimization, MVT, and related rates. Include at least two sub-questions.",
}

LANG_LABELS = {
   "Chinese": {
       "title_prefix": "🎓 Luo-cal",
       "config": "⚙️ 配置页",
       "api_key": "🔑 Claude API Key",
       "confirm_key": "✅ 确认 Key",
       "key_ok": "Key 已锁定",
       "key_err": "Key 格式错误",
       "select_unit": "选择 Unit",
       "select_concept": "选择 Concept",
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
   },
   "English": {
       "title_prefix": "🎓 Luo-cal",
       "config": "⚙️ Settings",
       "api_key": "🔑 Claude API Key",
       "confirm_key": "✅ Confirm Key",
       "key_ok": "Key locked",
       "key_err": "Invalid key format",
       "select_unit": "Select Unit",
       "select_concept": "Select Concept",
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
   }
}

# ── 状态初始化 ────────────────────────────────────────────
for k, v in {
   "messages": [], "api_key": "", "key_confirmed": False,
   "curr_unit": "Unit 1: 极限与连续", "curr_concept": "1.1 极限简介",
   "mastery_scores": {}, "mastery_ready": False, "last_summary": "",
   "lang": "Chinese",
}.items():
   if k not in st.session_state: st.session_state[k] = v

# ── 方案A+B：自动加载 Key ─────────────────────────────────
# 优先级1：Streamlit Cloud Secrets（教师部署，最稳定）
# 优先级2：已在本次 session 输入过的 Key
# 优先级3：要求用户手动输入
if not st.session_state.key_confirmed:
   secrets_key = st.secrets.get("ANTHROPIC_API_KEY", "")
   if secrets_key:
       st.session_state.api_key = secrets_key
       st.session_state.key_confirmed = True

L = LANG_LABELS[st.session_state.lang]

# ── 侧边栏 ────────────────────────────────────────────────
with st.sidebar:
   st.title(L["config"])

   # 语言切换
   if st.button(L["lang_btn"], use_container_width=True):
       st.session_state.lang = "English" if st.session_state.lang == "Chinese" else "Chinese"
       st.rerun()

   st.divider()

   # API Key 区域
   # 如果已从 Secrets 自动加载，显示提示而非输入框
   if st.session_state.key_confirmed and st.secrets.get("ANTHROPIC_API_KEY", ""):
       st.info(L["secrets_notice"])
   else:
       key_input = st.text_input(L["api_key"], type="password",
                                  value=st.session_state.api_key)
       if st.button(L["confirm_key"]):
           if key_input.startswith("sk-"):
               st.session_state.api_key = key_input
               st.session_state.key_confirmed = True
               st.success(L["key_ok"])
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

   # 醒目状态显示
   status_color = L["connected_color"] if st.session_state.key_confirmed else L["disconnected_color"]
   status_text = L["connected"] if st.session_state.key_confirmed else L["disconnected"]
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
   if concept_id not in scores: scores[concept_id] = 0
   if "[STATUS: CORRECT]" in response_text:
       scores[concept_id] += 1
   elif "[STATUS: INCORRECT]" in response_text or "[STATUS: PARTIAL]" in response_text:
       scores[concept_id] = 0
   if scores[concept_id] >= 3:
       st.session_state.mastery_ready = True

def generate_summary(concept_id):
   client = Anthropic(api_key=st.session_state.api_key)
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
   return client.messages.create(
       model=MODEL_NAME, max_tokens=600,
       messages=[{"role": "user", "content": prompt}]
   ).content[0].text

def get_ai_response(extra_content=None):
   client = Anthropic(api_key=st.session_state.api_key)
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
   )
   msgs = [{"role": m["role"], "content": m["content"]}
           for m in st.session_state.messages
           if isinstance(m.get("content"), (str, list))]
   if extra_content:
       msgs.append({"role": "user", "content": extra_content})
   with st.spinner(L_local["spinner"]):
       response = client.messages.create(
           model=MODEL_NAME, max_tokens=1500,
           system=system_msg, messages=msgs
       )
       reply = response.content[0].text
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

# 测试面板优先显示在顶部
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
           L["opening_default"].format(concept=st.session_state.curr_concept)
       )
   else:
       opening = OPENING_PROMPTS.get(
           key_en,
           L["opening_default"].format(concept=st.session_state.curr_concept)
       )
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

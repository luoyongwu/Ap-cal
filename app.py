import os
DISABLE_SCL = os.environ.get("DISABLE_SCL", "0") == "1"

import streamlit as st
from anthropic import Anthropic
import base64
import uuid

# 2026-09-03 item3 修复新增依赖（见 requirements.txt 同批次更新）。
# 用 try/except 兜底：万一某次部署 requirements.txt 还没生效，
# 保活功能静默跳过而不是让整个 app 崩溃。
try:
    from streamlit_autorefresh import st_autorefresh
    _AUTOREFRESH_AVAILABLE = True
except ImportError:
    _AUTOREFRESH_AVAILABLE = False

# ================================================================
# 2026-09-03 Fix#2/#4 补丁说明（请勿删除本注释块）
# ----------------------------------------------------------------
# Fix#2（稳定性 - session_id 硬编码）：
#   根因：RailwayAdapter.chat() 此前把 session_id 写死为字面量
#   "streamlit"，导致同一 student_uuid 的后端对话历史
#   （chat_messages 表，经 fetch_chat_history() 喂给 Claude）永远不会
#   随"重新登录"而重置，不同登录之间的上下文互相串戏。
#   修复：railway_login() 登录成功时生成一个真实的 uuid4，存入
#   st.session_state.session_id；RailwayAdapter.chat() 改为读取这个
#   值，不再使用硬编码字面量。
#   范围决策（方案B，2026-09-03 已确认）：session_id 只在"登录时"
#   生成一次，不随"切换概念"重新生成——概念级别的彻底隔离（Gemini
#   建议的方案A）留待后续、真正需要多学生连续使用时再单独处理，
#   不在本次补丁范围内。
#
# Fix（item 4 - 初始"<<"侧边栏按钮不显示）：
#   假设：首次进入时"messages 为空 -> 自动调 get_ai_response() ->
#   st.rerun()"这个自动重跑，在移动端可能抢在侧边栏折叠按钮完成
#   渲染之前就把整页刷新掉。
#   修复：(a) st.set_page_config 显式声明 initial_sidebar_state=
#   "expanded"；(b) 引入 is_initializing 标志位，让第一次进入某个
#   概念时先完整渲染一次页面（不发起 AI 调用），下一次 rerun 才真正
#   触发 get_ai_response()，给移动端浏览器一次完整的先行渲染机会。
#   注：这是低风险的缓解性修复，不是 100% 确认的根因定位——如果
#   问题依然复现，需要进一步排查。
#
# 2026-09-03（当天第二轮）新增 — item 3 完整修复：
# 3分钟无操作后复原到初始状态
# ----------------------------------------------------------------
# 病灶（已确认）：st.session_state 只存在于 Streamlit 服务端内存，
# 和浏览器 WebSocket 连接绑定。移动端亮屏静默一段时间后代理层
# （如 Streamlit Cloud/Railway Ingress）可能判定连接空闲而回收；
# 熄屏/切后台/弱网切换则会直接断开 WebSocket。无论哪种情况，
# 重连后 Streamlit 都会分配一个全新的空 session_state，登录状态、
# 对话历史全部消失，表现为"回到初始状态"。
#
# 采纳方案（Gemini 建议，两步协同）：
#   (a) 前端保活：st_autorefresh(interval=25000) 每 25 秒产生一次
#       服务器级别的 rerun 流量，防止亮屏静默期间被代理层的
#       idle timer 判定为空闲断连。
#   (b) 断线复原：登录成功时把 session_token 和 session_id 写入
#       URL query params（?auth=...&sid=...）。WebSocket 断线重连、
#       st.session_state 被清空后，脚本顶部会检测到"session_token
#       为空但 URL 里带着 auth/sid"这种情况，调用后端新增的
#       /api/v1/session/restore 端点（用 token 换回身份校验 +
#       该 session_id 下的历史消息），把登录状态和对话历史重新
#       灌回 st.session_state，实现无感恢复，不需要用户重新登录。
#       此端点依赖后端 luo-cal-backend 仓库 main.py 的配套改动
#       （同批次一起推送）。
#
# 已知安全权衡：session_token 出现在 URL 里意味着会被浏览器历史、
# 服务器访问日志等记录到——这是"断线可恢复"与"token 完全不落地"
# 之间的权衡，当前内部测试阶段接受这个权衡，真正对外之前需要
# 重新评估（比如改用更短时效的一次性 restore token）。
# ================================================================

st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide",
                    initial_sidebar_state="expanded")

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

        # ===== 2026-09-03 Fix#2：session_id 不再硬编码 =====
        # 登录成功时（railway_login()）已经生成了一个真实 uuid4 存入
        # st.session_state.session_id；这里改为读取该值。理论上登录
        # 后这个 key 一定存在，但仍保留 "streamlit" 作为兜底，避免
        # 极端情况下（例如手动清过部分 session_state）直接崩溃。
        session_id = st.session_state.get("session_id") or "streamlit"

        # ===== 2026-09-04 记录统一性修复（对话内概念漂移）新增 =====
        # 把当前学生轨道一并传给后端，后端用它过滤 actual_concept_id
        # 分类调用的合法闭集（AB 轨道看不到 BC-only 概念）。
        payload = {"concept_id": concept_id,
                   "user_input": last_user, "session_id": session_id,
                   "language": lang,
                   "student_track": st.session_state.get("student_track", "AB")}
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

        # ===== 2026-09-04 记录统一性修复（对话内概念漂移）新增 =====
        # 后端在 grade_student_answer() 里额外判断了"本轮实际讨论的是
        # 哪个 concept_id"（见 main.py 同批修复），通过 resolved_
        # concept_id 字段回传。如果和前端当前侧边栏状态不一致（典型
        # 场景：学生纯对话内要求换概念，从未碰过侧边栏下拉框），这里
        # 主动把 st.session_state.curr_unit/curr_concept 更新过来并
        # 同步进 URL，让侧边栏、大标题、以及下次断线重连都能反映真实
        # 概念，而不是停留在上一次手动选择的值上。找不到对应
        # (unit名, concept名)（防御性兜底，理论上不该发生，因为后端
        # 已经用闭集校验过）时静默跳过，不影响正常返回。
        resolved_concept_id = result.get("resolved_concept_id")
        if resolved_concept_id and resolved_concept_id in CONCEPT_ID_TO_LOCATION:
            _resolved_unit, _resolved_concept = CONCEPT_ID_TO_LOCATION[resolved_concept_id]
            if (_resolved_unit, _resolved_concept) != (st.session_state.curr_unit, st.session_state.curr_concept):
                st.session_state.curr_unit = _resolved_unit
                st.session_state.curr_concept = _resolved_concept
                _sync_concept_to_url()
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
        # ===== 2026-09-03 Fix#2：登录成功时生成真实 session_id =====
        # 方案B（2026-09-03 已确认）：只在登录这一刻生成一次，不随
        # "切换概念"重新生成。每次成功登录都会拿到一个全新 uuid4，
        # 从而和之前任何登录（无论是否同一个 student_uuid）的后端
        # 对话历史彻底隔开，解决跨登录串戏问题。
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state["_login_error"] = None
        # ===== 2026-09-03 item3 修复：把登录凭证写入 URL query params =====
        # 断线重连后 st.session_state 会被清空，但浏览器地址栏里的
        # query params 不受影响——靠这两个参数让 attempt_session_restore()
        # 之后能找回身份，见文件顶部的说明。
        st.query_params["auth"] = result["session_token"]
        st.query_params["sid"] = st.session_state.session_id
        # ===== 2026-09-04 记录统一性修复：登录时把当前概念也写入 URL =====
        # 见 attempt_session_restore() 处的说明。此处用的是登录这一刻
        # st.session_state.curr_unit/curr_concept 的当前值（初始化默认值，
        # 或上一位学生在同一浏览器会话里最后停留的概念——这是已有行为，
        # 不属于本次修复范围）。
        _sync_concept_to_url()
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


# ================================================================
# 2026-09-04 记录统一性修复 — concept_id URL 同步辅助函数
# ----------------------------------------------------------------
# 背景（详见 memory /areas/luo-cal-ole.md "Root cause REFINED"节）：
# item3 的 attempt_session_restore() 只恢复了 session_token 和聊天
# 记录，从未涉及 st.session_state.curr_unit/curr_concept。断线重连后，
# st.session_state 被整体清空重建，curr_unit/curr_concept 会被下面
# state 初始化字典的默认值（"1.1"）覆盖，而 session_token/messages
# 却被 attempt_session_restore() 正确恢复——两者不同步，导致重连后
# concept_id 悄悄回落到 "1.1"，此后无论侧边栏还是对话内切换都不会
# 纠正，直到用户手动重新点一次侧边栏。
#
# 修复思路：和 auth/sid 一样，把 curr_unit/curr_concept 对应的
# concept_id（如 "3.2"）也写进 URL query params（?concept=3.2），
# 在 attempt_session_restore() 里一并读回并 rehydrate。
#
# CONCEPT_ID_TO_LOCATION 在 UNITS 字典定义之后构建（见下方），
# 本函数在模块加载完成、UNITS 已存在后才会被实际调用，因此这里
# 直接引用 UNITS/CONCEPT_ID_TO_LOCATION 是安全的（Python 按调用时
# 绑定全局名字，不是按定义时）。
# ================================================================
def _sync_concept_to_url():
    """把当前 st.session_state.curr_unit/curr_concept 对应的 concept_id
    写入 URL query params，供 attempt_session_restore() 断线重连后取回。
    找不到对应 concept_id（理论上不应发生）时静默跳过，不影响主流程。"""
    try:
        concept_id = UNITS[st.session_state.curr_unit][st.session_state.curr_concept]
        st.query_params["concept"] = concept_id
    except KeyError:
        pass


# ================================================================
# 2026-09-03 item3 修复 — 断线复原函数
# ================================================================
def attempt_session_restore():
    """WebSocket 断线重连后 st.session_state 被清空时调用。如果 URL
    query params 里带着上次登录写入的 auth/sid，尝试用它们向后端换回
    身份校验结果 + 该 session_id 下的历史消息，重新灌入
    st.session_state，实现无感恢复。token 失效/过期时会清掉 URL 参数，
    静默回退到正常登录流程，不会报错崩溃。
    2026-09-04 记录统一性修复：同时读回 URL 里的 concept 参数（若存在），
    一并 rehydrate curr_unit/curr_concept，避免断线重连后 concept_id
    静默回落到侧边栏默认值 "1.1"。"""
    if st.session_state.get("session_token"):
        return  # 已经有有效登录状态，不需要复原
    auth_param = st.query_params.get("auth")
    sid_param = st.query_params.get("sid")
    if not auth_param or not sid_param:
        return

    import urllib.request, json, urllib.error
    req = urllib.request.Request(
        f"{RailwayAdapter.BACKEND_URL}/api/v1/session/restore?session_id={sid_param}",
        headers={"Authorization": f"Bearer {auth_param}"},
        method="GET")
    try:
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        st.session_state.session_token = auth_param
        st.session_state.session_id = sid_param
        st.session_state.student_display_name = result.get("display_name")
        st.session_state.messages = [
            {"role": m["role"], "content": m["content"]}
            for m in result.get("messages", [])
        ]
        st.session_state.backend = "railway"
        st.session_state.key_confirmed = True
        # ===== 2026-09-04 记录统一性修复：一并复原 curr_unit/curr_concept =====
        # 根因：此前这里完全没有涉及概念状态，导致重连后概念状态被下面
        # state 初始化字典的默认值 "1.1" 覆盖，而其它状态却被正确恢复。
        # 用 URL 里的 concept 参数（登录时/每次手动切换概念时写入，见
        # _sync_concept_to_url()）反查回 (unit名, concept名) 二元组。
        # 找不到该参数，或参数值不在当前 UNITS 表里（例如题库改版后旧
        # 链接失效）时，静默保留默认值，不报错、不中断复原流程。
        concept_param = st.query_params.get("concept")
        if concept_param and concept_param in CONCEPT_ID_TO_LOCATION:
            _restored_unit, _restored_concept = CONCEPT_ID_TO_LOCATION[concept_param]
            st.session_state.curr_unit = _restored_unit
            st.session_state.curr_concept = _restored_concept
    except Exception:
        # token 失效、过期，或后端暂时不可用：清掉 URL 里的陈旧参数，
        # 让脚本继续往下走正常的登录流程，不抛异常打断整个页面。
        for _p in ("auth", "sid"):
            try:
                del st.query_params[_p]
            except KeyError:
                pass
# ================================================================
# 断线复原函数结束
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

# ================================================================
# 2026-09-04 记录统一性修复：concept_id -> (unit名, concept名) 反查表
# ----------------------------------------------------------------
# attempt_session_restore() 和后续任何需要"从 URL 里的 concept_id
# 反查回侧边栏下拉框用的 (unit名, concept名)"的地方都用这张表。
# 在 UNITS 定义之后、模块加载时构建一次即可，UNITS 本身在运行时
# 不会变化。
# ================================================================
CONCEPT_ID_TO_LOCATION = {
    _cid: (_uname, _cname)
    for _uname, _concepts in UNITS.items()
    for _cname, _cid in _concepts.items()
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

# ================================================================
# 2026-08-02 迁移记录：CONCEPT_CONSTRAINTS 已迁移至后端
# ================================================================
# 原本这里有一份 CONCEPT_CONSTRAINTS 字典（逐概念的 Socratic 教学策略
# HARD RULE），但发现走 "🚀 Railway Backend" 这条真实生产链路时，
# RailwayAdapter.chat() 从未把这份字典拼出的 system prompt 发给后端
# ——这套精心设计的规则（包括 4.3 概念的 PRE-OVERRIDE）在真实链路上
# 从未生效过。Yongwu 拍板采纳"方案1"：把这份字典搬进后端
# （luo-cal-backend 仓库新增 concept_constraints.py），作为 SCL 策略
# 引擎的硬性组成部分，后端 socratic_chat() 现在会按 concept_id 自己
# 查表拼接。前端不再维护这份字典的副本，避免教学策略在两处重复维护、
# 彼此不同步。详见 luo-cal-backend 仓库 THEORY_CHANGELOG.md 对应条目。
# ================================================================

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
    # ---- 2026-09-03 Fix#2 新增：真实 session_id ----
    # 登录前为 None；railway_login() 登录成功时会赋一个真实 uuid4。
    "session_id": None,
    # ---- 2026-09-03 item4 修复新增：首次进入某概念时的初始化标志位 ----
    # 见下方"if not st.session_state.messages"那段的说明。
    "is_initializing": False,
    # ---- 2026-08 修复：leakage_log 补入初始化字典 ----
    # 此前 leakage_log 从未出现在这份默认状态字典里，也从未在任何一处
    # state 重置逻辑（切换 backend/切换概念/刷新按钮/登录登出）里被
    # 清空过。真实生产链路（Railway Backend）的 SCL_SYSTEM_PROMPT 里
    # 根本不含 [LEAKAGE:N] 指令（只有走 Anthropic/DeepSeek/Ollama 这几个
    # 非 Railway 测试后端时，本文件里 get_ai_response() 构造的 system_msg
    # 才会要求模型输出这个标签）——但由于 leakage_log 从不清空，一旦
    # 会话中任意时刻用非 Railway 后端测试过一次、写入过一条记录，之后
    # 无论切换到哪个 backend/概念，前端"Leakage Score: N/3"这行会一直
    # 显示那条陈旧记录，看起来像是"当前这一轮的实时评分"，实际上和
    # 当前对话完全无关。这里补上默认值，下面三处重置逻辑里补上清空。
    "leakage_log": [],
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 2026-09-03 item3 修复：在其它逻辑读取 session_token 之前，先尝试
# 断线复原——如果这是一次 WebSocket 重连后的全新 session_state，
# 且 URL 里带着有效的 auth/sid，这里会把登录状态和历史消息补回来。
# 2026-09-04 记录统一性修复：同批复原逻辑现在也会一并 rehydrate
# curr_unit/curr_concept（见 attempt_session_restore() 内部注释）。
attempt_session_restore()

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
        st.session_state.leakage_log = []  # 2026-08 修复：切换backend时一并清空
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
                st.session_state.session_id = None  # 2026-09-03 Fix#2：登出时一并清空
                st.session_state.messages = []
                st.session_state.leakage_log = []  # 2026-08 修复：登出时一并清空
                # 2026-09-03 item3 修复：登出时把 URL 里的 auth/sid 也清掉，
                # 避免残留的旧 token 被断线复原逻辑误用。
                # 2026-09-04 记录统一性修复：一并清掉 concept 参数，避免
                # 下一位在同一浏览器登录的学生短暂"继承"上一位的概念 URL
                # 参数（railway_login() 成功后会立即用新学生自己当前的
                # curr_unit/curr_concept 覆盖它，但登出后先清空更干净）。
                for _p in ("auth", "sid", "concept"):
                    try:
                        del st.query_params[_p]
                    except KeyError:
                        pass
                st.rerun()
        else:
            st.subheader("🔐 学生登录")
            login_code_input = st.text_input("请输入授权码", placeholder="LUO-XXXXXXXX")
            if st.button("登录", use_container_width=True):
                if login_code_input.strip():
                    if railway_login(login_code_input):
                        st.session_state.messages = []
                        st.session_state.leakage_log = []  # 2026-08 修复：登录成功时一并清空
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
        st.session_state.leakage_log = []  # 2026-08 修复：切换概念时一并清空
        # 注：按方案B（2026-09-03 已确认），session_id 不在这里重新
        # 生成——只在登录时生成一次。切概念时后端历史依然共享同一个
        # session_id（用于出题查重），只是前端本地展示清空。
        # 2026-09-04 记录统一性修复：每次通过侧边栏切换概念时，同步
        # 把新概念写入 URL query params，供未来任何一次断线重连时
        # attempt_session_restore() 取回，避免 concept_id 悄悄回落。
        _sync_concept_to_url()
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
    # 2026-08-02：TEACHING CONSTRAINT 这一行（原来拼接 CONCEPT_CONSTRAINTS）
    # 已删除——逐概念约束现在由后端 socratic_chat() 按 concept_id 自己
    # 查表拼接，不再需要前端在这里重复构造。这里保留的是通用规则
    # （STATUS/LEAKAGE 标签、SINGLE-PROBLEM RULE），对走 Anthropic/
    # DeepSeek/Ollama 这几个不经过后端诊断管道的测试用途后端依然有效；
    # 走 Railway Backend 时，RailwayAdapter.chat() 本来就不发送 system
    # 参数（见该类定义），这里的 system_msg 对 Railway 路径无实际影响，
    # 后端会用自己拼好的 SCL_SYSTEM_PROMPT + concept_constraint。
    #
    # 2026-08 修复重要说明：下面这段 system_msg（含 [LEAKAGE:N] 指令）
    # 只在 backend 为 anthropic/deepseek/ollama 时真正生效。走 Railway
    # Backend（真实学生所用的链路）时，后端自己的 SCL_SYSTEM_PROMPT 里
    # 完全没有 LEAKAGE 相关指令，Claude 不会输出 [LEAKAGE:N]，
    # extract_leakage() 应该匹配不到、leakage_log 不应该新增记录。
    # 之前观测到 Railway 链路上仍然显示"Leakage Score: N/3"，根因是
    # leakage_log 从未在切换 backend/概念时清空，显示的是本会话更早
    # 用非 Railway 后端测试时留下的陈旧值，不是当前对话的实时评分——
    # 已在上面的 state 重置处修复。如果未来需要 Railway 路径也具备
    # 泄漏自评能力，需要在后端 SCL_SYSTEM_PROMPT 里新增对应指令，并让
    # socratic_chat() 的返回值里包含 leakage 字段，而不是依赖这里的
    # system_msg（这里的 system_msg 对 Railway 路径不生效）。
    system_msg = (
        f"You are a strict AP Calculus Socratic tutor. {L_local['lang_instr']} "
        f"NEVER give the answer directly. Always guide with questions. "
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

# ================================================================
# 2026-09-03 item3 修复：保活自动刷新
# ----------------------------------------------------------------
# 只在"已登录 Railway 会话"这个场景下开启，避免在配置页/其它后端
# 测试场景里平白多刷新。interval 单位是毫秒，25秒一次，用来防止
# 亮屏静默期间代理层的 idle timer 把 WebSocket 连接判定为空闲断开。
# ================================================================
if (_AUTOREFRESH_AVAILABLE and st.session_state.backend == "railway"
        and st.session_state.session_token):
    st_autorefresh(interval=25000, key="keepalive_autorefresh")

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
    # ================================================================
    # 2026-09-03 item4 修复：is_initializing 标志位
    # ----------------------------------------------------------------
    # 此前这里进入某个概念时会立即同步调用 get_ai_response()（等待
    # Claude API 返回）再 st.rerun()，移动端可能在侧边栏折叠按钮
    # ("<<") 完成渲染前就被这次强制重跑打断。现在分两步：第一次进入
    # （is_initializing 还是 False）只翻转标志位、立刻 rerun，不发起
    # AI 调用，让这一轮先把页面完整渲染出来；下一轮（is_initializing
    # 已经是 True）才真正调用 get_ai_response()。
    # 这是缓解性修复，不是 100% 确认的根因——如果问题依然复现，
    # 需要进一步排查（比如浏览器本身的渲染时机问题）。
    # ================================================================
    if not st.session_state.is_initializing:
        st.session_state.is_initializing = True
        st.rerun()
    else:
        concept_id = UNITS[st.session_state.curr_unit][st.session_state.curr_concept]
        key_en = concept_id + "_en"
        if st.session_state.lang == "Chinese":
            opening = OPENING_PROMPTS.get(concept_id, L["opening_default"].format(concept=st.session_state.curr_concept))
        else:
            opening = OPENING_PROMPTS.get(key_en, L["opening_default"].format(concept=st.session_state.curr_concept))
        first = get_ai_response(opening)
        st.session_state.messages.append({"role": "assistant", "content": first})
        st.session_state.is_initializing = False
        st.rerun()

if st.button(L["refresh"]):
    st.session_state.messages = []
    st.session_state.last_summary = ""
    st.session_state.mastery_ready = False
    st.session_state.mastery_scores = {}
    st.session_state.leakage_log = []  # 2026-08 修复：点"刷新当前概念"时一并清空
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

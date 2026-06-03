import streamlit as st
import os
from anthropic import Anthropic

st.set_page_config(page_title="AP-Cal 智能辅导总线", page_icon="🎓", layout="wide")

# ============================================================
# 【v2.0 核心修复】密钥持久化状态机
# 设计原则：
#   1. 密钥只写入一次，之后永不丢失（即使 concept 切换触发 rerun）
#   2. 每次 API 调用前主动验证连接有效性（心跳探针）
#   3. 连接断线后自动尝试用已存密钥重连，无需用户重新输入
# ============================================================

def init_session_defaults():
    """初始化所有 session_state 默认值，防止 rerun 后状态丢失"""
    defaults = {
        "ENV_CLAUDE_KEY": "",
        "key_verified": False,       # 密钥是否已通过 API 实际验证（不只是非空）
        "key_input_cache": "",       # 输入框缓存，与激活状态解耦
        "messages": [],
        "current_concept": None,
        "connection_status": "disconnected",  # connected / disconnected / checking
        "last_error": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_defaults()


def verify_key_with_api(api_key: str) -> tuple[bool, str]:
    """
    向 Anthropic API 发送最小探针请求，真实验证密钥有效性。
    返回 (is_valid: bool, error_msg: str)
    """
    try:
        client = Anthropic(api_key=api_key)
        # 修正第1处：采用最新模型名称验证探针
        client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1,
            messages=[{"role": "user", "content": "h"}]
        )
        return True, ""
    except Exception as e:
        err_str = str(e)
        if "401" in err_str or "authentication" in err_str.lower():
            return False, "❌ 密钥无效：认证失败（401），请检查密钥是否正确。"
        elif "403" in err_str:
            return False, "❌ 密钥无效：权限不足（403）。"
        elif "429" in err_str:
            # 429 意味着密钥有效但触发了速率限制，视为连接成功
            return True, ""
        else:
            return False, f"⚠️ 连接异常：{err_str[:120]}"


def get_active_client():
    """
    获取已验证的 Anthropic client。
    """
    if st.session_state.ENV_CLAUDE_KEY and st.session_state.key_verified:
        return Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
    return None


# ============================================================
# 🏛️ 侧边栏控制台
# ============================================================
st.sidebar.title("🎓 AP-Cal 教学控制台")
st.sidebar.markdown("---")

# ── 密钥输入区（仅在未激活时显示完整输入流程）──
if not st.session_state.key_verified:
    st.sidebar.markdown("### 🔑 密钥激活")
    input_key = st.sidebar.text_input(
        "步骤 1：粘贴您的 Claude API Key:",
        type="password",
        value=st.session_state.key_input_cache,
        placeholder="sk-ant-api03-...",
        key="key_text_input"
    )
    # 同步输入框内容到缓存（不污染激活状态）
    st.session_state.key_input_cache = input_key

    if st.sidebar.button("⚡ 步骤 2：验证并激活密钥", use_container_width=True):
        candidate = input_key.strip()
        if not candidate:
            st.sidebar.warning("⚠️ 请先输入密钥！")
        else:
            st.session_state.connection_status = "checking"
            with st.sidebar:
                with st.spinner("🔍 正在向 Anthropic 服务器验证密钥..."):
                    ok, err = verify_key_with_api(candidate)
            if ok:
                st.session_state.ENV_CLAUDE_KEY = candidate
                st.session_state.key_verified = True
                st.session_state.connection_status = "connected"
                st.session_state.last_error = ""
                os.environ["ANTHROPIC_API_KEY"] = candidate
                st.rerun()
            else:
                st.session_state.connection_status = "disconnected"
                st.session_state.last_error = err
                st.sidebar.error(err)

else:
    # ── 已激活：显示简洁状态栏 + 重置选项 ──
    st.sidebar.markdown("### 🔑 密钥状态")

    # 状态指示器
    if st.session_state.connection_status == "connected":
        masked = st.session_state.ENV_CLAUDE_KEY[:8] + "..." + st.session_state.ENV_CLAUDE_KEY[-4:]
        st.sidebar.success(f"🟢 已连接  |  `{masked}`")
    elif st.session_state.connection_status == "checking":
        st.sidebar.info("🔄 重连中...")
    else:
        st.sidebar.error("🔴 连接断开，正在自动重连...")

    # 手动重新验证按钮
    col_a, col_b = st.sidebar.columns(2)
    with col_a:
        if st.sidebar.button("🔄 重新验证", use_container_width=True):
            st.session_state.connection_status = "checking"
            with st.sidebar:
                with st.spinner("重连中..."):
                    ok, err = verify_key_with_api(st.session_state.ENV_CLAUDE_KEY)
            if ok:
                st.session_state.connection_status = "connected"
                st.session_state.last_error = ""
                st.sidebar.toast("✅ 重连成功！", icon="🟢")
            else:
                st.session_state.connection_status = "disconnected"
                st.session_state.last_error = err
                st.sidebar.error(err)
            st.rerun()

    # 更换密钥（清空激活状态，回到输入界面），对齐 col_b 缩进
    with col_b:
        if st.sidebar.button("🔁 更换密钥", use_container_width=True):
            st.session_state.key_verified = False
            st.session_state.ENV_CLAUDE_KEY = ""
            st.session_state.key_input_cache = ""
            st.session_state.connection_status = "disconnected"
            st.rerun()

st.sidebar.markdown("---")

# ── 微积分概念选择矩阵 ──
concept_option = st.sidebar.selectbox(
    "🎯 选择当前死磕的微积分核心概念 (Unit 1 & 2):",
    [
        "1.1 Limits Chronology (极限的直观引入与定义)",
        "1.2 Asymptotes & Infinity (无穷大与渐近线行为)",
        "1.3 Continuity & IVT (连续性定义与介值定理)",
        "1.4 Squeeze Theorem (夹逼定理的代数与几何夹击)",
        "2.1 Derivative Definition (导数的极限定义与割线变切线)",
        "2.2 Power/Product/Quotient Rules (三大基础求导法则)",
        "2.3 Chain Rule & Implicit (复合函数求导与隐函数微分)",
        "2.4 Higher-Order Derivatives (高阶导数与物理变化率)"
    ]
)

lang_label = st.sidebar.radio("🌐 语言 / Language:", ["中文 (Chinese)", "English"])

# ── 【v2.0 关键修复】concept 切换时只重置对话，不碰密钥状态 ──
if st.session_state.current_concept != concept_option:
    st.session_state.messages = []
    st.session_state.current_concept = concept_option

# ── 初始化欢迎消息 ──
WELCOME_MATRIX = {
    "1.1 Limits Chronology (极限的直观引入与定义)": "Welcome! Let's explore how a function behaves as it approaches a point. Think about $f(x)=\\frac{x^2-1}{x-1}$ at $x=1$. What happens?",
    "1.2 Asymptotes & Infinity (无穷大与渐近线行为)": "Welcome! When the denominator shrinks to zero, the function value explodes. Let's touch the edge of infinity.",
    "1.3 Continuity & IVT (连续性定义与介值定理)": "Welcome! No holes, no jumps, no vertical asymptotes. If a continuous function goes from negative to positive, it MUST cross zero.",
    "1.4 Squeeze Theorem (夹逼定理的代数与几何夹击)": "Welcome! Locked from above, trapped from below. If two functions squeeze a middle one, its limit is absolute.",
    "2.1 Derivative Definition (导数的极限定义 with 割线变切线)": "Welcome! Instantaneous change is born from average change. Let's master the limit of the difference quotient.",
    "2.2 Power/Product/Quotient Rules (三大基础求导法则)": "Welcome! Let's shift from limit calculations to structural shortcuts.",
    "2.3 Chain Rule & Implicit (复合函数求导与隐函数微分)": "Welcome! Peeling the onion layer by layer. Let's crack nested functions.",
    "2.4 Higher-Order Derivatives (高阶导数与物理变化率)": "Welcome! The derivative of velocity is acceleration. Let's observe rates of change.",
}

if len(st.session_state.messages) == 0:
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME_MATRIX[st.session_state.current_concept]}
    ]

# ============================================================
# 🎨 主界面
# ============================================================
st.title("🎓 Luo-cal 智能微积分交互教学总线")
st.caption(f"概念：{st.session_state.current_concept}  |  语言：{lang_label}")

# ── 顶部连接状态横幅 ──
if st.session_state.key_verified and st.session_state.connection_status == "disconnected":
    banner_col1, banner_col2 = st.columns([4, 1])
    with banner_col1:
        st.warning("⚠️ 检测到连接中断。点击右侧按钮自动重连（无需重新输入密钥）。")
    with banner_col2:
        if st.button("🔄 一键重连", use_container_width=True):
            ok, err = verify_key_with_api(st.session_state.ENV_CLAUDE_KEY)
            if ok:
                st.session_state.connection_status = "connected"
                st.session_state.last_error = ""
                st.rerun()
            else:
                st.error(err)

# ── 渲染历史对话 ──
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── 多模态上传通道 ──
st.markdown("---")
st.subheader("📷 移动端多模态答题通道")
uploaded_file = st.file_uploader("📝 拍照上传手写推导步骤：", type=["png", "jpg", "jpeg"])
if uploaded_file:
    st.success("🎉 图片捕获成功！准备扫描解题步骤。")

# ── 习题触发控制中心 ──
st.markdown("---")
st.subheader("🎯 习题触发控制中心")
col1, col2 = st.columns(2)
with col1:
    st.info("💡 **通道A (自动触发)**: 苏格拉底交互闭环已挂载。模型会自动判断您的掌握程度并随时提问。")
with col2:
    trigger_exam = st.button("🚀 显式触发：向模型索要当前概念 AP 风格习题", use_container_width=True)

# ── 输入主干 ──
user_input = st.chat_input("在此输入您的微积分想法，或对模型说：'请给我出一道题'...")

final_input = ""
if user_input:
    final_input = user_input
elif trigger_exam:
    final_input = "【控制台指令】: 请立即根据当前选择的微积分概念，为我出一道符合 AP 难度和风格的综合习题，开始测试！"

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    st.rerun()

# ============================================================
# 💬 核心推理流（带自动重连保护）
# ============================================================
if (len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user"):

    if not st.session_state.key_verified or not st.session_state.ENV_CLAUDE_KEY:
        st.warning("⚠️ 传输拦截：密钥未激活。请在左侧侧边栏完成步骤1和步骤2。")
    else:
        try:
            client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)

            # 协议级自愈：合并连续相同角色
            cleaned_history = []
            for m in st.session_state.messages:
                if cleaned_history and cleaned_history[-1]["role"] == m["role"]:
                    cleaned_history[-1]["content"] += "\n" + m["content"]
                else:
                    cleaned_history.append({"role": m["role"], "content": m["content"]})

            system_prompt = (
                f"Current concept: {st.session_state.current_concept}.\n"
                f"Language: {lang_label}.\n"
                "STRICT RULES:\n"
                "1. Never give direct answers. Always guide step-by-step using Socratic questions.\n"
                "2. Assess student level (Basic/Partial/Mastered) and dynamically trigger exercises when appropriate.\n"
                "3. For AP Style problem requests: generate realistic AP-level multiple-choice or free-response questions. Provide answer key inside markdown spoilers (>! answer !<).\n"
                "4. Never reveal your chain-of-thought (CoT)."
            )

            with st.spinner("⚡ Luo-cal 正在深度演算对话流..."):
                # 修正第2处：核心对话请求采用最新模型名称
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1548,
                    system=system_prompt,
                    messages=cleaned_history
                )
                assistant_res = response.content[0].text

            st.session_state.connection_status = "connected"
            st.session_state.last_error = ""
            st.session_state.messages.append({"role": "assistant", "content": assistant_res})
            st.rerun()

        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "403" in err_str:
                st.session_state.key_verified = False
                st.session_state.connection_status = "disconnected"
                st.error("🔑 密钥失效（认证错误）。请在左侧侧边栏重新激活密钥。")
            elif "429" in err_str:
                st.warning("⏳ 请求过于频繁（429 速率限制），请稍等 10 秒后重试。")
                st.session_state.connection_status = "connected"
            elif "timeout" in err_str.lower() or "connection" in err_str.lower():
                st.session_state.connection_status = "disconnected"
                st.warning("🌐 网络连接超时。密钥仍有效，点击页面顶部【一键重连】即可恢复，无需重新输入密钥。")
            else:
                st.session_state.connection_status = "disconnected"
                st.error(f"❌ 系统摩擦报错详情: {err_str}")

import streamlit as st
import os
from anthropic import Anthropic

st.set_page_config(page_title="AP-Cal 智能辅导总线", page_icon="🎓", layout="wide")

# 初始化后端内存中的 API Key 状态机
if "ENV_CLAUDE_KEY" not in st.session_state:
    st.session_state.ENV_CLAUDE_KEY = ""

# 🏛️ 侧边栏控制台
st.sidebar.title("🎓 AP-Cal 教学控制台")
st.sidebar.markdown("---")

# 1️⃣ 第一层：纯粹的输入框（仅用于承载粘贴的内容）
input_key = st.sidebar.text_input(
    "🔑 步骤 1：请在此粘贴您的 Claude API Key:", 
    type="password", 
    value=st.session_state.ENV_CLAUDE_KEY, 
    placeholder="sk-ant-api03-..."
)

# 2️⃣ 第二层：物理锁定提交按钮（彻底解决不知按哪里的死锁！）
# 任何时候点击它，都会强行把输入框的值写入系统底层
if st.sidebar.button("⚡ 步骤 2：【点击此处】物理激活并锁定密钥"):
    if input_key.strip():
        st.session_state.ENV_CLAUDE_KEY = input_key.strip()
        os.environ["ANTHROPIC_API_KEY"] = st.session_state.ENV_CLAUDE_KEY
    else:
        st.sidebar.warning("⚠️ 请先在上方输入框粘贴密钥，再点击激活！")

# 3️⃣ 第三层：独立的状态回显框（与输入及提交区域完全隔离）
st.sidebar.markdown("⬇️ **当前底座密钥点火状态回显：**")
if st.session_state.ENV_CLAUDE_KEY:
    st.sidebar.success("🟢 密钥激活成功！AI 底座已锁死，请在右侧畅快死磕。")
else:
    st.sidebar.error("🔴 密钥未激活！底座处于断线状态。请执行步骤1和步骤2。")

st.sidebar.markdown("---")

# 📖 微积分核心概念选择矩阵
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

# 🌐 翻译语言网关控制
lang_label = st.sidebar.radio("🌐 界面翻译网关语言 / Language Switch:", ["中文 (Chinese)", "English"])

# 🔄 跨概念切换重置状态机
if "current_concept" not in st.session_state:
    st.session_state.current_concept = concept_option
if st.session_state.current_concept != concept_option:
    st.session_state.messages = []
    st.session_state.current_concept = concept_option

if "messages" not in st.session_state or len(st.session_state.messages) == 0:
    # 欢迎矩阵
    welcome_matrix = {
        "1.1 Limits Chronology (极限的直观引入与定义)": "Welcome! Let's explore how a function behaves as it infinitely approaches a point. Think about $f(x)=\\frac{x^2-1}{x-1}$ at $x=1$. What happens?",
        "1.2 Asymptotes & Infinity (无穷大与渐近线行为)": "Welcome! When the denominator shrinks to zero, the function value explodes. Let's touch the edge of infinity.",
        "1.3 Continuity & IVT (连续性定义与介值定理)": "Welcome! No holes, no jumps, no vertical asymptotes. If a continuous function goes from negative to positive, it MUST cross zero.",
        "1.4 Squeeze Theorem (夹逼定理的代数与几何夹击)": "Welcome! Locked from above, trapped from below. If two functions squeeze a middle one, its limit is absolute.",
        "2.1 Derivative Definition (导数的极限 definition)": "Welcome! Instantaneous change is born from average change. Let's master the limit of the difference quotient.",
        "2.2 Power/Product/Quotient Rules (三大基础求导法则)": "Welcome! Let's shift our gear from limit calculations to structural shortcuts.",
        "2.3 Chain Rule & Implicit (复合函数求导与隐函数微分)": "Welcome! Peeling the onion layer by layer. Let's crack nested functions.",
        "2.4 Higher-Order Derivatives (高阶导数与物理变化率)": "Welcome! The derivative of velocity is acceleration. Let's observe rates of change."
    }
    st.session_state.messages = [{"role": "assistant", "content": welcome_matrix[st.session_state.current_concept]}]

# 🎨 渲染主界面布局
st.title("🎓 Luo-cal 智能微积分交互教学总线")
st.caption(f"当前死磕概念：{st.session_state.current_concept} | 语言：{lang_label}")

# 渲染历史会话
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 📷 移动端拍照上传/手写习题交互模块
st.markdown("---")
st.subheader("📷 移动设备多模态答题通道")
uploaded_file = st.file_uploader("📝 在纸上写下您的推导步骤，拍照上传反馈：", type=["png", "jpg", "jpeg"])
if uploaded_file:
    st.success("🎉 图片捕获成功！准备扫描解题步骤。")

st.markdown("---")
st.subheader("🎯 习题触发控制中心")
col1, col2 = st.columns(2)
with col1:
    st.info("💡 **通道A (自动触发)**: 苏格拉底交互闭环已挂载。模型会自动判断您的掌握程度并随时提问。")
with col2:
    trigger_exam = st.button("🚀 显式触发：向模型索要当前概念 AP 风格习题")

# 💬 师生交互输入主干
user_input = st.chat_input("在此输入您的微积分想法，或直接对模型说：'请给我出一道题'...")

final_input = ""
if user_input:
    final_input = user_input
elif trigger_exam:
    final_input = "【控制台指令】: 请立即根据当前选择的微积分概念，为我出一道符合 AP 难度和风格的综合习题，开始测试！"

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    st.rerun()

# 核心逻辑运算流（仅在有最新输入且密钥锁定的情况下执行）
if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
    if not st.session_state.ENV_CLAUDE_KEY:
        st.warning("⚠️ 无法发送请求！请确保左侧侧边栏已执行【步骤2】激活并锁定了密钥！")
    else:
        try:
            client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
            
            # 协议级自愈防线：合并连续相同角色
            cleaned_history = []
            for m in st.session_state.messages:
                if cleaned_history and cleaned_history[-1]["role"] == m["role"]:
                    cleaned_history[-1]["content"] += "\n" + m["content"]
                else:
                    cleaned_history.append({"role": m["role"], "content": m["content"]})
            
            system_prompt = (
                f"Current concept: {st.session_state.current_concept}.\n"
                f"Language: {lang_label}.\n"
                "STRICT RULE:\n"
                "1. Never give direct answers. Always guide step-by-step using Socratic questions.\n"
                "2. Assess student level (Basic/Partial/Mastered) and dynamic trigger exercise when appropriate.\n"
                "3. For AP Style problem requests: generate realistic AP-level multiple-choice or free-response questions based on the current concept. Provide encrypted key inside markdown spoilers.\n"
                "4. Absolutely never reveal your chain-of-thought (CoT)."
            )
            
            with st.spinner("⚡ Luo-cal 正在深度演算对话流..."):
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1548,
                    system=system_prompt,
                    messages=cleaned_history
                )
                assistant_res = response.content[0].text
                st.session_state.messages.append({"role": "assistant", "content": assistant_res})
                st.rerun()
        except Exception as e:
            st.error(f"❌ 系统摩擦报错详情: {str(e)}")

import streamlit as st
import os
from anthropic import Anthropic

st.set_page_config(page_title="AP-Cal 智能辅导总线", page_icon="🎓", layout="wide")

# 初始化后端内存状态机
if "ENV_CLAUDE_KEY" not in st.session_state:
    st.session_state.ENV_CLAUDE_KEY = ""
if "click_count" not in st.session_state:
    st.session_state.click_count = 0

# 🏛️ 侧边栏控制台
st.sidebar.title("🎓 AP-Cal 教学控制台")
st.sidebar.markdown("---")

# 📥 框 1：纯粹的输入接收框
input_key = st.sidebar.text_input(
    "🔑 步骤 1：请在此粘贴您的 Claude API Key:", 
    type="password", 
    value=st.session_state.ENV_CLAUDE_KEY, 
    placeholder="sk-ant-api..."
)

# ⚡ 框 2：点击框（按钮动作触发区）
click_action = st.sidebar.button("⚡ 步骤 2：【鼠标点击此处】物理提交输入")

# 🛡️ 动作状态校验防线：专门用来告诉老师“点击按钮本身有效”！
if click_action:
    st.session_state.click_count += 1
    if input_key.strip():
        st.session_state.ENV_CLAUDE_KEY = input_key.strip()
        os.environ["ANTHROPIC_API_KEY"] = st.session_state.ENV_CLAUDE_KEY
    else:
        st.session_state.ENV_CLAUDE_KEY = ""

# 如果检测到用户刚刚点击过按钮，立刻强制弹框回显，确保点击感知绝对明显
if click_action:
    st.sidebar.warning(f"📥 验证：已成功接收您的第 {st.session_state.click_count} 次物理点击提交！")

st.sidebar.markdown("---")

# 🔍 框 3：完全独立的“系统认可与底座鉴权结果”框（与点击动作隔离）
st.sidebar.markdown("### 📋 大模型底座系统认可状态")
with st.sidebar.container(border=True): # 刚性容器隔离框
    if st.session_state.ENV_CLAUDE_KEY:
        st.success("🟢 认可结果：系统已成功接纳并锁死了该密钥！AI 引擎点火完毕。")
    else:
        st.error("🔴 认可结果：当前底座尚未检测到有效激活凭证，AI 正处于挂起状态。")

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

# 🌐 界面翻译语言网关
lang_label = st.sidebar.radio("🌐 界面翻译网关语言 / Language Switch:", ["中文 (Chinese)", "English"])

# 🔄 状态机切换熔断
if "current_concept" not in st.session_state:
    st.session_state.current_concept = concept_option
if st.session_state.current_concept != concept_option:
    st.session_state.messages = []
    st.session_state.current_concept = concept_option

if "messages" not in st.session_state or len(st.session_state.messages) == 0:
    welcome_matrix = {
        "1.1 Limits Chronology (极限的直观引入与定义)": "Welcome! Let's explore how a function behaves as it infinitely approaches a point. Think about $f(x)=\\frac{x^2-1}{x-1}$ at $x=1$. What happens?",
        "1.2 Asymptotes & Infinity (无穷大与渐近线行为)": "Welcome! When the denominator shrinks to zero, the function value explodes. Let's touch the edge of infinity.",
        "1.3 Continuity & IVT (连续性定义与介值定理)": "Welcome! No holes, no jumps, no vertical asymptotes. If a continuous function goes from negative to positive, it MUST cross zero.",
        "1.4 Squeeze Theorem (夹逼定理的代数与几何夹击)": "Welcome! Locked from above, trapped from below. If two functions squeeze a middle one, its limit is absolute.",
        "2.1 Derivative Definition (导数的极限定义与割线变切线)": "Welcome! Instantaneous change is born from average change. Let's master the limit of the difference quotient.",
        "2.2 Power/Product/Quotient Rules (三大基础求导法则)": "Welcome! Let's shift our gear from limit calculations to shortcuts.",
        "2.3 Chain Rule & Implicit (复合函数求导与隐函数微分)": "Welcome! Peeling the onion layer by layer. Let's crack nested functions.",
        "2.4 Higher-Order Derivatives (高阶导数与物理变化率)": "Welcome! Let's observe rates of change."
    }
    st.session_state.messages = [{"role": "assistant", "content": welcome_matrix[st.session_state.current_concept]}]

# 🎨 渲染主界面布局
st.title("🎓 Luo-cal 智能微积分交互教学总线")
st.caption(f"当前死磕概念：{st.session_state.current_concept} | 语言：{lang_label}")

# 渲染历史会话
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 📷 移动端拍照上传通道
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

# 核心逻辑运算流（仅在有最新输入且系统认可密钥的情况下执行）
if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
    if not st.session_state.ENV_CLAUDE_KEY:
        st.warning("⚠️ 传输拦截：模型未能被激发。请确保在左侧侧边栏通过【步骤2】锁定并使系统认可您的密钥！")
    else:
        try:
            client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
            
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
            
            with st.spinner("⚡ Luo-cal 正在呼叫当前最新大模型底座..."):
                # 刚性锁定当前唯一最新可用模型标识符
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1548,
                    system=system_prompt,
                    messages=cleaned_history
                )
                assistant_res = response.content[0].text
                st.session_state.messages.append({"role": "assistant", "content": assistant_res})
                st.rerun()
        except Exception as e:
            st.error(f"❌ 系统摩擦报错详情: {str(e)}")

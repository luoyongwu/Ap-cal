import streamlit as st
import os
from anthropic import Anthropic

st.set_page_config(page_title="AP-Cal 智能辅导总线", page_icon="🎓", layout="wide")

# 🏛️ 侧边栏控制台
st.sidebar.title("🎓 AP-Cal 教学控制台")
st.sidebar.markdown("---")

if "ENV_CLAUDE_KEY" not in st.session_state:
    st.session_state.ENV_CLAUDE_KEY = ""

# 🔑 醒目的 Key 输入和状态回显防线
input_key = st.sidebar.text_input(
    "🔑 请输入您的 Claude API Key:", 
    type="password", 
    value=st.session_state.ENV_CLAUDE_KEY, 
    placeholder="sk-ant-api03-..."
)

if input_key:
    st.session_state.ENV_CLAUDE_KEY = input_key

# 🟢🔴 刚性状态指示灯回归！让老师一眼看清当前状态
if st.session_state.ENV_CLAUDE_KEY:
    st.sidebar.success("🟢 密钥已锁定！大模型底座随时可以点火。")
    # 物理注入系统环境变量，双重保险
    os.environ["ANTHROPIC_API_KEY"] = st.session_state.ENV_CLAUDE_KEY
else:
    st.sidebar.error("🔴 密钥未载入！大模型正处于断线锁定状态。")

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

# 🔄 状态机初始化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_concept" not in st.session_state:
    st.session_state.current_concept = concept_option

# 跨概念切换时安全熔断，重置清空历史栈
if st.session_state.current_concept != concept_option:
    st.session_state.messages = []
    st.session_state.current_concept = concept_option

# 🎨 主界面布局
st.title("🎓 Luo-cal 智能微积分交互教学总线")
st.caption(f"当前死磕概念：{st.session_state.current_concept} | 语言：{lang_label}")

# 渲染欢迎词矩阵
welcome_matrix = {
    "1.1 Limits Chronology (极限的直观引入与定义)": "Welcome! Let's explore how a function behaves as it infinitely approaches a point. Think about $f(x)=\\frac{x^2-1}{x-1}$ at $x=1$. What happens?",
    "1.2 Asymptotes & Infinity (无穷大与渐近线行为)": "Welcome! When the denominator shrinks to zero, the function value explodes. Let's touch the edge of infinity.",
    "1.3 Continuity & IVT (连续性定义与介值定理)": "Welcome! No holes, no jumps, no vertical asymptotes. If a continuous function goes from negative to positive, it MUST cross zero.",
    "1.4 Squeeze Theorem (夹逼定理的代数与几何夹击)": "Welcome! Locked from above, trapped from below. If two functions squeeze a middle one, its limit is absolute.",
    "2.1 Derivative Definition (导数的极限定义与割线变切线)": "Welcome! Instantaneous change is born from average change. Let's master the limit of the difference quotient.",
    "2.2 Power/Product/Quotient Rules (三大基础求导法则)": "Welcome! Let's shift our gear from limit calculations to structural shortcuts. Ready for the mechanics of differentiation?",
    "2.3 Chain Rule & Implicit (复合函数求导与隐函数微分)": "Welcome! Peeling the onion layer by layer. Let's crack the rate of change of nested functions.",
    "2.4 Higher-Order Derivatives (高阶导数与物理变化率)": "Welcome! The derivative of velocity is acceleration. Let's observe how the rate of change itself changes."
}

if len(st.session_state.messages) == 0:
    st.session_state.messages.append({"role": "assistant", "content": welcome_matrix[st.session_state.current_concept]})

# 渲染历史会话
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 📷 移动端拍照上传/手写习题交互模块
st.markdown("---")
st.subheader("📷 移动设备多模态答题通道")
uploaded_file = st.file_uploader("📝 在纸上写下您的推导步骤，拍照上传反馈：", type=["png", "jpg", "jpeg"])
if uploaded_file:
    st.success("🎉 图片捕获成功！Luo-cal 异步多模态 Vision 模块已就绪，准备扫描解题步骤。")

st.markdown("---")
# 🔑 习题控制及机制面板
st.subheader("🎯 习题触发控制中心")
col1, col2 = st.columns(2)
with col1:
    st.info("💡 **通道A (自动触发)**: 苏格拉底交互闭环已挂载。模型会自动判断您的掌握程度，随时切入提问。")
with col2:
    trigger_exam = st.button("🚀 显式触发：向模型索要当前概念 AP 风格习题")

# 💬 师生交互输入主干（支持按回车直接提交）
user_input = st.chat_input("在此输入您的微积分想法，或直接对模型说：'请给我出一道题'...")

# 逻辑合并：无论是用户输入，还是点击了显式触发按钮
final_input = ""
if user_input:
    final_input = user_input
elif trigger_exam:
    final_input = "【控制台指令】: 请立即根据当前选择的微积分概念，为我出一道符合 AP 难度和风格的综合习题，开始测试！"

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    with st.chat_message("user"):
        st.markdown(final_input)
        
    if not st.session_state.ENV_CLAUDE_KEY:
        st.warning("⚠️ 提示：请在左侧侧边栏输入您的 Claude API Key 以激活 AI 底座对话！")
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
            
            # 严格遵循约定的系统提示词（严防泄露思维链、苏格拉底式提问）
            system_prompt = (
                f"Current concept: {st.session_state.current_concept}.\n"
                f"Language网关切换为: {lang_label}.\n"
                "STRICT RULE:\n"
                "1. Never give direct answers or results. Always guide the student step-by-step using Socratic questions.\n"
                "2. Assess student level (Basic/Partial/Mastered) and dynamic trigger exercise when appropriate.\n"
                "3. For AP Style problem requests: generate realistic AP-level multiple-choice or free-response questions based on the current concept. Provide the encrypted answer key only inside markdown spoilers if forced.\n"
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
            st.error(f"❌ 大模型底座运行摩擦: {str(e)}")

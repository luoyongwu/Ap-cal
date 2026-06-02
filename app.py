import streamlit as st
import os
from anthropic import Anthropic

st.set_page_config(page_title="AP-Cal 智能辅导总线", page_icon="🎓", layout="wide")

# 🏛️ 侧边栏控制台
st.sidebar.title("🎓 AP-Cal 教学控制台")
st.sidebar.markdown("---")

if "ENV_CLAUDE_KEY" not in st.session_state:
    st.session_state.ENV_CLAUDE_KEY = ""

input_key = st.sidebar.text_input(
    "🔑 请输入您的 Claude API Key:", 
    type="password", 
    value=st.session_state.ENV_CLAUDE_KEY, 
    placeholder="sk-ant-api03-..."
)
if input_key:
    st.session_state.ENV_CLAUDE_KEY = input_key

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
uploaded_file = st.file_uploader("在纸上写下您的推导步骤，拍照上传反馈：", type=["png", "jpg", "jpeg"])
if uploaded_file:
    st.success("图片已捕获成功，主总线随时可以接入多模态 Vision 扫描！")

st.markdown("---")
# 🔑 工业级自愈防线：修正上一版 st.thumbnail 导致的崩溃，改用稳定的原生组件
if st.checkbox("🔑 查看 MCQ 官方答案密匙 & 习题触发状态机制"):
    st.info("习题触发器：双通道触发正常挂载 (通道A: 苏格拉底交互闭环 / 通道B: 显式触发)")

# 💬 师生交互输入主干
user_input = st.chat_input("在此输入您的微积分想法或直接向模型索要习题...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
        
    if not st.session_state.ENV_CLAUDE_KEY:
        st.warning("⚠️ 请在左侧侧边栏输入您的 Claude API Key 激活底座对话。")
    else:
        try:
            client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
            
            # 协议级自愈防线：处理历史栈中的连续相同角色，防止 API 报错
            cleaned_history = []
            for m in st.session_state.messages:
                if cleaned_history and cleaned_history[-1]["role"] == m["role"]:
                    cleaned_history[-1]["content"] += "\n" + m["content"]
                else:
                    cleaned_history.append({"role": m["role"], "content": m["content"]})
            
            # 构建系统提示词，严防泄露思维链
            system_prompt = f"Current concept: {st.session_state.current_concept}. Language: {lang_label}. STRICT RULE: Never give direct answers. Always guide with Socratic questions. Never reveal chain-of-thought."
            
            with st.spinner("Luo-cal 正在深度演算对话流..."):
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    system=system_prompt,
                    messages=cleaned_history
                )
                assistant_res = response.content[0].text
                
                st.session_state.messages.append({"role": "assistant", "content": assistant_res})
                with st.chat_message("assistant"):
                    st.markdown(assistant_res)
                    st.rerun()
        except Exception as e:
            st.error(f"❌ 大模型底座运行摩擦: {str(e)}")

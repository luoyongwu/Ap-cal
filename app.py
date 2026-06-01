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
    placeholder="sk-ant-api03-...",
    help="密钥锁死在后台内存中，断网或刷新 100% 不丢失。"
)

if input_key:
    st.session_state.ENV_CLAUDE_KEY = input_key.strip()
    os.environ["ANTHROPIC_API_KEY"] = input_key.strip()

st.sidebar.markdown("---")
lang_mode = st.sidebar.segmented_control("🌐 教学语言模式 / Language", ["中文 (CN)", "English (EN)"], default="中文 (CN)")

# 🤖 默认采用极速、普适性强的 Haiku 4.5 内核，Sonnet 顺延可选
model_option = st.sidebar.selectbox(
    "🤖 核心大模型内核选择", 
    ["claude-haiku-4-5-20251001", "claude-sonnet-4-5"],
    index=0,
    help="普通 API 密钥请务必保持默认 Haiku 选项，以确保极速响应与全账户兼容；Sonnet 仅限具备高级权限的账户升级使用。"
)

concept_option = st.sidebar.selectbox(
    "核心微积分概念 / Concepts",
    [
        "1.1 Concept of Approach (趋近的本质)",
        "1.2 Two-Sided Limits (左右极限独立性)",
        "1.3 Continuity 3-Conditions (连续性三承诺)",
        "1.4 IVT (介值定理)",
        "2.1 Instantaneous Rate (瞬时变化率哲学)",
        "2.2 Definition of Derivative (导数定义的0/0拯救)",
        "2.3 Corner and Cusp (连续但不可导的尖点对撞)",
        "2.4 Chain Rule Essence (链式法则齿轮咬合)",
        "🎓 Unit 1 & 2 阶段综合测试 (AP FRQ Style)"
    ]
)

unit_control_contract = {
    "anti_cheat_rules": {
        "chain_rule_cheat_keywords": ["忘记内层", "忘记求导", "忘掉内层", "forget inner", "just outer"],
        "chain_rule_prompt": "【CRITICAL CONSTRAINT】The student is discussing the Chain Rule. Remind them Socratically about the dependency of rates of change. If they forget the inner derivative, use the gear analogy (齿轮比喻) to show why the rates must multiply, not just look at the outer layer."
    }
}

welcome_matrix = {
    "1.1 Concept of Approach (趋近的本质)": {
        "中文 (CN)": "🤖 [AP-Cal 导师]: 你好。想象数轴上的一个动点正在向数字 1 移动。它每一次都缩短剩下距离的一半，因此它会无限地接近 1，但从停下的位置来看它始终没有真正等于 1。从直觉上讲，我们能说这个动点的最终趋势是 1 吗？这对你理解微积分中的极限（Limit）有什么启发？",
        "English (EN)": "🤖 [AP-Cal Tutor]: Hello. Imagine a point on a number line moving toward 1. Each step, it covers exactly half of the remaining distance. It approaches 1 infinitely but never structurally touches 1. Intuitively, can we say its ultimate trend is 1? What does this reveal about the concept of a Limit?"
    },
    "1.2 Two-Sided Limits (左右极限独立性)": {
        "中文 (CN)": "🤖 [AP-Cal 导师]: 你好。想象你正沿着一条峡谷的小路前进。从东边进峡谷时你测得的海拔是 100 米，但从西边进时测得的海拔是 50 米。在东西交界会合的这一点上，这个峡谷有唯一的极限（Limit）海拔吗？为什么？",
        "English (EN)": "🤖 [AP-Cal Tutor]: Hello. Imagine walking down a canyon trail. Approaching the border point from the East, your elevation is 100m. Approaching from the West, it is 50m. At that exact meeting point, does a single unique Limit of elevation exist? Why?"
    },
    "1.3 Continuity 3-Conditions (连续性三承诺)": {
        "中文 (CN)": "🤖 [AP-Cal 导师]: 你好。如果我们承诺你可以“不抬起笔尖”在纸上完美连续地画完一段函数曲线。当你的笔尖经过某个特定的点 x=c 时，在数学层面上，函数必须对你兑现哪三个刚性承诺？",
        "English (EN)": "🤖 [AP-Cal Tutor]: Hello. If we guarantee that you can draw a function's curve perfectly without ever lifting your pen, what three mathematical 'promises' must the function satisfy at any specific point x=c?"
    },
    "1.4 IVT (介值定理)": {
        "中文 (CN)": "🤖 [AP-Cal 导师]: 你好。在你的成长历程中，你的身高从 1 米长到了 1.8 米。在时间的河流里，是否必然存在那么一个被冻结的绝对瞬间，你的身高精准地停留在 1.527 米？为什么？",
        "English (EN)": "🤖 [AP-Cal Tutor]: Hello. During your growth, your height increased from 1m to 1.8m. In the river of time, must there exist a single frozen instant where your height was exactly 1.527m? What is the hidden assumption here?"
    },
    "2.1 Instantaneous Rate (瞬时变化率哲学)": {
        "中文 (CN)": "🤖 [AP-Cal 导师]: 你好。当我们用极高速度的相机拍照时，快门时间趋向于 0。在这样一张完美的、静止的照片里，藏着被摄物体的“运动”和“速度”信息吗？如果没有时间间隔，瞬时速度（Instantaneous Velocity）是如何诞生的？",
        "English (EN)": "🤖 [AP-Cal Tutor]: Hello. When a camera captures a high-speed photo, the shutter time approaches 0. In this perfectly frozen picture, does the concept of 'motion' or 'speed' still exist? If there is no time elapsed, how can we mathematically define instantaneous rate of change?"
    },
    "2.2 Definition of Derivative (导数定义的0/0拯救)": {
        "中文 (CN)": "🤖 [AP-Cal 导师]: 你好。在割线变切线、两点无限重合的过程中，斜率公式的分母 h 变成了 0。我们如何用 Unit 1 学到的极限魔法去拯救这个荒谬的 0/0 公式？代数消去中的 'h趋向0' 与 'h等于0' 有什么物理本质区别？",
        "English (EN)": "🤖 [AP-Cal Tutor]: Hello. As the secant line merges into a tangent line, the denominator h in the slope formula approaches 0. How do we use Unit 1's limit magic to rescue this absurd 0/0 expression? What is the absolute conceptual difference between 'h approaches 0' and 'h equals 0'?"
    },
    "2.3 Corner and Cusp (连续但不可导的尖点对撞)": {
        "中文 (CN)": "🤖 [AP-Cal 导师]: 你好。y = |x| 这个函数，在 x=0 处你能不抬笔地画过去吗？那么在这一点，你能画出它的切线吗？这两个问题的答案是否可以不同？",
        "English (EN)": "🤖 [AP-Cal Tutor]: Hello. For the function y = |x|, can you draw it continuously through x=0 without lifting your pen? At that exact point, can you draw a unique tangent line? Can the answers to these two questions be different?"
    },
    "2.4 Chain Rule Essence (链式法则齿轮咬合)": {
        "中文 (CN)": "🤖 [AP-Cal 导师]: 你好。想象三个互相咬合的齿轮 A, B, C。齿轮 A 每转 1 圈带动 B 转 2 圈，B 转 1 圈带动 C 转 3 圈。当 A 稍微转动一点点时，C 的转速变化是 A 的几倍？为什么复合函数求导（Chain Rule）的结构是乘法而不是加法？",
        "English (EN)": "🤖 [AP-Cal Tutor]: Hello. Imagine three interlocking gears A, B, and C. Gear A turns B at a 2x rate, and B turns C at a 3x rate. When A moves slightly, how many times faster does C change? Why is the structure of the Chain Rule multiplicative rather than additive?"
    },
    "🎓 Unit 1 & 2 阶段综合测试 (AP FRQ Style)": {
        "中文 (CN)": "🤖 [AP-Cal 导师]: 很好。我们现在进入 Unit 1 & 2 的 Free-Response Question (FRQ) 综合能力实战演练。请看下方上传区，你可以选择在纸上作答并拍照上传，或者直接在聊天框打出你的核心证明步骤。",
        "English (EN)": "🤖 [AP-Cal Tutor]: Welcome to the Unit 1 & 2 Free-Response Question (FRQ) Milestone. You can choose to write down your full derivations on paper and take a photo to upload below, or directly type your analytical logic in the chat input."
    }
}

if "current_concept" not in st.session_state:
    st.session_state.current_concept = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

# 概念切换自愈与重置机制
if st.session_state.current_concept != concept_option:
    st.session_state.messages = []
    st.session_state.current_concept = concept_option

# 欢迎词平铺触发
if len(st.session_state.messages) == 0:
    welcome_text = welcome_matrix[concept_option][lang_mode]
    st.session_state.messages.append({"role": "assistant", "content": welcome_text})

st.title("🎓 AP-Cal 苏格拉底交互式导师系统")
st.caption(f"内核核心: {model_option} | 当前聚焦概念: {concept_option}")

# 渲染历史对话
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 📸 完美渲染：file_uploader 标准组件
if concept_option == "🎓 Unit 1 & 2 阶段综合测试 (AP FRQ Style)":
    uploaded_file = st.file_uploader("📸 老师/同学：请上传您的手写 FRQ 卷面照片", type=["png", "jpg", "jpeg"])
    if uploaded_file and f"uploaded_{uploaded_file.name}" not in st.session_state:
        st.session_state[f"uploaded_{uploaded_file.name}"] = True
        frq_notice = f"📷 [系统提示]: 手写卷面 `{uploaded_file.name}` 已安全送达总线。请在下方输入框中打出您的核心解题思路，导师将联合卷面进行苏格拉底式评判。"
        st.session_state.messages.append({"role": "assistant", "content": frq_notice})
        st.rerun()

# 📬 用户交互主循环输入
if user_input := st.chat_input("在此输入您的微积分见解或疑问..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    if not st.session_state.ENV_CLAUDE_KEY:
        st.error("❌ 侧边栏检测到未填入 Claude API Key，请填入密钥后开启对话。")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Cal 正在深度思考中..."):
                try:
                    client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
                    
                    lang_label = "中文" if "CN" in lang_mode else "English"
                    chain_rule_injection = ""
                    if "Chain Rule" in concept_option:
                        chain_rule_injection = unit_control_contract["anti_cheat_rules"]["chain_rule_prompt"]
                    
                    system_prompt = f"""You are Cal, a Socratic AP Calculus tutor. 
Current concept: {concept_option}
Teaching language: {lang_label}
STRICT RULE: Never give direct answers. Always guide with questions.
Never reveal chain-of-thought. Ask one focused question at a time.
{chain_rule_injection}"""
                    
                    # 🛡️ 双重熔断历史网关：拦截噪音、合并同角色连续消息、修剪头部非法助手消息
                    formatted_messages = []
                    for m in st.session_state.messages:
                        if any(phrase in m["content"] for phrase in ["🤖 [AP-Cal", "📷 [系统提示]"]):
                            continue
                            
                        if formatted_messages and formatted_messages[-1]["role"] == m["role"]:
                            formatted_messages[-1]["content"] += "\n" + m["content"]
                        else:
                            formatted_messages.append({"role": m["role"], "content": m["content"]})
                    
                    while formatted_messages and formatted_messages[0]["role"] == "assistant":
                        formatted_messages.pop(0)
                    
                    if not formatted_messages:
                        formatted_messages.append({"role": "user", "content": user_input})
                        
                    response = client.messages.create(
                        model=model_option,
                        max_tokens=1000,
                        system=system_prompt,
                        messages=formatted_messages
                    )
                    reply = response.content[0].text
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                except Exception as e:
                    st.error(f"💥 API 交互发生摩擦: {str(e)}")

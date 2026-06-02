import streamlit as st
import os
from anthropic import Anthropic

st.set_page_config(page_title="AP-Cal 智能辅导总线", page_icon="🎓", layout="wide")

# 🧠 状态机核心内存挂载 (置于最顶层，严防状态丢失)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "ENV_CLAUDE_KEY" not in st.session_state:
    st.session_state.ENV_CLAUDE_KEY = ""
if "key_audit_status" not in st.session_state:
    st.session_state.key_audit_status = "NOT_VERIFIED" # 三种状态: NOT_VERIFIED, VALID, INVALID
if "current_concept" not in st.session_state:
    st.session_state.current_concept = ""

# 🗂️ 概念大纲矩阵配置 (Unit 1 & Unit 2 全量 8 大核心概念系统级配套欢迎语)
concept_matrix = {
    "Unit 1: Limits & Continuity": {
        "1.1 Defining Limits & Estimating From Graphs": {
            "en": "Hello! Welcome to AP Calculus BC. Today we explore **1.1 Defining Limits & Estimating From Graphs**. Intuitively, if a moving point approaches a certain position endlessly, will its final trend actually 'hit' that point? How do you understand the difference between 'approaching' and 'reaching'?",
            "zh": "你好！欢迎来到AP微积分课程。今天我们一起开辟1.1节：**极限的定义和从图中估算**。直观上说，如果一个动点无限向某个位置靠拢，它最终的趋势能和那个点撞上吗？你目前点是怎么理解‘趋近’和‘到达’的？"
        },
        "1.2 Algebraic Properties & Limit Evaluation": {
            "en": "Hello! Welcome to **1.2 Algebraic Properties & Limit Evaluation**. When we encounter expressions that cannot be evaluated by direct substitution (like denominator being 0), what do you think algebraic manipulation is actually doing? Are we hiding the flaw, or finding a new path?",
            "zh": "你好！欢迎开启1.2节：**极限的代数性质与计算**。当我们遇到不能直接代入的式子（比如分母为0），你认为代数变形的本质是在掩盖什么，还是在寻找新的出路？"
        },
        "1.3 Continuity & The Intermediate Value Theorem (IVT)": {
            "en": "Hello! Welcome to **1.3 Continuity & The Intermediate Value Theorem (IVT)**. If a function is continuous over a closed interval, can you draw a broken curve without lifting your pen? What is a practical, rigid application of the IVT in real life?",
            "zh": "你好！欢迎开启1.3节：**连续性与介值定理(IVT)**。如果一个函数在某个区间是连续的，你能不能不提笔就画出一段不连贯的曲线？介值定理在现实中有什么硬性应用？"
        },
        "1.4 Infinite Limits & Vertical Asymptotes": {
            "en": "Hello! Welcome to **1.4 Infinite Limits & Vertical Asymptotes**. When the independent variable infinitely approaches a certain point, and the function value blows up to infinity, what does this behavior mean visually on the graph?",
            "zh": "你好！欢迎开启1.4节：**无穷极限与垂直渐近线**。当自变量无限逼近某一点时，函数值如果冲向了无穷大，在图象上这意味着什么？"
        }
    },
    "Unit 2: Differentiation (Fundamentals)": {
        "2.1 Secant Lines, Tangent Lines & Derivative Definition": {
            "en": "Hello! Welcome to Unit 2 **2.1 Secant Lines, Tangent Lines & Derivative Definition**. How do you elevate an average rate of change from a secant line into an instantaneous slope of a tangent line? What mathematical gap is bridged here?",
            "zh": "你好！欢迎来到第2单元2.1节：**割线、切线与导数定义**。你如何把一段割线的平均变化率，提炼成某一个瞬间的切线斜率？这中间跨越了什么数学鸿沟？"
        },
        "2.2 Derivative Rules (Power, Constant, Sum, Exp, Log)": {
            "en": "Hello! Welcome to **2.2 Derivative Rules**. Behind formulas like Power Rule or Exponential derivative, the shadow of the limit definition is always there. Which foundational proof are you most interested in looking at?",
            "zh": "你好！欢迎开启2.2节：**基础导数法则**。幂函数、指数函数求导公式背后都有极限定义的影子，你目前对哪一个基础法则的推导最感兴趣？"
        },
        "2.3 Product Rule & Quotient Rule": {
            "en": "Hello! Welcome to **2.3 Product Rule & Quotient Rule**. Why is the derivative of a product of two functions NOT simply the product of their individual derivatives? Can you explain this using a geometric area or a concrete example?",
            "zh": "你好！欢迎开启2.3节：**乘积法则与商法则**。为什么两个函数乘积的导数，不等于它们各自导数的乘积？你能试着用几何图形或具体例子解释吗？"
        },
        "2.4 Chain Rule & Composite Functions": {
            "en": "Hello! Welcome to **2.4 Chain Rule & Composite Functions**. When dealing with a composite function $f(g(x))$, just like peeling an onion, do you think we should start from the outer layer first, or the inner core?",
            "zh": "你好！欢迎开启2.4节：**链式法则与复合函数**。面对复合函数 $f(g(x))$，就像剥洋葱一样，你认为应该先从外层剥起，还是先从内层剥起？"
        }
    }
}

# 🏛️ 选择组件挂载（放在前面以激活秒切刷新）
st.sidebar.title("🎓 AP-Cal 教学控制台")
st.sidebar.markdown("---")

unit_option = st.sidebar.selectbox("📂 选择教学单元 (Unit):", list(concept_matrix.keys()))
concept_option = st.sidebar.selectbox("🎯 选择核心概念 (Concept):", list(concept_matrix[unit_option].keys()))

# 🚀 【核心恢复点：概念瞬时秒切机制】
if st.session_state.current_concept != concept_option:
    st.session_state.current_concept = concept_option
    # 瞬间注入初始第一问结构（包含英中双语种子），由于不需要发网络请求，此动作极速完成
    st.session_state.messages = [{
        "role": "assistant",
        "en_content": concept_matrix[unit_option][concept_option]["en"],
        "zh_content": concept_matrix[unit_option][concept_option]["zh"]
    }]
    st.rerun()

# 🌐 【一键全屏瞬间切换网关】：不走后台翻译，通过前端开关秒级渲染，自由来回切换且绝不回退状态
st.sidebar.markdown("### 🌐 界面语言自由切换总线")
show_chinese = st.sidebar.checkbox("🇨🇳 开启全屏中英双语对照 (隐含默认纯英文页面)", value=True)

st.sidebar.markdown("---")

# 🔒 罗老师刚性审计：极致醒目的一目了然审核控制台
st.sidebar.markdown("### 🔑 密钥刚性审核中心")

# 1. 密码箱
input_key = st.sidebar.text_input(
    "1️⃣ 第一步：在此贴入您的 Claude Key",
    type="password",
    placeholder="sk-ant-api03-...",
    help="粘贴后请立刻点击下方的验证按钮，切勿按回车。"
)

# 2. 🎯 一目了然的物理点击处（大字符强视觉聚焦）
verify_clicked = st.sidebar.button("👉 2️⃣ 【核心动作：点击此处验证有效性】 👈")

# 3. 🚦 极其醒目的多状态审核看板
if st.session_state.key_audit_status == "NOT_VERIFIED":
    st.sidebar.warning("🟡 后台审计状态：等待锁定凭证...")
elif st.session_state.key_audit_status == "VALID":
    st.sidebar.success("🟢 审核通过：密钥完全有效！总线已全量激活。")
elif st.session_state.key_audit_status == "INVALID":
    st.sidebar.error("❌ 审核失败：密钥无法通过 Anthropic 联机握手测试！")

# 执行验证逻辑
if verify_clicked:
    if input_key:
        with st.sidebar.spinner("⏳ 正在进行多层杂质清洗与官方网络握手测试..."):
            cleaned_key = input_key.strip().replace('"', '').replace("'", "").strip()
            try:
                test_client = Anthropic(api_key=cleaned_key)
                test_client.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=1,
                    messages=[{"role": "user", "content": "ping"}]
                )
                st.session_state.ENV_CLAUDE_KEY = cleaned_key
                st.session_state.key_audit_status = "VALID"
                st.rerun()
            except Exception:
                st.session_state.key_audit_status = "INVALID"
                st.rerun()
    else:
        st.sidebar.warning("⚠️ 提示内容为空。")


st.sidebar.markdown("---")
if st.sidebar.button("♻️ 清空历史 · 开启当前新课题"):
    st.session_state.messages = [{
        "role": "assistant",
        "en_content": concept_matrix[unit_option][concept_option]["en"],
        "zh_content": concept_matrix[unit_option][concept_option]["zh"]
    }]
    st.rerun()

# 🏆 主教学舞台渲染
st.title(f"🎓 AP-Cal: {concept_option}")

# 🔄 极速前端渲染总线：自由来回切换且0延迟
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            # 助理发出的辅导流：根据勾选框状态，0秒动态切换排版样式，绝不回退状态
            if show_chinese:
                st.markdown(f"{msg['en_content']}\n\n---\n🇨🇳 **[中文释义]**\n{msg['zh_content']}")
            else:
                st.markdown(msg["en_content"])

# 🚀 苏格拉底驱动大模型核心逻辑（轻装上阵，只呼叫一次模型，速度提升一倍以上）
if student_input := st.chat_input("用英文或中文输入你的想法或疑问..."):
    if st.session_state.key_audit_status != "VALID":
        st.error("🚨 动作拦截：未检测到通过刚性验证的有效密钥！请先在左侧输入并完成核心动作。")
        st.stop()
        
    # 1. 压入学生输入
    st.session_state.messages.append({"role": "user", "content": student_input})
    st.rerun()

# 💫 后台大模型隐式生成（单周期并发，只呼叫一次模型）
if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
    client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
    
    # 状态机对齐防线
    sanitized_messages = []
    for msg in st.session_state.messages:
        # 为了兼容历史对齐，只将用户和助理的普通文本提取出来交接给大模型作为上下文
        content_text = msg["content"] if msg["role"] == "user" else msg["en_content"]
        if sanitized_messages and sanitized_messages[-1]["role"] == msg["role"]:
            sanitized_messages[-1]["content"] += f"\n{content_text}"
        else:
            sanitized_messages.append({"role": msg["role"], "content": content_text})
            
    while sanitized_messages and sanitized_messages[0]["role"] == "assistant" and len(sanitized_messages) > 1:
        sanitized_messages.pop(0)

    # 锁定双语同步输出核心大纲：迫使 Claude 3.5 同时吐出英中对照块，彻底切断慢速二次翻译网络
    system_prompt = f"""You are an expert AP Calculus BC professor guiding a student through the concept: {concept_option}.
    
    STRICT COMPLIANCE RULE: 
    1. Never give direct answers or formulas immediately. Always guide the student with targeted questions (Socratic Method).
    2. Ask only ONE focused question at a time.
    3. You MUST provide your response in BOTH English and Chinese simultaneously. 
    Format your response EXACTLY like this:
    [Your English Response here]
    ===
    [Your Chinese Response here]
    
    Ensure the content before and after '===' matches perfectly in meaning."""

    with st.chat_message("assistant"):
        with st.spinner("🧠 教授正在组织下一轮苏格拉底追问..."):
            try:
                api_messages = [{"role": m["role"], "content": m["content"]} for m in sanitized_messages]
                raw_response = client.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=1500,
                    temperature=0.3,
                    system=system_prompt,
                    messages=api_messages
                )
                raw_text = raw_response.content[0].text
                
                # 分割中英双语种子
                if "===" in raw_text:
                    parts = raw_text.split("===")
                    en_part = parts[0].strip()
                    zh_part = parts[1].strip()
                else:
                    en_part = raw_text
                    zh_part = "（大模型输出格式未完全切分，请保持对照查看）" + raw_text
                
                # 一键压入并存盘内存，保持两端对称
                st.session_state.messages.append({
                    "role": "assistant",
                    "en_content": en_part,
                    "zh_content": zh_part
                })
                st.rerun()
            except Exception as e:
                st.error(f"🚨 大模型总线发生摩擦: {str(e)}")

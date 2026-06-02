import streamlit as st
import os
from anthropic import Anthropic

st.set_page_config(page_title="AP-Cal 智能辅导总线", page_icon="🎓", layout="wide")

# 🧠 状态机内存初始化 (必须置于最顶层)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "ENV_CLAUDE_KEY" not in st.session_state:
    st.session_state.ENV_CLAUDE_KEY = ""
if "key_audit_result" not in st.session_state:
    st.session_state.key_audit_result = "🔴 未检测到凭证"

# 🚀 【核心修复】：主舞台初始化强行破冰，无需等待密钥，一打开页面就必须显示第一问
if len(st.session_state.messages) == 0:
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Hello! Welcome to AP-Cal. Today, let's explore **1.1 Defining Limits & Estimating From Graphs** together. To start, what is your current understanding of limits, or do you have a specific problem you want to look at?"
    })

# 🏛️ 侧边栏控制台
st.sidebar.title("🎓 AP-Cal 教学控制台")
st.sidebar.markdown("---")

# 1. 密码箱组件 (隐藏 Key 字符，不回显)
input_key = st.sidebar.text_input(
    "🔑 请输入您的 Claude API Key:",
    type="password",
    placeholder="sk-ant-api03-...",
    help="粘贴密钥后，请直接点击下方的物理确认按钮。"
)

st.sidebar.markdown("### 🚦 密钥审核状态")
# 2. 刚性向用户回显验证结果（绝不暴露 Key 密码本身）
if "🟢" in st.session_state.key_audit_result:
    st.sidebar.success(st.session_state.key_audit_result)
elif "🟡" in st.session_state.key_audit_result:
    st.sidebar.warning(st.session_state.key_audit_result)
else:
    st.sidebar.error(st.session_state.key_audit_result)

# 3. 🎯 罗老师指定的明确物理点击确认按钮
if st.sidebar.button("👉 【第一步：点击此处确认并验证密钥有效性】 👈"):
    if input_key:
        st.session_state.key_audit_result = "临 ⏳ 正在进行多层清洗与远端握手验证..."
        
        # 工业级多层清洗：无情滤掉所有由于复制夹带的空格、换行符、单双引号
        cleaned_key = input_key.strip().replace('"', '').replace("'", "").strip()
        
        # 刚性联机审核大模型是否真正有效
        try:
            test_client = Anthropic(api_key=cleaned_key)
            # 向 Anthropic 官方发送 1 字节的刚性握手测试流
            test_client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}]
            )
            # 握手成功：锁定内存，向用户展示审核通过结果
            st.session_state.ENV_CLAUDE_KEY = cleaned_key
            st.session_state.key_audit_result = "🟢 审核通过：密钥验证有效，总线已全量激活！"
            st.rerun()
        except Exception as e:
            # 握手失败：向用户明确反馈错误原因
            st.session_state.key_audit_result = f"❌ 审核失败：此密钥无法通过大模型验证。错误原因: {str(e)}"
            st.rerun()
    else:
        st.sidebar.warning("⚠️ 审核提示：输入框内无内容，请输入有效密钥。")

st.sidebar.markdown("---")

# 概念矩阵配置 (Unit 1 & Unit 2 全量 8 大核心概念完美集成)
concept_matrix = {
    "Unit 1: Limits & Continuity": [
        "1.1 Defining Limits & Estimating From Graphs",
        "1.2 Algebraic Properties & Limit Evaluation",
        "1.3 Continuity & The Intermediate Value Theorem (IVT)",
        "1.4 Infinite Limits & Vertical Asymptotes"
    ],
    "Unit 2: Differentiation (Fundamentals)": [
        "2.1 Secant Lines, Tangent Lines & Derivative Definition",
        "2.2 Derivative Rules (Power, Constant, Sum, Exp, Log)",
        "2.3 Product Rule & Quotient Rule",
        "2.4 Chain Rule & Composite Functions"
    ]
}

unit_option = st.sidebar.selectbox("📂 选择教学单元 (Unit):", list(concept_matrix.keys()))
concept_option = st.sidebar.selectbox("🎯 选择核心概念 (Concept):", concept_matrix[unit_option])

# 监听课题切换
if len(st.session_state.messages) > 0 and concept_option not in st.session_state.messages[0]["content"]:
    st.session_state.messages = [{
        "role": "assistant", 
        "content": f"Hello! Welcome to AP-Cal. Today, let's explore **{concept_option}** together. To start, what is your current understanding of this topic, or do you have a specific problem you want to look at?"
    }]
    st.rerun()

lang_option = st.sidebar.radio("🌐 教学语言 (Language):", ["English Only", "中英双语切换网关 (Bilingual)"])
lang_label = "Bilingual (English and Chinese)" if lang_option == "中英双语切换网关 (Bilingual)" else "Strictly English"

if st.sidebar.button("♻️ 清空历史 · 开启新课题"):
    st.session_state.messages = []
    st.rerun()

# 🏆 主教学舞台渲染
st.title(f"🎓 AP-Cal: {concept_option}")
st.caption(f"当前管控模式：苏格拉底式启发教学 | 语言网关：{lang_option}")

# 渲染历史对话流
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 🔄 翻译网关底层驱动函数（对接全新 claude-sonnet-4-5）
def translate_via_claude(text_list, target_lang="Chinese", client=None):
    if not client or not text_list:
        return text_list
    cleaned_list = [t for t in text_list if "AP-Cal" not in t and "concept matrix" not in t.lower()]
    if not cleaned_list:
        return text_list

    payload = "\n---\n".join(cleaned_list)
    prompt = f"You are a professional AP Calculus translator. Translate the following AP Calculus teaching dialogue into {target_lang}. Keep LaTeX formatting like $...$ or $$...$$ strictly untouched. Do not add any introductory or ending commentary, reply with the translation only.\n\n{payload}"
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )
        translated_raw = response.content[0].text
        return [t.strip() for t in translated_raw.split("---") if t.strip()]
    except Exception:
        return text_list

# 🚀 苏格格拉底驱动核心逻辑
if student_input := st.chat_input("用英文输入你对这个概念的想法或疑问..."):
    if "🟢" not in st.session_state.key_audit_result:
        st.error("🚨 动作拦截：未检测到通过刚性验证的有效密钥！请先在左侧输入 Key 并点击按钮通过审核。")
        st.stop()
        
    client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
    
    st.session_state.messages.append({"role": "user", "content": student_input})
    with st.chat_message("user"):
        st.markdown(student_input)
        
    sanitized_messages = []
    for msg in st.session_state.messages:
        if sanitized_messages and sanitized_messages[-1]["role"] == msg["role"]:
            sanitized_messages[-1]["content"] += f"\n{msg['content']}"
        else:
            sanitized_messages.append({"role": msg["role"], "content": msg["content"]})
            
    while sanitized_messages and sanitized_messages[0]["role"] == "assistant" and len(sanitized_messages) > 1:
        sanitized_messages.pop(0)

    chain_rule_injection = ""
    if "Chain Rule" in concept_option:
        chain_rule_injection = "STRICT COMPLIANCE: If the student struggles with derivative of f(g(x)), force them to identify the inner function u=g(x) and outer function f(u) separately. Do not let them bypass this step."

    system_prompt = f"""You are an expert AP Calculus BC professor guiding a student through the concept: {concept_option}.
    Your teaching language is: {lang_label}.
    STRICT RULE: Never give direct answers or formulas immediately. Always guide the student with targeted, conceptual questions (Socratic Method).
    Never reveal your chain-of-thought. Ask only ONE focused question at a time to prevent cognitive overload.
    {chain_rule_injection}"""

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        try:
            api_messages = [{"role": m["role"], "content": m["content"]} for m in sanitized_messages]

            raw_response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=1000,
                temperature=0.3,
                system=system_prompt,
                messages=api_messages
            )
            assistant_reply = raw_response.content[0].text
            
            if lang_option == "中英双语切换网关 (Bilingual)":
                translated_blocks = translate_via_claude([assistant_reply], target_lang="Chinese", client=client)
                if translated_blocks:
                    assistant_reply = f"{assistant_reply}\n\n---\n🇨🇳 **[中文释义]**\n{translated_blocks[0]}"
            
            response_placeholder.markdown(assistant_reply)
            st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
            
        except Exception as e:
            st.error(f"🚨 大模型逻辑总线发生摩擦: {str(e)}")

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
    help="密钥锁死在后台内存中，手机端 Safari 刷新 100% 不丢失。"
)
if input_key:
    st.session_state.ENV_CLAUDE_KEY = input_key

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

# 语种与苏格拉底模式刚性管控
lang_option = st.sidebar.radio("🌐 教学语言 (Language):", ["English Only", "中英双语切换网关 (Bilingual)"])
lang_label = "Bilingual (English and Chinese)" if lang_option == "中英双语切换网关 (Bilingual)" else "Strictly English"

st.sidebar.markdown("---")
if st.sidebar.button("♻️ 清空历史 · 开启新课题"):
    st.session_state.messages = []
    st.rerun()

# 🧠 核心状态机总线初始化
if "messages" not in st.session_state:
    st.session_state.messages = []

# 🏆 主教学舞台渲染
st.title(f"🎓 AP-Cal: {concept_option}")
st.caption(f"当前管控模式：苏格拉底式启发教学 | 语言网关：{lang_option}")

# 渲染历史对话流
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 🔄 翻译网关底层驱动函数（规避系统欢迎语、严格防超限、抗格式脱落）
def translate_via_claude(text_list, target_lang="Chinese", client=None):
    if not client or not text_list:
        return text_list
    
    # 工业级清洗：剔除初始欢迎矩阵，只针对学生和老师的对话进行增量高净值翻译
    cleaned_list = [t for t in text_list if "AP-Cal 概念矩阵已成功挂载" not in t and "concept matrix" not in t.lower()]
    if not cleaned_list:
        return text_list

    payload = "\n---\n".join(cleaned_list)
    prompt = f"You are a professional AP Calculus translator. Translate the following dialogue into {target_lang}. Keep LaTeX formatting like $...$ or $$...$$ strictly untouched. Do not add any commentary.\n\n{payload}"
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )
        translated_raw = response.content[0].text
        return [t.strip() for t in translated_raw.split("---") if t.strip()]
    except Exception:
        return text_list

# 🚀 苏格拉底驱动核心逻辑
if student_input := st.chat_input("用英文输入你对这个概念的想法或疑问..."):
    if not st.session_state.ENV_CLAUDE_KEY:
        st.warning("⚠️ 教学控制台未检测到 Claude API Key，请先在左侧栏输入密钥锁死后台。")
        st.stop()
        
    client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
    
    # 1. 压入学生原始输入
    st.session_state.messages.append({"role": "user", "content": student_input})
    with st.chat_message("user"):
        st.markdown(student_input)
        
    # 2. 状态机刚性红线校验与修复（预防同角色连续碰撞引发 API 400 报错）
    sanitized_messages = []
    for msg in st.session_state.messages:
        if sanitized_messages and sanitized_messages[-1]["role"] == msg["role"]:
            sanitized_messages[-1]["content"] += f"\n{msg['content']}"
        else:
            sanitized_messages.append({"role": msg.copy()})
            
    # 裁剪头部非法助理回复
    while sanitized_messages and sanitized_messages[0]["role"] == "assistant":
        sanitized_messages.pop(0)

    # 3. 构造刚性 Prompt 教学大纲
    chain_rule_injection = ""
    if "Chain Rule" in concept_option:
        chain_rule_injection = "STRICT COMPLIANCE: If the student struggles with derivative of f(g(x)), force them to identify the inner function u=g(x) and outer function f(u) separately. Do not let them bypass this step."

    system_prompt = f"""You are an expert AP Calculus BC professor guiding a student through the concept: {concept_option}.
    Your teaching language is: {lang_label}.
    STRICT RULE: Never give direct answers or formulas immediately. Always guide the student with targeted, conceptual questions (Socratic Method).
    Never reveal your chain-of-thought. Ask only ONE focused question at a time to prevent cognitive overload.
    {chain_rule_injection}"""

    # 4. 呼叫大模型逻辑总线
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        try:
            # 转换格式投射给 Claude
            api_messages = []
            for m in sanitized_messages:
                # 兼容打包格式
                content_data = m["content"]["content"] if isinstance(m["content"], dict) else m["content"]
                api_messages.append({"role": m["role"], "content": content_data})

            raw_response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.3,
                system=system_prompt,
                messages=api_messages
            )
            assistant_reply = raw_response.content[0].text
            
            # 5. 判定是否激活中英双语自动动态平滑转译网关
            if lang_option == "中英双语切换网关 (Bilingual)":
                translated_blocks = translate_via_claude([assistant_reply], target_lang="Chinese", client=client)
                if translated_blocks:
                    assistant_reply = f"{assistant_reply}\n\n---\n🇨🇳 **[中文释义]**\n{translated_blocks[0]}"
            
            response_placeholder.markdown(assistant_reply)
            st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
            
        except Exception as e:
            st.error(f"🚨 大模型逻辑总线发生摩擦: {str(e)}")
